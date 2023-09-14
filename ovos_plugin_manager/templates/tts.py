"""
this module is meant to enable usage of mycroft plugins inside and outside
mycroft, importing from here will make things work as planned in mycroft,
but if outside mycroft things will still work

The main use case is for plugins to be used across different projects

## Differences from upstream

TTS:
- added automatic guessing of phonemes/visime calculation, enabling mouth
movements for all TTS engines (only mimic implements this in upstream)
- playback start call has been omitted and moved to init method
- init is called by mycroft, but non mycroft usage wont call it
- outside mycroft the enclosure is not set, bus is dummy and playback thread is not used
    - playback queue is not wanted when some module is calling get_tts
    - if playback was started on init then python scripts would never stop
        from mycroft.tts import TTSFactory
        engine = TTSFactory.create()
        engine.get_tts("hello world", "hello_world." + engine.audio_ext)
        # would hang here
        engine.playback.stop()
"""
import inspect
import random
import re
import subprocess
import threading
from distutils.spawn import find_executable
from os.path import isfile, join, exists
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from time import time, sleep

import requests
from ovos_config import Configuration

from ovos_bus_client.message import Message, dig_for_message
from ovos_plugin_manager.g2p import OVOSG2PFactory, find_g2p_plugins
from ovos_plugin_manager.templates.g2p import OutOfVocabulary
from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache, hash_sentence
from ovos_utils import classproperty
from ovos_utils import resolve_resource_file
from ovos_utils.enclosure.api import EnclosureAPI
from ovos_utils.file_utils import get_cache_directory
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus as BUS
from ovos_utils.metrics import Stopwatch
from ovos_utils.process_utils import RuntimeRequirements
from ovos_utils.sound import play_audio

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)
SSML_TAGS = re.compile(r'<[^>]*>')


class PlaybackThread(Thread):
    """Thread class for playing back tts audio and sending
    viseme data to enclosure.
    """

    def __init__(self, queue):
        super(PlaybackThread, self).__init__()
        self.queue = queue
        self._terminated = False
        self._processing_queue = False
        self._paused = False
        self.enclosure = None
        self.p = None
        self._tts = []
        self.bus = None
        self._now_playing = None
        self.active_tts = None
        self._started = threading.Event()

    @property
    def is_running(self):
        return self._started.is_set() and not self._terminated

    def activate_tts(self, tts_id):
        self.active_tts = tts_id
        tts = self.get_attached_tts()
        if tts:
            tts.begin_audio()

    def deactivate_tts(self):
        if self.active_tts:
            tts = self.get_attached_tts()
            if tts:
                tts.end_audio()
        self.active_tts = None

    def init(self, tts):
        """DEPRECATED! Init the TTS Playback thread."""
        self.attach_tts(tts)
        self.set_bus(tts.bus)

    def set_bus(self, bus):
        """Provide bus instance to the TTS Playback thread.
        Args:
            bus (MycroftBusClient): bus client
        """
        self.bus = bus

    @property
    def tts(self):
        tts = self.get_attached_tts()
        if not tts and self._tts:
            return self._tts[0]
        return tts

    @tts.setter
    def tts(self, val):
        self.attach_tts(val)

    @property
    def attached_tts(self):
        return self._tts

    def attach_tts(self, tts):
        """Add TTS to be cache checked."""
        if tts not in self.attached_tts:
            self.attached_tts.append(tts)

    def detach_tts(self, tts):
        """Remove TTS from cache check."""
        if tts in self.attached_tts:
            self.attached_tts.remove(tts)

    def get_attached_tts(self, tts_id=None):
        tts_id = tts_id or self.active_tts
        if not tts_id:
            return
        for tts in self.attached_tts:
            if hasattr(tts, "tts_id"):
                # opm plugin
                if tts.tts_id == tts_id:
                    return tts

        for tts in self.attached_tts:
            if not hasattr(tts, "tts_id"):
                # non-opm plugin
                if tts.tts_name == tts_id:
                    return tts

    def clear_queue(self):
        """Remove all pending playbacks."""
        while not self.queue.empty():
            self.queue.get()
        try:
            self.p.terminate()
        except Exception:
            pass

    def begin_audio(self, message=None):
        """Perform beginning of speech actions."""
        if self.bus:
            message = message or Message("speak")
            self.bus.emit(message.forward("recognizer_loop:audio_output_start"))
        else:
            LOG.warning("Speech started before bus was attached.")

    def end_audio(self, listen, message=None):
        """Perform end of speech output actions.
        Will inform the system that speech has ended and trigger the TTS's
        cache checks. Listening will be triggered if requested.
        Args:
            listen (bool): True if listening event should be emitted
        """
        if self.bus:
            # Send end of speech signals to the system
            message = message or Message("speak")
            self.bus.emit(message.forward("recognizer_loop:audio_output_end"))
            if listen:
                self.bus.emit(message.forward('mycroft.mic.listen'))
        else:
            LOG.warning("Speech started before bus was attached.")

    def on_start(self, message=None):
        self.blink(0.5)
        if not self._processing_queue:
            self._processing_queue = True
            self.begin_audio(message)

    def on_end(self, listen=False, message=None):
        if self._processing_queue:
            self.end_audio(listen, message)
            self._processing_queue = False
        # Clear cache for all attached tts objects
        # This is basically the only safe time
        for tts in self.attached_tts:
            tts.cache.curate()
        self.blink(0.2)

    def _play(self):
        try:
            data, visemes, listen, tts_id, message = self._now_playing
            self.activate_tts(tts_id)
            self.on_start(message)
            self.p = play_audio(data)
            if visemes:
                self.show_visemes(visemes)
            if self.p:
                self.p.communicate()
                self.p.wait()
            self.deactivate_tts()
            if self.queue.empty():
                self.on_end(listen, message)
        except Empty:
            pass
        except Exception as e:
            LOG.exception(e)
            if self._processing_queue:
                self.on_end()
        self._now_playing = None

    def run(self, cb=None):
        """Thread main loop. Get audio and extra data from queue and play.

        The queue messages is a tuple containing
        snd_type: 'mp3' or 'wav' telling the loop what format the data is in
        data: path to temporary audio data
        videmes: list of visemes to display while playing
        listen: if listening should be triggered at the end of the sentence.

        Playback of audio is started and the visemes are sent over the bus
        the loop then wait for the playback process to finish before starting
        checking the next position in queue.

        If the queue is empty the tts.end_audio() is called possibly triggering
        listening.
        """
        self._paused = False
        self._started.set()
        while not self._terminated:
            while self._paused:
                sleep(0.2)
            try:
                # HACK: we do these check to account for direct usages of TTS.queue singletons
                speech_data = self.queue.get(timeout=2)
                if len(speech_data) == 5 and isinstance(speech_data[-1], Message):
                    data, visemes, listen, tts_id, message = speech_data
                else:
                    LOG.warning("it seems you interfacing with TTS.queue directly, this is not recommended!\n"
                                "new expected TTS.queue contents -> data, visemes, listen, tts_id, message")
                    if len(speech_data) == 6:
                        # old ovos backwards compat
                        _, data, visemes, ident, listen, tts_id = speech_data
                    elif len(speech_data) == 5:
                        # mycroft style
                        tts_id = None
                        _, data, visemes, ident, listen = speech_data
                    else:
                        # old mycroft style  TODO can this be deprecated? its very very old
                        listen = False
                        tts_id = None
                        _, data, visemes, ident = speech_data

                    message = Message("speak", context={"session": {"session_id": ident}})

                self._now_playing = (data, visemes, listen, tts_id, message)
                self._play()
            except Exception as e:
                pass

    def show_visemes(self, pairs):
        """Send viseme data to enclosure

        Args:
            pairs (list): Visime and timing pair

        Returns:
            bool: True if button has been pressed.
        """
        if self.enclosure:
            self.enclosure.mouth_viseme(time(), pairs)

    def pause(self):
        """pause thread"""
        self._paused = True
        if self.p:
            self.p.terminate()

    def resume(self):
        """resume thread"""
        if self._now_playing:
            self._play()
        self._paused = False

    def clear(self):
        """Clear all pending actions for the TTS playback thread."""
        self.clear_queue()

    def blink(self, rate=1.0):
        """Blink mycroft's eyes"""
        if self.enclosure and random.random() < rate:
            self.enclosure.eyes_blink("b")

    def stop(self):
        """Stop thread"""
        self._now_playing = None
        self._terminated = True
        self.clear_queue()

    def shutdown(self):
        self.stop()
        for tts in self.attached_tts:
            self.detach_tts(tts)

    def __del__(self):
        self.shutdown()


