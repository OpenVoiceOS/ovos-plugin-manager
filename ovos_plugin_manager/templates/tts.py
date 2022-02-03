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
from os.path import isfile, join, splitext
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from time import time, sleep

import requests
from ovos_plugin_manager.g2p import OVOSG2PFactory
from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache, hash_sentence
from ovos_utils import resolve_resource_file
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.enclosure.api import EnclosureAPI
from ovos_utils.file_utils import get_cache_directory
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG
from ovos_utils.messagebus import Message, FakeBus as BUS
from ovos_utils.metrics import Stopwatch
from ovos_utils.signal import check_for_signal, create_signal
from ovos_utils.sound import play_audio

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)


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
        self.tts = None
        self._now_playing = None

    def init(self, tts):
        self.tts = tts

    @property
    def bus(self):
        if self.tts:
            return self.tts.bus
        return None

    def clear_queue(self):
        """Remove all pending playbacks."""
        while not self.queue.empty():
            self.queue.get()
        try:
            self.p.terminate()
        except Exception:
            pass

    def on_start(self):
        self.blink(0.5)
        if not self._processing_queue:
            self._processing_queue = True
            self.tts.begin_audio()

    def on_end(self, listen=False):
        if self._processing_queue:
            self.tts.end_audio(listen)
            self._processing_queue = False
        self.blink(0.2)

    def _play(self):
        listen = False
        try:
            if len(self._now_playing) == 5:
                # new mycroft style
                snd_type, data, visemes, ident, listen = self._now_playing
            else:
                # old mycroft style
                snd_type, data, visemes, ident = self._now_playing
            self.on_start()
            self.p = play_audio(data)
            if visemes:
                self.show_visemes(visemes)
            if self.p:
                self.p.communicate()
                self.p.wait()
            if self.queue.empty():
                self.on_end(listen)
        except Empty:
            pass
        except Exception as e:
            LOG.exception(e)
            if self._processing_queue:
                self.on_end(listen)
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
        while not self._terminated:
            while self._paused:
                sleep(0.2)
            try:
                self._now_playing = self.queue.get(timeout=2)
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

    def __init__(self, lang="en-us", config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        self.log_timestamps = False

        try:
            config_core = read_mycroft_config() or {}
        except FileNotFoundError:
            config_core = {}

        config = config or config_core.get("tts", {})
        config["lang"] = config.get("lang") or config_core.get("lang")

        self.stopwatch = Stopwatch()
        self.tts_name = self.__class__.__name__
        self.bus = BUS()  # initialized in "init" step
        self.lang = lang or config.get("lang") or 'en-us'
        self.config = config or {}
        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []
        self.log_timestamps = self.config.get("log_timestamps", False)

        self.voice = self.config.get("voice") or "default"
        # TODO can self.filename be deprecated ? is it used anywhere at all?
        cache_dir = get_cache_directory(self.tts_name)
        self.filename = join(cache_dir, 'tts.' + self.audio_ext)
        self.enclosure = None
        random.seed()
        self.queue = Queue()
        self.playback = PlaybackThread(self.queue)
        # NOTE: self.playback.start() was moved to init method
        #   playback queue is not wanted if we only care about get_tts
        #   init is called by mycroft, but non mycroft usage wont call it,
        #   outside mycroft the enclosure is not set, bus is dummy and
        #   playback thread is not used
        self.spellings = self.load_spellings()
        tts_id = join(self.tts_name, self.voice, self.lang)
        self.cache = TextToSpeechCache(
            self.config, tts_id, self.audio_ext
        )
        self.cache.curate()
        self.g2p = OVOSG2PFactory.create(config_core)
        self.add_metric({"metric_type": "tts.init"})

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
        # This check will clear the "signal", in case it is still there for some reasons
        check_for_signal("isSpeaking")
        # this will create it again
        create_signal("isSpeaking")
        # Create signals informing start of speech
        self.bus.emit(Message("recognizer_loop:audio_output_start"))
        self.add_metric({"metric_type": "tts.start"})

    def end_audio(self, listen=False):
        """Helper function for child classes to call in execute().

        Sends the recognizer_loop:audio_output_end message (indicating
        that speaking is done for the moment) as well as trigger listening
        if it has been requested. It also checks if cache directory needs
        cleaning to free up disk space.

        Arguments:
            listen (bool): indication if listening trigger should be sent.
        """

        self.bus.emit(Message("recognizer_loop:audio_output_end"))
        if listen:
            self.bus.emit(Message('mycroft.mic.listen'))

        # This check will clear the "signal"
        check_for_signal("isSpeaking")
        self.add_metric({"metric_type": "tts.end"})
        self.stopwatch.stop()
        self.cache.curate()

    def init(self, bus=None):
        """ Performs intial setup of TTS object.

        Arguments:
            bus:    Mycroft messagebus connection
        """
        self.bus = bus or BUS
        self.playback.start()
        self.playback.init(self)
        self.enclosure = EnclosureAPI(self.bus)
        self.playback.enclosure = self.enclosure
        self.add_metric({"metric_type": "tts.setup"})

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

    def validate_ssml(self, utterance):
        """Check if engine supports ssml, if not remove all tags.

        Remove unsupported / invalid tags

        Arguments:
            utterance (str): Sentence to validate

        Returns:
            str: validated_sentence
        """
        # if ssml is not supported by TTS engine remove all tags
        if not self.ssml_tags:
            return self.remove_ssml(utterance)

        # find ssml tags in string
        tags = re.findall('<[^>]*>', utterance)

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
            ident: (str) Id reference to current interaction
            listen: (bool) True if listen should be triggered at the end
                    of the utterance.
        """
        sentence = self.validate_ssml(sentence)
        self.add_metric({"metric_type": "tts.ssml.validated"})
        create_signal("isSpeaking")
        try:
            self._execute(sentence, ident, listen, **kwargs)
        except Exception:
            # If an error occurs end the audio sequence through an empty entry
            self.queue.put(EMPTY_PLAYBACK_QUEUE_TUPLE)
            # Re-raise to allow the Exception to be handled externally as well.
            raise

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

        # synth -> queue for playback
        for sentence, l in chunks:
            sentence_hash = hash_sentence(sentence)
            if sentence_hash in self.cache:  # load from cache
                audio_file, phonemes = self._get_from_cache(sentence, sentence_hash)
            else:  # synth + cache
                audio_file, phonemes = self._synth(sentence, sentence_hash, **kwargs)

            # get visemes/mouth movements
            if phonemes:
                viseme = self.viseme(phonemes)
            else:
                lang = self._get_lang(kwargs)
                viseme = self.g2p.utterance2visemes(sentence, lang)

            audio_ext = self._determine_ext(audio_file)
            self.queue.put(
                (audio_ext, str(audio_file), viseme, ident, l)
            )
            self.add_metric({"metric_type": "tts.queued"})

    def _determine_ext(self, audio_file):
        # determine audio_ext on the fly
        # do not use the ext defined in the plugin since it might not match
        # some plugins support multiple extensions
        # or have caches in different extensions
        try:
            _, audio_ext = splitext(str(audio_file))
            return audio_ext[1:]
        except:
            return self.audio_ext

    def _get_lang(self, kwargs):
        # parse requested language for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        lang = kwargs.get("lang")
        if not lang and kwargs.get("message"):
            # get lang from message object if possible
            try:
                lang = kwargs["message"].data.get("lang") or \
                       kwargs["message"].context.get("lang")
            except:  # not a mycroft message object
                pass
        return lang or self.lang

    def _synth(self, sentence, sentence_hash=None, **kwargs):
        self.add_metric({"metric_type": "tts.synth.start"})
        sentence_hash = sentence_hash or hash_sentence(sentence)
        audio = self.cache.define_audio_file(sentence_hash)

        # parse requested language for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        kwargs["lang"] = self._get_lang(kwargs)

        # filter kwargs per plugin, different plugins expose different options
        #   mycroft-core -> no kwargs
        #   ovos -> lang
        #   neon-core -> message
        kwargs = {k: v for k, v in kwargs.items()
                  if k in inspect.signature(self.get_tts).parameters
                  and k not in ["sentence", "wav_file"]}

        # finally do the TTS synth
        audio.path, phonemes = self.get_tts(sentence, str(audio), **kwargs)
        self.add_metric({"metric_type": "tts.synth.finished"})
        # cache sentence + phonemes
        self._cache_sentence(sentence, audio, phonemes, sentence_hash)
        return audio, phonemes

    def _cache_phonemes(self, sentence, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        if not phonemes:
            try:
                phonemes = self.g2p.utterance2arpa(sentence, self.lang)
                self.add_metric({"metric_type": "tts.phonemes.g2p"})
            except Exception as e:
                self.add_metric({"metric_type": "tts.phonemes.g2p.error", "error": str(e)})
        if phonemes:
            return self.save_phonemes(sentence_hash, phonemes)
        return None

    def _cache_sentence(self, sentence, audio_file, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        # RANT: why do you hate strings ChrisV?
        if isinstance(audio_file.path, str):
            audio_file.path = Path(audio_file.path)
        pho_file = self._cache_phonemes(sentence, phonemes, sentence_hash)
        self.cache.cached_sentences[sentence_hash] = (audio_file, pho_file)
        self.add_metric({"metric_type": "tts.synth.cached"})

    def _get_from_cache(self, sentence, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        phonemes = None
        audio_file, pho_file = self.cache.cached_sentences[sentence_hash]
        LOG.info(f"Found {audio_file.name} in TTS cache")
        if not pho_file:
            # guess phonemes from sentence + cache them
            pho_file = self._cache_phonemes(sentence, sentence_hash)
        if pho_file:
            phonemes = pho_file.load()
        return audio_file, phonemes

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
        try:
            self.playback.stop()
            self.playback.join()
        except Exception as e:
            pass
        self.add_metric({"metric_type": "tts.stop"})

    def __del__(self):
        self.stop()


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