class TTSContext:
    """ parses kwargs for valid signatures and extracts voice/lang optional parameters
    it will look for a requested voice in kwargs and inside the source Message data if available.
    voice can also be defined by a combination of language and gender,
    in that case the helper method get_voice will be used to resolve the final voice_id
    """

    def __init__(self, engine):
        self.engine = engine

    def get_message(self, kwargs):
        msg = kwargs.get("message") or dig_for_message()
        if msg and isinstance(msg, Message):
            return msg

    def get_lang(self, kwargs):
        # parse requested language for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        lang = kwargs.get("lang")
        message = self.get_message(kwargs)
        if not lang and message:
            # get lang from message object if possible
            lang = message.data.get("lang") or \
                   message.context.get("lang")
        return lang or self.engine.lang

    def get_gender(self, kwargs):
        gender = kwargs.get("gender")
        message = self.get_message(kwargs)
        if not gender and message:
            # get gender from message object if possible
            gender = message.data.get("gender") or \
                     message.context.get("gender")
        return gender

    def get_voice(self, kwargs):
        # parse requested voice for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        voice = kwargs.get("voice")
        message = self.get_message(kwargs)
        if not voice and message:
            # get voice from message object if possible
            voice = message.data.get("voice") or \
                    message.context.get("voice")

        if not voice:
            gender = self.get_gender(kwargs)
            if gender:
                lang = self.get_lang(kwargs)
                voice = self.engine.get_voice(gender, lang)

        return voice or self.engine.voice

    def get(self, kwargs=None):
        kwargs = kwargs or {}
        return self.get_lang(kwargs), self.get_voice(kwargs)

    def get_cache(self, kwargs=None):
        lang, voice = self.get(kwargs)
        return self.engine.get_cache(voice, lang)


class TTS:
    """TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` and ``validate_ssml(sentence)`` functions.

    Arguments:
        lang (str):
        config (dict): Configuration for this specific tts engine
        validator (TTSValidator): Used to verify proper installation
        phonetic_spelling (bool): Whether to spell certain words phonetically
        ssml_tags (list): Supported ssml properties. Ex. ['speak', 'prosody']
    """
    queue = None
    playback = None

    def __init__(self, lang="en-us", config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        self.log_timestamps = False

        self.config = config or get_plugin_config(config, "tts")

        self.stopwatch = Stopwatch()
        self.tts_name = self.__class__.__name__
        self.bus = BUS()  # initialized in "init" step
        self.lang = lang or self.config.get("lang") or 'en-us'
        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []
        self.log_timestamps = self.config.get("log_timestamps", False)

        self.voice = self.config.get("voice") or "default"
        # TODO can self.filename be deprecated ? is it used anywhere at all?
        cache_dir = get_cache_directory(self.tts_name)
        self.filename = join(cache_dir, 'tts.' + self.audio_ext)
        self.effects = self.config.get("effects", {})  # for TTSMutator

        random.seed()

        if TTS.queue is None:
            TTS.queue = Queue()

        self.context = TTSContext(self)

        # NOTE: self.playback.start() was moved to init method
        #   playback queue is not wanted if we only care about get_tts
        #   init is called by mycroft, but non mycroft usage wont call it,
        #   outside mycroft the enclosure is not set, bus is dummy and
        #   playback thread is not used
        self.spellings = self.load_spellings()

        self.caches = {
            self.tts_id: TextToSpeechCache(
                self.config, self.tts_id, self.audio_ext
            )}

        cfg = Configuration()
        g2pm = self.config.get("g2p_module")
        if g2pm:
            if g2pm in find_g2p_plugins():
                cfg.setdefault("g2p", {})
                globl = cfg["g2p"].get("module") or g2pm
                if globl != g2pm:
                    LOG.info(f"TTS requested {g2pm} explicitly, ignoring global module {globl} ")
                cfg["g2p"]["module"] = g2pm
            else:
                LOG.warning(f"TTS selected {g2pm}, but it is not available!")

        try:
            self.g2p = OVOSG2PFactory.create(cfg)
        except:
            LOG.exception("G2P plugin not loaded, there will be no mouth movements")
            self.g2p = None

        self.cache.curate()

        self.add_metric({"metric_type": "tts.init"})

    @classproperty
    def runtime_requirements(self):
        """ skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements()

    @property
    def tts_id(self):
        lang, voice = self.context.get()
        return join(self.tts_name, voice, lang)

    @property
    def cache(self):
        return self.caches.get(self.tts_id) or \
            self.get_cache()

    @cache.setter
    def cache(self, val):
        self.caches[self.tts_id] = val

    def get_cache(self, voice=None, lang=None):
        lang = lang or self.lang
        voice = voice or self.voice or "default"
        tts_id = join(self.tts_name, voice, lang)
        if tts_id not in self.caches:
            self.caches[tts_id] = TextToSpeechCache(
                self.config, tts_id, self.audio_ext
            )
        return self.caches[tts_id]

    def handle_metric(self, metadata=None):
        """ receive timing metrics for diagnostics
        does nothing by default but plugins might use it, eg, NeonCore"""

    def add_metric(self, metadata=None):
        """ wraps handle_metric to catch exceptions and log timestamps """
        try:
            self.handle_metric(metadata)
            if self.log_timestamps:
                LOG.debug(f"time delta: {self.stopwatch.delta} metric: {metadata}")
        except Exception as e:
            LOG.exception(e)

    def load_spellings(self, config=None):
        """Load phonetic spellings of words as dictionary."""
        path = join('text', self.lang.lower(), 'phonetic_spellings.txt')
        try:
            spellings_file = resolve_resource_file(path, config=config)
        except:
            LOG.debug('Failed to locate phonetic spellings resouce file.')
            return {}
        if not spellings_file:
            return {}
        try:
            with open(spellings_file) as f:
                lines = filter(bool, f.read().split('\n'))
            lines = [i.split(':') for i in lines]
            return {key.strip(): value.strip() for key, value in lines}
        except ValueError:
            LOG.exception('Failed to load phonetic spellings.')
            return {}

    def begin_audio(self):
        """Helper function for child classes to call in execute()"""
        self.add_metric({"metric_type": "tts.start"})

    def end_audio(self, listen=False):
        """Helper cleanup function for child classes to call in execute().

        Arguments:
            listen (bool): DEPRECATED: indication if listening trigger should be sent.
        """
        self.add_metric({"metric_type": "tts.end"})
        self.stopwatch.stop()

    def init(self, bus=None):
        """ Performs intial setup of TTS object.

        Arguments:
            bus:    Mycroft messagebus connection
        """
        self.bus = bus or BUS()
        self._init_playback()
        self.add_metric({"metric_type": "tts.setup"})

    def _init_playback(self):
        # shutdown any previous thread
        if TTS.playback:
            TTS.playback.shutdown()

        TTS.playback = PlaybackThread(TTS.queue)
        TTS.playback.set_bus(self.bus)
        TTS.playback.attach_tts(self)
        if not TTS.playback.enclosure:
            TTS.playback.enclosure = EnclosureAPI(self.bus)
        TTS.playback.start()

    @property
    def enclosure(self):
        if not TTS.playback.enclosure:
            bus = TTS.playback.bus or self.bus
            TTS.playback.enclosure = EnclosureAPI(bus)
        return TTS.playback.enclosure

    @enclosure.setter
    def enclosure(self, val):
        TTS.playback.enclosure = val

    def get_tts(self, sentence, wav_file, lang=None):
        """Abstract method that a tts implementation needs to implement.

        Should get data from tts.

        Arguments:
            sentence(str): Sentence to synthesize
            wav_file(str): output file
            lang(str): requested language (optional), defaults to self.lang

        Returns:
            tuple: (wav_file, phoneme)
        """
        return "", None

    def modify_tag(self, tag):
        """Override to modify each supported ssml tag.

        Arguments:
            tag (str): SSML tag to check and possibly transform.
        """
        return tag

    @staticmethod
    def remove_ssml(text):
        """Removes SSML tags from a string.

        Arguments:
            text (str): input string

        Returns:
            str: input string stripped from tags.
        """
        return re.sub('<[^>]*>', '', text).replace('  ', ' ')

    @staticmethod
    def format_speak_tags(sentence: str, include_tags: bool = True) -> str:
        """
        Cleans up SSML tags for speech synthesis and ensures the phrase is
        wrapped in 'speak' tags and any excluded text is
        removed.
        Args:
            sentence: Input sentence to be spoken
            include_tags: Flag to include <speak> tags in returned string
        Returns:
            Cleaned sentence to pass to TTS
        """
        # Wrap sentence in speak tag if no tags present
        if "<speak>" not in sentence and "</speak>" not in sentence:
            to_speak = f"<speak>{sentence}</speak>"
        # Assume speak starts at the beginning of the sentence
        elif "<speak>" not in sentence:
            to_speak = f"<speak>{sentence}"
        # Assume speak ends at the end of the sentence
        elif "</speak>" not in sentence:
            to_speak = f"{sentence}</speak>"
        else:
            to_speak = sentence

        # Trim text outside of speak tags
        if not to_speak.startswith("<speak>"):
            to_speak = f"<speak>{to_speak.split('<speak>', 1)[1]}"

        if not to_speak.endswith("</speak>"):
            to_speak = f"{to_speak.split('</speak>', 1)[0]}</speak>"

        if to_speak == "<speak></speak>":
            return ""

        if include_tags:
            return to_speak
        else:
            return to_speak.lstrip("<speak>").rstrip("</speak>")

    def validate_ssml(self, utterance):
        """Check if engine supports ssml, if not remove all tags.

        Remove unsupported / invalid tags

        Arguments:
            utterance (str): Sentence to validate

        Returns:
            str: validated_sentence
        """

        # Validate speak tags
        if not self.ssml_tags or "speak" not in self.ssml_tags:
            self.format_speak_tags(utterance, False)
        elif self.ssml_tags and "speak" in self.ssml_tags:
            self.format_speak_tags(utterance)

        # if ssml is not supported by TTS engine remove all tags
        if not self.ssml_tags:
            return self.remove_ssml(utterance)

        # find ssml tags in string
        tags = SSML_TAGS.findall(utterance)

        for tag in tags:
            if any(supported in tag for supported in self.ssml_tags):
                utterance = utterance.replace(tag, self.modify_tag(tag))
            else:
                # remove unsupported tag
                utterance = utterance.replace(tag, "")

        # return text with supported ssml tags only
        return utterance.replace("  ", " ")

    def _preprocess_sentence(self, sentence):
        """Default preprocessing is no preprocessing.

        This method can be overridden to create chunks suitable to the
        TTS engine in question.

        Arguments:
            sentence (str): sentence to preprocess

        Returns:
            list: list of sentence parts
        """
        return [sentence]

    def execute(self, sentence, ident=None, listen=False, **kwargs):
        """Convert sentence to speech, preprocessing out unsupported ssml

        The method caches results if possible using the hash of the
        sentence.

        Arguments:
            sentence: (str) Sentence to be spoken
            ident: (str) session_id from Message
            listen: (bool) True if listen should be triggered at the end
                    of the utterance.
        """
        sentence = self.validate_ssml(sentence)
        self.add_metric({"metric_type": "tts.ssml.validated"})
        self._execute(sentence, ident, listen, **kwargs)

    def _replace_phonetic_spellings(self, sentence):
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    spelled = self.spellings[word.lower()]
                    sentence = sentence.replace(word, spelled)
        return sentence

    def _execute(self, sentence, ident, listen, **kwargs):
        self.stopwatch.start()
        sentence = self._replace_phonetic_spellings(sentence)
        chunks = self._preprocess_sentence(sentence)
        # Apply the listen flag to the last chunk, set the rest to False
        chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                  for i in range(len(chunks))]
        self.add_metric({"metric_type": "tts.preprocessed",
                         "n_chunks": len(chunks)})

        lang, voice = self.context.get(kwargs)
        tts_id = join(self.tts_name, voice, lang)

        # synth -> queue for playback
        for sentence, l in chunks:
            # load from cache or synth + cache
            audio_file, phonemes = self.synth(sentence, **kwargs)

            # get visemes/mouth movements
            viseme = []
            if phonemes:
                viseme = self.viseme(phonemes)
            elif self.g2p is not None:
                try:
                    viseme = self.g2p.utterance2visemes(sentence, lang)
                except OutOfVocabulary:
                    pass
                except:
                    # this one is unplanned, let devs know all the info so they can fix it
                    LOG.exception(f"Unexpected failure in G2P plugin: {self.g2p}")

            if not viseme:
                # Debug level because this is expected in default installs
                LOG.debug(f"no mouth movements available! unknown visemes for {sentence}")

            message = kwargs.get("message") or \
                      dig_for_message() or \
                      Message("speak", context={"session": {"session_id": ident}})
            TTS.queue.put(
                (str(audio_file), viseme, l, tts_id, message)
            )
            self.add_metric({"metric_type": "tts.queued"})

    def apply_voice_effects(self, wav_file):
        if not self.effects:
            return wav_file
        if not find_executable("sox"):
            LOG.error("sox not found, can not apply voice effects")
            return wav_file
        mutator = TTSMutator(wav_file, self.effects)
        mutated_wav = wav_file.replace(f".{self.audio_ext}",
                                       f"_mutated.{self.audio_ext}")
        mutator.apply(mutated_wav)
        return mutated_wav

    def synth(self, sentence, **kwargs):
        """ This method wraps get_tts
        several optional keyword arguments are supported
        sentence will be read/saved to cache"""
        self.add_metric({"metric_type": "tts.synth.start"})
        sentence_hash = hash_sentence(sentence)

        # parse requested language for this TTS request
        # NOTE: this is ovos/neon only functionality, not in mycroft-core!
        lang, voice = self.context.get(kwargs)
        kwargs["lang"] = lang
        kwargs["voice"] = voice

        cache = self.get_cache(voice, lang)  # cache per tts_id (lang/voice combo)

        # load from cache
        if sentence_hash in cache:
            audio, phonemes = self.get_from_cache(sentence, **kwargs)
            self.add_metric({"metric_type": "tts.synth.finished", "cache": True})
            return audio, phonemes

        # synth + cache
        audio = cache.define_audio_file(sentence_hash)

        # filter kwargs per plugin, different plugins expose different options
        #   mycroft-core -> no kwargs
        #   ovos -> lang + voice optional kwargs
        #   neon-core -> message
        kwargs = {k: v for k, v in kwargs.items()
                  if k in inspect.signature(self.get_tts).parameters
                  and k not in ["sentence", "wav_file"]}

        # finally do the TTS synth
        audio.path, phonemes = self.get_tts(sentence, str(audio), **kwargs)
        self.add_metric({"metric_type": "tts.synth.finished"})

        # cache sentence + phonemes
        self._cache_sentence(sentence, audio, phonemes, sentence_hash,
                             voice=voice, lang=lang)

        audio.path = self.apply_voice_effects(audio.path)
        return audio, phonemes

    def _cache_phonemes(self, sentence, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        if not phonemes and self.g2p is not None:
            try:
                phonemes = self.g2p.utterance2arpa(sentence, self.lang)
                self.add_metric({"metric_type": "tts.phonemes.g2p"})
            except Exception as e:
                self.add_metric({"metric_type": "tts.phonemes.g2p.error", "error": str(e)})
        if phonemes:
            return self.save_phonemes(sentence_hash, phonemes)
        return None

    def _cache_sentence(self, sentence, audio_file, phonemes=None, sentence_hash=None,
                        voice=None, lang=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        # RANT: why do you hate strings ChrisV?
        if isinstance(audio_file.path, str):
            audio_file.path = Path(audio_file.path)
        pho_file = self._cache_phonemes(sentence, phonemes, sentence_hash)
        cache = self.get_cache(voice=voice, lang=lang)
        cache.cached_sentences[sentence_hash] = (audio_file, pho_file)
        self.add_metric({"metric_type": "tts.synth.cached"})

    def get_from_cache(self, sentence, **kwargs):
        sentence_hash = hash_sentence(sentence)
        phonemes = None
        cache = self.context.get_cache(kwargs)
        audio_file, pho_file = cache.cached_sentences[sentence_hash]
        LOG.info(f"Found {audio_file.name} in TTS cache")
        if not pho_file:
            # guess phonemes from sentence + cache them
            pho_file = self._cache_phonemes(sentence, sentence_hash)
        if pho_file:
            phonemes = pho_file.load()
        return audio_file, phonemes

    def get_voice(self, gender, lang=None):
        """ map a language and gender to a valid voice for this TTS engine """
        lang = lang or self.lang
        return gender

    def viseme(self, phonemes):
        """Create visemes from phonemes.

        May be implemented to convert TTS phonemes into Mycroft mouth
        visuals.

        Arguments:
            phonemes (str): String with phoneme data

        Returns:
            list: visemes
        """
        visimes = []
        if phonemes:
            phones = str(phonemes).split(" ")
            for pair in phones:
                if ":" in pair:
                    pho_dur = pair.split(":")  # phoneme:duration
                    if len(pho_dur) == 2:
                        visimes.append((VISIMES.get(pho_dur[0], '4'),
                                        float(pho_dur[1])))
                else:
                    visimes.append((VISIMES.get(pair, '4'),
                                    float(0.2)))
        return visimes or None

    def clear_cache(self):
        """ Remove all cached files. """
        self.cache.clear()

    def save_phonemes(self, key, phonemes):
        """Cache phonemes

        Arguments:
            key (str):        Hash key for the sentence
            phonemes (str):   phoneme string to save
        """
        phoneme_file = self.cache.define_phoneme_file(key)
        phoneme_file.save(phonemes)
        return phoneme_file

    def load_phonemes(self, key):
        """Load phonemes from cache file.

        Arguments:
            key (str): Key identifying phoneme cache
        """
        phoneme_file = self.cache.define_phoneme_file(key)
        return phoneme_file.load()

    def stop(self):
        if TTS.playback:
            try:
                TTS.playback.stop()
            except Exception as e:
                pass
        self.add_metric({"metric_type": "tts.stop"})

    def shutdown(self):
        self.stop()
        if TTS.playback:
            TTS.playback.detach_tts(self)

    def __del__(self):
        self.shutdown()

    @property
    def available_languages(self) -> set:
        """Return languages supported by this TTS implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()


class TTSValidator:
    """TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """

    def __init__(self, tts):
        self.tts = tts

    def validate(self):
        self.validate_dependencies()
        self.validate_instance()
        self.validate_filename()
        self.validate_lang()
        self.validate_connection()

    def validate_dependencies(self):
        """Determine if all the TTS's external dependencies are satisfied."""
        pass

    def validate_instance(self):
        pass

    def validate_filename(self):
        pass

    def validate_lang(self):
        """Ensure the TTS supports current language."""

    def validate_connection(self):
        """Ensure the TTS can connect to it's backend.

        This can mean for example being able to launch the correct executable
        or contact a webserver.
        """

    def get_tts_class(self):
        """Return TTS class that this validator is for."""


class ConcatTTS(TTS):
    def __init__(self, *args, **kwargs):
        super(ConcatTTS, self).__init__(*args, **kwargs)
        self.time_step = float(self.config.get("time_step", 0.1))
        if self.time_step < 0.1:
            self.time_step = 0.1
        self.sound_files_path = self.config.get("sounds")
        self.channels = self.config.get("channels", "1")
        self.rate = self.config.get("rate", "16000")

    def sentence_to_files(self, sentence):
        """ list of ordered files to concatenate and form final wav file
        return files (list) , phonemes (list)
        """
        raise NotImplementedError

    def concat(self, files, wav_file):
        """ generate output wav file from input files """
        cmd = ["sox"]
        for file in files:
            if not isfile(file):
                continue
            cmd.append("-c")
            cmd.append(self.channels)
            cmd.append("-r")
            cmd.append(self.rate)
            cmd.append(file)

        cmd.append(wav_file)
        cmd.append("channels")
        cmd.append(self.channels)
        cmd.append("rate")
        cmd.append(self.rate)
        LOG.info(subprocess.check_output(cmd))
        return wav_file

    def get_tts(self, sentence, wav_file, lang=None):
        """
            get data from tts.

            Args:
                sentence(str): Sentence to synthesize
                wav_file(str): output file

            Returns:
                tuple: (wav_file, phoneme)
        """
        files, phonemes = self.sentence_to_files(sentence)
        wav_file = self.concat(files, wav_file)
        return wav_file, phonemes


class RemoteTTSException(Exception):
    pass


class RemoteTTSTimeoutException(RemoteTTSException):
    pass


class RemoteTTS(TTS):
    """
    Abstract class for a Remote TTS engine implementation.
    This class is only provided for backwards compatibility
    Usage is discouraged
    """

    def __init__(self, lang, config, url, api_path, validator):
        super(RemoteTTS, self).__init__(lang, config, validator)
        self.api_path = api_path
        self.auth = None
        self.url = config.get('url', url).rstrip('/')

    def build_request_params(self, sentence):
        pass

    def get_tts(self, sentence, wav_file, lang=None):
        r = requests.get(
            self.url + self.api_path, params=self.build_request_params(sentence),
            timeout=10, verify=False, auth=self.auth)
        if r.status_code != 200:
            return None
        with open(wav_file, 'wb') as f:
            f.write(r.content)
        return wav_file, None


class TTSMutator:
    def __init__(self, sound_file, config=None):
        self.config = config or {}
        self.sound_file = sound_file
        sox = find_executable("sox")
        if sox is None:
            raise ImportError("could not find 'sox' executable")
        self.effects = [sox, sound_file, sound_file]

    def apply(self, output=None):
        if len(list(self.config.keys())):
            for effect in self.config:
                params = self.config[effect]
                if effect == "pitch":
                    self.pitch(**params)
                elif effect == "phaser":
                    self.phaser(**params)
                elif effect == "flanger":
                    self.flanger(**params)
                elif effect == "reverb":
                    self.reverb(**params)
                elif effect == "tempo":
                    self.tempo(**params)
                elif effect == "treble":
                    self.treble(**params)
                elif effect == "tremolo":
                    self.tremolo(**params)
                elif effect == "reverse":
                    self.reverse()
                elif effect == "speed":
                    self.speed(**params)
                elif effect == "chorus":
                    self.chorus(**params)
                elif effect == "echo":
                    self.echo(**params)
                elif effect == "bend":
                    self.bend(**params)
                elif effect == "stretch":
                    self.stretch(**params)
                elif effect == "overdrive":
                    self.overdrive(**params)
                elif effect == "bass":
                    self.bass(**params)
                elif effect == "allpass":
                    self.allpass(**params)
                elif effect == "bandpass":
                    self.bandpass(**params)
                elif effect == "bandreject":
                    self.bandreject(**params)
                elif effect == "compand":
                    self.compand(**params)
                elif effect == "contrast":
                    self.contrast(**params)
                elif effect == "equalizer":
                    self.equalizer(**params)
                elif effect == "gain":
                    self.gain(**params)
                elif effect == "highpass":
                    self.highpass(**params)
                elif effect == "lowpass":
                    self.lowpass(**params)
                elif effect == "loudness":
                    self.loudness(**params)
                elif effect == "noisered":
                    self.noisered(**params)
            if output:
                self.save(output)

    def save(self, out_path=None):
        out_path = out_path or self.sound_file
        self.effects[2] = out_path
        subprocess.call(self.effects, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
        return out_path

    def pitch(self, n_semitones, quick=False):
        """
        Pitch shift the audio without changing the tempo.

        This effect uses the WSOLA algorithm. The audio is chopped up into segments which are then shifted in the time domain and overlapped (cross-faded) at points where their waveforms are most similar as determined by measurement of least squares.

        Parameters:
        n_semitones : float
        The number of semitones to shift. Can be positive or negative.

        quick : bool, default=False
        If True, this effect will run faster but with lower sound quality.
        """
        LOG.debug("pitch")
        effect_args = ['pitch']

        if quick:
            effect_args.append('-q')

        effect_args.append('{:f}'.format(n_semitones * 100.))
        self.effects += effect_args

    def phaser(self, gain_in=0.8, gain_out=0.74, delay=3, decay=0.4,
               speed=0.5, modulation_shape='sinusoidal'):
        """
        Apply a phasing effect to the audio.

            Parameters:
            gain_in : float, default=0.8
            Input volume between 0 and 1

            gain_out: float, default=0.74
            Output volume between 0 and 1

            delay : float, default=3
            Delay in miliseconds between 0 and 5

            decay : float, default=0.4
            Decay relative to gain_in, between 0.1 and 0.5.

            speed : float, default=0.5
            Modulation speed in Hz, between 0.1 and 2

            modulation_shape : str, defaul=’sinusoidal’
            Modulation shpae. One of ‘sinusoidal’ or ‘triangular’
        """
        LOG.debug("phaser")
        effect_args = [
            'phaser',
            '{:f}'.format(gain_in),
            '{:f}'.format(gain_out),
            '{:f}'.format(delay),
            '{:f}'.format(decay),
            '{:f}'.format(speed)
        ]

        if modulation_shape == 'sinusoidal':
            effect_args.append('-s')
        elif modulation_shape == 'triangular':
            effect_args.append('-t')
        self.effects += effect_args

    def flanger(self, delay=0, depth=2, regen=0, width=71, speed=0.5,
                shape='sine', phase=25, interp='linear'):
        """
        Apply a flanging effect to the audio.

        Parameters:
        delay : float, default=0
        Base delay (in miliseconds) between 0 and 30.

        depth : float, default=2
        Added swept delay (in miliseconds) between 0 and 10.

        regen : float, default=0
        Percentage regeneration between -95 and 95.

        width : float, default=71,
        Percentage of delayed signal mixed with original between 0 and 100.

        speed : float, default=0.5
        Sweeps per second (in Hz) between 0.1 and 10.

        shape : ‘sine’ or ‘triangle’, default=’sine’
        Swept wave shape

        phase : float, default=25
        Swept wave percentage phase-shift for multi-channel flange between 0 and 100. 0 = 100 = same phase on each channel

        interp : ‘linear’ or ‘quadratic’, default=’linear’
        Digital delay-line interpolation type.
        """
        LOG.debug("flanger")
        effect_args = [
            'flanger',
            '{:f}'.format(delay),
            '{:f}'.format(depth),
            '{:f}'.format(regen),
            '{:f}'.format(width),
            '{:f}'.format(speed),
            '{}'.format(shape),
            '{:f}'.format(phase),
            '{}'.format(interp)
        ]
        self.effects += effect_args

    def reverb(self, reverberance=50, high_freq_damping=50, room_scale=100,
               stereo_depth=100, pre_delay=0, wet_gain=0, wet_only=False):
        """
        Add reverberation to the audio using the ‘freeverb’ algorithm. A reverberation effect is sometimes desirable for concert halls that are too small or contain so many people that the hall’s natural reverberance is diminished. Applying a small amount of stereo reverb to a (dry) mono signal will usually make it sound more natural.

        Parameters:
        reverberance : float, default=50
        Percentage of reverberance

        high_freq_damping : float, default=50
        Percentage of high-frequency damping.

        room_scale : float, default=100
        Scale of the room as a percentage.

        stereo_depth : float, default=100
        Stereo depth as a percentage.

        pre_delay : float, default=0
        Pre-delay in milliseconds.

        wet_gain : float, default=0
        Amount of wet gain in dB

        wet_only : bool, default=False
        If True, only outputs the wet signal.
        """
        LOG.debug("reverb")
        effect_args = ['reverb']

        if wet_only:
            effect_args.append('-w')

        effect_args.extend([
            '{:f}'.format(reverberance),
            '{:f}'.format(high_freq_damping),
            '{:f}'.format(room_scale),
            '{:f}'.format(stereo_depth),
            '{:f}'.format(pre_delay),
            '{:f}'.format(wet_gain)
        ])
        self.effects += effect_args

    def tempo(self, factor, audio_type=None, quick=False):
        """Time stretch audio without changing pitch.

        This effect uses the WSOLA algorithm. The audio is chopped up into segments which are then shifted in the time domain and overlapped (cross-faded) at points where their waveforms are most similar as determined by measurement of least squares.

        Parameters:
        factor : float
        The ratio of new tempo to the old tempo. For ex. 1.1 speeds up the tempo by 10%; 0.9 slows it down by 10%.

        audio_type : str
        Type of audio, which optimizes algorithm parameters. One of:
        m : Music,
        s : Speech,
        l : Linear (useful when factor is close to 1),
        quick : bool, default=False
        If True, this effect will run faster but with lower sound quality.
        """
        LOG.debug("tempo")
        if factor <= 0:
            raise ValueError("factor must be a positive number")

        if factor < 0.5 or factor > 2:
            LOG.warning(
                "Using an extreme time stretching factor. "
                "Quality of results will be poor"
            )

        if abs(factor - 1.0) <= 0.1:
            LOG.warning(
                "For this stretch factor, "
                "the stretch effect has better performance."
            )

        if audio_type not in [None, 'm', 's', 'l']:
            raise ValueError(
                "audio_type must be one of None, 'm', 's', or 'l'."
            )

        if not isinstance(quick, bool):
            raise ValueError("quick must be a boolean.")

        effect_args = ['tempo']

        if quick:
            effect_args.append('-q')

        if audio_type is not None:
            effect_args.append('-{}'.format(audio_type))

        effect_args.append('{:f}'.format(factor))
        self.effects += effect_args

    def treble(self, gain_db, frequency=3000.0, slope=0.5):
        """
        Boost or cut the treble (lower) frequencies of the audio using a two-pole shelving filter with a response similar to that of a standard hi-fi’s tone-controls. This is also known as shelving equalisation.

        The filters are described in detail in http://musicdsp.org/files/Audio-EQ-Cookbook.txt

        Parameters:
        gain_db : float
        The gain at the Nyquist frequency. For a large cut use -20, for a large boost use 20.

        frequency : float, default=100.0
        The filter’s cutoff frequency in Hz.

        slope : float, default=0.5
        The steepness of the filter’s shelf transition. For a gentle slope use 0.3, and use 1.0 for a steep slope.

        """
        LOG.debug("treble")
        effect_args = [
            'treble', '{:f}'.format(gain_db), '{:f}'.format(frequency),
            '{:f}s'.format(slope)
        ]

        self.effects.extend(effect_args)

    def tremolo(self, speed=6.0, depth=40.0):
        """
        Apply a tremolo (low frequency amplitude modulation) effect to the audio. The tremolo frequency in Hz is giv en by speed, and the depth as a percentage by depth (default 40).

        Parameters:
        speed : float
        Tremolo speed in Hz.

        depth : float
        Tremolo depth as a percentage of the total amplitude.

        """
        LOG.debug("tremolo")
        effect_args = [
            'tremolo',
            '{:f}'.format(speed),
            '{:f}'.format(depth)
        ]

        self.effects.extend(effect_args)

    def reverse(self):
        """Reverse the audio completely"""
        LOG.debug("reverse")
        effect_args = ['reverse']
        self.effects.extend(effect_args)

    def speed(self, factor):
        """
        Adjust the audio speed (pitch and tempo together).

        Technically, the speed effect only changes the sample rate information, leaving the samples themselves untouched. The rate effect is invoked automatically to resample to the output sample rate, using its default quality/speed. For higher quality or higher speed resampling, in addition to the speed effect, specify the rate effect with the desired quality option.

        Parameters:
        factor : float
        The ratio of the new speed to the old speed. For ex. 1.1 speeds up the audio by 10%; 0.9 slows it down by 10%. Note - this argument is the inverse of what is passed to the sox stretch effect for consistency with speed.
        """
        LOG.debug("speed: " + str(factor))

        if factor < 0.5 or factor > 2:
            LOG.warning(
                "Using an extreme factor. Quality of results will be poor"
            )

        effect_args = ['speed', '{:f}'.format(factor)]

        self.effects.extend(effect_args)

    def chorus(self, gain_in=0.5, gain_out=0.9, n_voices=3, delays=None,
               decays=None, speeds=None, depths=None, shapes=None):
        """
        Add a chorus effect to the audio. This can makeasingle vocal sound like a chorus, but can also be applied to instrumentation.

        Chorus resembles an echo effect with a short delay, but whereas with echo the delay is constant, with chorus, it is varied using sinusoidal or triangular modulation. The modulation depth defines the range the modulated delay is played before or after the delay. Hence the delayed sound will sound slower or faster, that is the delayed sound tuned around the original one, like in a chorus where some vocals are slightly off key.

        Parameters:
        gain_in : float, default=0.3
        The time in seconds over which the instantaneous level of the input signal is averaged to determine increases in volume.

        gain_out : float, default=0.8
        The time in seconds over which the instantaneous level of the input signal is averaged to determine decreases in volume.

        n_voices : int, default=3
        The number of voices in the chorus effect.

        delays : list of floats > 20 or None, default=None
        If a list, the list of delays (in miliseconds) of length n_voices. If None, the individual delay parameters are chosen automatically to be between 40 and 60 miliseconds.

        decays : list of floats or None, default=None
        If a list, the list of decays (as a fraction of gain_in) of length n_voices. If None, the individual decay parameters are chosen automatically to be between 0.3 and 0.4.

        speeds : list of floats or None, default=None
        If a list, the list of modulation speeds (in Hz) of length n_voices If None, the individual speed parameters are chosen automatically to be between 0.25 and 0.4 Hz.

        depths : list of floats or None, default=None
        If a list, the list of depths (in miliseconds) of length n_voices. If None, the individual delay parameters are chosen automatically to be between 1 and 3 miliseconds.

        shapes : list of ‘s’ or ‘t’ or None, deault=None
        If a list, the list of modulation shapes - ‘s’ for sinusoidal or ‘t’ for triangular - of length n_voices. If None, the individual shapes are chosen automatically.
        """
        LOG.debug("chorus")
        if gain_in <= 0 or gain_in > 1:
            raise ValueError("gain_in must be a number between 0 and 1.")
        if gain_out <= 0 or gain_out > 1:
            raise ValueError("gain_out must be a number between 0 and 1.")
        if not isinstance(n_voices, int) or n_voices <= 0:
            raise ValueError("n_voices must be a positive integer.")

            # validate delays
        if not (delays is None or isinstance(delays, list)):
            raise ValueError("delays must be a list or None")
        if delays is not None:
            if len(delays) != n_voices:
                raise ValueError("the length of delays must equal n_voices")
        else:
            delays = [random.uniform(40, 60) for _ in range(n_voices)]

            # validate decays
        if not (decays is None or isinstance(decays, list)):
            raise ValueError("decays must be a list or None")
        if decays is not None:
            if len(decays) != n_voices:
                raise ValueError("the length of decays must equal n_voices")
        else:
            decays = [random.uniform(0.3, 0.4) for _ in range(n_voices)]

            # validate speeds
        if not (speeds is None or isinstance(speeds, list)):
            raise ValueError("speeds must be a list or None")
        if speeds is not None:
            if len(speeds) != n_voices:
                raise ValueError("the length of speeds must equal n_voices")
        else:
            speeds = [random.uniform(0.25, 0.4) for _ in range(n_voices)]

            # validate depths
        if not (depths is None or isinstance(depths, list)):
            raise ValueError("depths must be a list or None")
        if depths is not None:
            if len(depths) != n_voices:
                raise ValueError("the length of depths must equal n_voices")
        else:
            depths = [random.uniform(1.0, 3.0) for _ in range(n_voices)]

            # validate shapes
        if not (shapes is None or isinstance(shapes, list)):
            raise ValueError("shapes must be a list or None")
        if shapes is not None:
            if len(shapes) != n_voices:
                raise ValueError("the length of shapes must equal n_voices")
            if any((p not in ['t', 's']) for p in shapes):
                raise ValueError("the elements of shapes must be 's' or 't'")
        else:
            shapes = [random.choice(['t', 's']) for _ in range(n_voices)]

        effect_args = ['chorus', '{}'.format(gain_in), '{}'.format(gain_out)]

        for i in range(n_voices):
            effect_args.extend([
                '{:f}'.format(delays[i]),
                '{:f}'.format(decays[i]),
                '{:f}'.format(speeds[i]),
                '{:f}'.format(depths[i]),
                '-{}'.format(shapes[i])
            ])

        self.effects.extend(effect_args)

    def echo(self, gain_in=0.8, gain_out=0.9, n_echos=1, delays=None,
             decays=None):
        """
        Add echoing to the audio.

        Echoes are reflected sound and can occur naturally amongst mountains (and sometimes large buildings) when talking or shouting; digital echo effects emulate this behav- iour and are often used to help fill out the sound of a single instrument or vocal. The time differ- ence between the original signal and the reflection is the ‘delay’ (time), and the loudness of the reflected signal is the ‘decay’. Multiple echoes can have different delays and decays.

        Parameters:
        gain_in : float, default=0.8
        Input volume, between 0 and 1

        gain_out : float, default=0.9
        Output volume, between 0 and 1

        n_echos : int, default=1
        Number of reflections

        delays : list, default=[60]
        List of delays in miliseconds

        decays : list, default=[0.4]
        List of decays, relative to gain in between 0 and 1

        """
        delays = delays or [60]
        decays = decays or [0.4]
        LOG.debug("echo")
        if gain_in <= 0 or gain_in > 1:
            raise ValueError("gain_in must be a number between 0 and 1.")

        if gain_out <= 0 or gain_out > 1:
            raise ValueError("gain_out must be a number between 0 and 1.")

        if not isinstance(n_echos, int) or n_echos <= 0:
            raise ValueError("n_echos must be a positive integer.")

            # validate delays
        if not isinstance(delays, list):
            raise ValueError("delays must be a list")

        if len(delays) != n_echos:
            raise ValueError("the length of delays must equal n_echos")

            # validate decays
        if not isinstance(decays, list):
            raise ValueError("decays must be a list")

        if len(decays) != n_echos:
            raise ValueError("the length of decays must equal n_echos")

        effect_args = ['echo', '{:f}'.format(gain_in), '{:f}'.format(gain_out)]

        for i in range(n_echos):
            effect_args.extend([
                '{}'.format(delays[i]),
                '{}'.format(decays[i])
            ])

        self.effects.extend(effect_args)

    def bend(self, n_bends, start_times, end_times, cents, frame_rate=25,
             oversample_rate=16):
        """
        Changes pitch by specified amounts at specified times. The pitch-bending algorithm utilises the Discrete Fourier Transform (DFT) at a particular frame rate and over-sampling rate.

        Parameters:
        n_bends : int
        The number of intervals to pitch shift

        start_times : list of floats
        A list of absolute start times (in seconds), in order

        end_times : list of floats
        A list of absolute end times (in seconds) in order. [start_time, end_time] intervals may not overlap!

        cents : list of floats
        A list of pitch shifts in cents. A positive value shifts the pitch up, a negative value shifts the pitch down.

        frame_rate : int, default=25
        The number of DFT frames to process per second, between 10 and 80

        oversample_rate: int, default=16
        The number of frames to over sample per second, between 4 and 32
        """
        LOG.debug("bend")
        if not isinstance(n_bends, int) or n_bends < 1:
            raise ValueError("n_bends must be a positive integer.")

        if not isinstance(start_times, list) or len(start_times) != n_bends:
            raise ValueError("start_times must be a list of length n_bends.")

        if any([(p <= 0) for p in start_times]):
            raise ValueError("start_times must be positive floats.")

        if sorted(start_times) != start_times:
            raise ValueError("start_times must be in increasing order.")

        if not isinstance(end_times, list) or len(end_times) != n_bends:
            raise ValueError("end_times must be a list of length n_bends.")

        if any([(p <= 0) for p in end_times]):
            raise ValueError("end_times must be positive floats.")

        if sorted(end_times) != end_times:
            raise ValueError("end_times must be in increasing order.")

        if any([e <= s for s, e in zip(start_times, end_times)]):
            raise ValueError(
                "end_times must be element-wise greater than start_times."
            )

        if any([e > s for s, e in zip(start_times[1:], end_times[:-1])]):
            raise ValueError(
                "[start_time, end_time] intervals must be non-overlapping."
            )

        if not isinstance(cents, list) or len(cents) != n_bends:
            raise ValueError("cents must be a list of length n_bends.")

        if (not isinstance(frame_rate, int) or
                frame_rate < 10 or frame_rate > 80):
            raise ValueError("frame_rate must be an integer between 10 and 80")

        if (not isinstance(oversample_rate, int) or
                oversample_rate < 4 or oversample_rate > 32):
            raise ValueError(
                "oversample_rate must be an integer between 4 and 32."
            )

        effect_args = [
            'bend',
            '-f', '{}'.format(frame_rate),
            '-o', '{}'.format(oversample_rate)
        ]

        last = 0
        for i in range(n_bends):
            t_start = round(start_times[i] - last, 2)
            t_end = round(end_times[i] - start_times[i], 2)
            effect_args.append(
                '{:f},{:f},{:f}'.format(t_start, cents[i], t_end)
            )
            last = end_times[i]

        self.effects.extend(effect_args)

    def stretch(self, factor, window=20):
        """
        Change the audio duration (but not its pitch). Unless factor is close to 1, use the tempo effect instead.

        This effect is broadly equivalent to the tempo effect with search set to zero, so in general, its results are comparatively poor; it is retained as it can sometimes out-perform tempo for small factors.

        Parameters:
        factor : float
        The ratio of the new tempo to the old tempo. For ex. 1.1 speeds up the tempo by 10%; 0.9 slows it down by 10%. Note - this argument is the inverse of what is passed to the sox stretch effect for consistency with tempo.

        window : float, default=20
        Window size in miliseconds
        """
        LOG.debug("stretch")
        if factor <= 0:
            raise ValueError("factor must be a positive number")

        if factor < 0.5 or factor > 2:
            LOG.warning(
                "Using an extreme time stretching factor. "
                "Quality of results will be poor"
            )

        if abs(factor - 1.0) > 0.1:
            LOG.warning(
                "For this stretch factor, "
                "the tempo effect has better performance."
            )

        if window <= 0:
            raise ValueError(
                "window must be a positive number."
            )

        effect_args = ['stretch', '{:f}'.format(factor), '{:f}'.format(window)]

        self.effects.extend(effect_args)

    def overdrive(self, gain_db=20.0, colour=20.0):
        """
        Apply non-linear distortion.

        Parameters:
        gain_db : float, default=20
        Controls the amount of distortion (dB).

        colour : float, default=20
        Controls the amount of even harmonic content in the output (dB).
        """
        LOG.debug("overdrive")
        effect_args = [
            'overdrive',
            '{:f}'.format(gain_db),
            '{:f}'.format(colour)
        ]
        self.effects.extend(effect_args)

    def bass(self, gain_db, frequency=100.0, slope=0.5):
        """
        Boost or cut the bass (lower) frequencies of the audio using a two-pole shelving filter with a response similar to that of a standard hi-fi’s tone-controls. This is also known as shelving equalisation.

        The filters are described in detail in http://musicdsp.org/files/Audio-EQ-Cookbook.txt

        Parameters:
        gain_db : float
        The gain at 0 Hz. For a large cut use -20, for a large boost use 20.

        frequency : float, default=100.0
        The filter’s cutoff frequency in Hz.

        slope : float, default=0.5
        The steepness of the filter’s shelf transition. For a gentle slope use 0.3, and use 1.0 for a steep slope.
        """
        LOG.debug("bass")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        effect_args = [
            'bass', '{:f}'.format(gain_db), '{:f}'.format(frequency),
            '{:f}s'.format(slope)
        ]

        self.effects.extend(effect_args)

    def allpass(self, frequency, width_q=2.0):
        """
        Apply a two-pole all-pass filter. An all-pass filter changes the audio’s frequency to phase relationship without changing its frequency to amplitude relationship. The filter is described in detail in at http://musicdsp.org/files/Audio-EQ-Cookbook.txt

        Parameters:
        frequency : float
        The filter’s center frequency in Hz.

        width_q : float, default=2.0
        The filter’s width as a Q-factor.
        """
        LOG.debug("allpass")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        effect_args = [
            'allpass', '{:f}'.format(frequency), '{:f}q'.format(width_q)
        ]

        self.effects.extend(effect_args)

    def bandpass(self, frequency, width_q=2.0, constant_skirt=False):
        """
        Apply a two-pole Butterworth band-pass filter with the given central frequency, and (3dB-point) band-width. The filter rolls off at 6dB per octave (20dB per decade) and is described in detail in http://musicdsp.org/files/Audio-EQ-Cookbook.txt
        Parameters:
        frequency : float
        The filter’s center frequency in Hz.

        width_q : float, default=2.0
        The filter’s width as a Q-factor.

        constant_skirt : bool, default=False
        If True, selects constant skirt gain (peak gain = width_q). If False, selects constant 0dB peak gain.
        """
        LOG.debug("bandpass")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        if not isinstance(constant_skirt, bool):
            raise ValueError("constant_skirt must be a boolean.")

        effect_args = ['bandpass']

        if constant_skirt:
            effect_args.append('-c')

        effect_args.extend(['{:f}'.format(frequency), '{:f}q'.format(width_q)])

        self.effects.extend(effect_args)

    def bandreject(self, frequency, width_q=2.0):
        """
        Apply a two-pole Butterworth band-reject filter with the given central frequency, and (3dB-point) band-width. The filter rolls off at 6dB per octave (20dB per decade) and is described in detail in http://musicdsp.org/files/Audio-EQ-Cookbook.txt

        Parameters:
        frequency : float
        The filter’s center frequency in Hz.

        width_q : float, default=2.0
        The filter’s width as a Q-factor.

        constant_skirt : bool, default=False
        If True, selects constant skirt gain (peak gain = width_q). If False, selects constant 0dB peak gain.
        """
        LOG.debug("bandreject")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        effect_args = [
            'bandreject', '{:f}'.format(frequency), '{:f}q'.format(width_q)
        ]

        self.effects.extend(effect_args)

    def compand(self, attack_time=0.3, decay_time=0.8, soft_knee_db=6.0,
                tf_points=None):
        """
        Compand (compress or expand) the dynamic range of the audio.

        Parameters:
        attack_time : float, default=0.3
        The time in seconds over which the instantaneous level of the input signal is averaged to determine increases in volume.

        decay_time : float, default=0.8
        The time in seconds over which the instantaneous level of the input signal is averaged to determine decreases in volume.

        soft_knee_db : float or None, default=6.0
        The ammount (in dB) for which the points at where adjacent line segments on the transfer function meet will be rounded. If None, no soft_knee is applied.

        tf_points : list of tuples
        Transfer function points as a list of tuples corresponding to points in (dB, dB) defining the compander’s transfer function.
        """
        tf_points = tf_points or [(-70, -70), (-60, -20), (0, 0)]
        LOG.debug("compand")
        if attack_time <= 0:
            raise ValueError("attack_time must be a positive number.")

        if decay_time <= 0:
            raise ValueError("decay_time must be a positive number.")

        if attack_time > decay_time:
            LOG.warning(
                "attack_time is larger than decay_time.\n"
                "For most situations, attack_time should be shorter than "
                "decay time because the human ear is more sensitive to sudden "
                "loud music than sudden soft music."
            )

        if not isinstance(tf_points, list):
            raise TypeError("tf_points must be a list.")
        if len(tf_points) == 0:
            raise ValueError("tf_points must have at least one point.")
        if any(not isinstance(pair, tuple) for pair in tf_points):
            raise ValueError("elements of tf_points must be pairs")
        if any(len(pair) != 2 for pair in tf_points):
            raise ValueError("Tuples in tf_points must be length 2")
        if any((p[0] > 0 or p[1] > 0) for p in tf_points):
            raise ValueError("Tuple values in tf_points must be <= 0 (dB).")
        if len(tf_points) > len(set([p[0] for p in tf_points])):
            raise ValueError("Found duplicate x-value in tf_points.")

        tf_points = sorted(
            tf_points,
            key=lambda tf_points: tf_points[0]
        )
        transfer_list = []
        for point in tf_points:
            transfer_list.extend([
                "{:f}".format(point[0]), "{:f}".format(point[1])
            ])

        effect_args = [
            'compand',
            "{:f},{:f}".format(attack_time, decay_time)
        ]

        if soft_knee_db is not None:
            effect_args.append(
                "{:f}:{}".format(soft_knee_db, ",".join(transfer_list))
            )
        else:
            effect_args.append(",".join(transfer_list))

        self.effects.extend(effect_args)

    def contrast(self, amount=75):
        """
        Comparable with compression, this effect modifies an audio signal to make it sound louder.

        Parameters:
        amount : float
        Amount of enhancement between 0 and 100.

        """
        LOG.debug("contrast")
        if amount < 0 or amount > 100:
            raise ValueError('amount must be a number between 0 and 100.')

        effect_args = ['contrast', '{:f}'.format(amount)]

        self.effects.extend(effect_args)

    def equalizer(self, frequency, width_q, gain_db):
        """
        Apply a two-pole peaking equalisation (EQ) filter to boost or reduce around a given frequency. This effect can be applied multiple times to produce complex EQ curves.

        Parameters:
        frequency : float
        The filter’s central frequency in Hz.

        width_q : float
        The filter’s width as a Q-factor.

        gain_db : float
        The filter’s gain in dB.
        """
        LOG.debug("equalizer")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        effect_args = [
            'equalizer',
            '{:f}'.format(frequency),
            '{:f}q'.format(width_q),
            '{:f}'.format(gain_db)
        ]
        self.effects.extend(effect_args)

    def gain(self, gain_db=0.0, normalize=True, limiter=False, balance=None):
        """
        Apply amplification or attenuation to the audio signal.

        Parameters:
        gain_db : float, default=0.0
        Gain adjustment in decibels (dB).

        normalize : bool, default=True
        If True, audio is normalized to gain_db relative to full scale. If False, simply adjusts the audio power level by gain_db.

        limiter : bool, default=False
        If True, a simple limiter is invoked to prevent clipping.

        balance : str or None, default=None
        Balance gain across channels. Can be one of:
        None applies no balancing (default)
        ‘e’ applies gain to all channels other than that with the
        highest peak level, such that all channels attain the same peak level
        ‘B’ applies gain to all channels other than that with the
        highest RMS level, such that all channels attain the same RMS level
        ‘b’ applies gain with clipping protection to all channels other
        than that with the highest RMS level, such that all channels attain the same RMS level
        If normalize=True, ‘B’ and ‘b’ are equivalent.
        """
        LOG.debug("gain")
        if balance not in [None, 'e', 'B', 'b']:
            raise ValueError("balance must be one of None, 'e', 'B', or 'b'.")

        effect_args = ['gain']

        if balance is not None:
            effect_args.append('-{}'.format(balance))

        if normalize:
            effect_args.append('-n')

        if limiter:
            effect_args.append('-l')

        effect_args.append('{:f}'.format(gain_db))
        self.effects.extend(effect_args)

    def highpass(self, frequency, width_q=0.707, n_poles=2):
        """
        Apply a high-pass filter with 3dB point frequency. The filter can be either single-pole or double-pole. The filters roll off at 6dB per pole per octave (20dB per pole per decade).

        Parameters:
        frequency : float
        The filter’s cutoff frequency in Hz.

        width_q : float, default=0.707
        The filter’s width as a Q-factor. Applies only when n_poles=2. The default gives a Butterworth response.

        n_poles : int, default=2
        The number of poles in the filter. Must be either 1 or 2
        """
        LOG.debug("highpass")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        if n_poles not in [1, 2]:
            raise ValueError("n_poles must be 1 or 2.")

        effect_args = [
            'highpass', '-{}'.format(n_poles), '{:f}'.format(frequency)
        ]

        if n_poles == 2:
            effect_args.append('{:f}q'.format(width_q))

        self.effects.extend(effect_args)

    def lowpass(self, frequency, width_q=0.707, n_poles=2):
        """
        Apply a low-pass filter with 3dB point frequency. The filter can be either single-pole or double-pole.
        The filters roll off at 6dB per pole per octave (20dB per pole per decade).

        Parameters:
        frequency : float
        The filter’s cutoff frequency in Hz.

        width_q : float, default=0.707
        The filter’s width as a Q-factor. Applies only when n_poles=2. The default gives a Butterworth response.

        n_poles : int, default=2
        The number of poles in the filter. Must be either 1 or 2
        """
        LOG.debug("lowpass")
        if frequency <= 0:
            raise ValueError("frequency must be a positive number.")

        if width_q <= 0:
            raise ValueError("width_q must be a positive number.")

        if n_poles not in [1, 2]:
            raise ValueError("n_poles must be 1 or 2.")

        effect_args = [
            'lowpass', '-{}'.format(n_poles), '{:f}'.format(frequency)
        ]

        if n_poles == 2:
            effect_args.append('{:f}q'.format(width_q))

        self.effects.extend(effect_args)

    def loudness(self, gain_db=-10.0, reference_level=65.0):
        """
        Loudness control. Similar to the gain effect, but provides equalisation for the human auditory system.

        The gain is adjusted by gain_db and the signal is equalised according to ISO 226 w.r.t. reference_level.

        Parameters:
        gain_db : float, default=-10.0
        Loudness adjustment amount (in dB)

        reference_level : float, default=65.0
        Reference level (in dB) according to which the signal is equalized. Must be between 50 and 75 (dB)
        """
        LOG.debug("loudness")
        if reference_level > 75 or reference_level < 50:
            raise ValueError('reference_level must be between 50 and 75')

        effect_args = [
            'loudness',
            '{:f}'.format(gain_db),
            '{:f}'.format(reference_level)
        ]
        self.effects.extend(effect_args)

    def noisered(self, profile_path, amount=0.5):
        """
        Reduce noise in the audio signal by profiling and filtering. This effect is moderately effective at removing consistent background noise such as hiss or hum.

        Parameters:
        profile_path : str
        Path to a noise profile file. This file can be generated using the noiseprof effect.

        amount : float, default=0.5
        How much noise should be removed is specified by amount. Should be between 0 and 1. Higher numbers will remove more noise but present a greater likelihood of removing wanted components of the audio signal.
        """
        # TODO auto gen profile file
        LOG.info("noisered")
        if not exists(profile_path):
            raise IOError(
                "profile_path {} does not exist.".format(profile_path))

        if amount < 0 or amount > 1:
            raise ValueError("amount must be a number between 0 and 1.")

        effect_args = [
            'noisered',
            profile_path,
            '{:f}'.format(amount)
        ]
        self.effects.extend(effect_args)
