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
import hashlib
import os.path
import random
import re
from os.path import isfile, join
from queue import Queue, Empty
from threading import Thread
from time import time, sleep
from memory_tempfile import MemoryTempfile
import os

from ovos_utils import resolve_resource_file
from ovos_utils.enclosure.api import EnclosureAPI
from ovos_utils.lang.phonemes import get_phonemes
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG
from ovos_utils.messagebus import Message, FakeBus as BUS
from ovos_utils.signal import check_for_signal, create_signal
from ovos_utils.sound import play_mp3, play_wav

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)


# TODO move to ovos_utils
def get_ram_directory(folder):
    tempfile = MemoryTempfile(fallback=True)
    path = os.path.join(tempfile.gettempdir(), folder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


class PlaybackThread(Thread):
    """
        Thread class for playing back tts audio and sending
        viseme data to enclosure.
    """

    def __init__(self, queue):
        super(PlaybackThread, self).__init__()
        self.queue = queue
        self._terminated = False
        self._processing_queue = False
        self._paused = False
        self.enclosure = None

    def init(self, tts):
        self.tts = tts

    @property
    def bus(self):
        if self.tts:
            return self.tts.bus
        return None

    def clear_queue(self):
        """
            Remove all pending playbacks.
        """
        while not self.queue.empty():
            self.queue.get()
        try:
            self.p.terminate()
        except Exception:
            pass

    def run(self, cb=None):
        """
            Thread main loop. get audio and viseme data from queue
            and play.
        """
        self._paused = False
        while not self._terminated:
            while self._paused:  # barge-in support etc
                sleep(0.2)
            try:
                snd_type, data, visemes, ident = self.queue.get(timeout=2)
                self.blink(0.5)
                if not self._processing_queue:
                    self._processing_queue = True
                    self.tts.begin_audio()

                if snd_type == 'wav':
                    self.p = play_wav(data)
                elif snd_type == 'mp3':
                    self.p = play_mp3(data)

                if visemes:
                    self.show_visemes(visemes)
                self.p.communicate()
                self.p.wait()

                if self.queue.empty():
                    self.tts.end_audio()
                    self._processing_queue = False
                self.blink(0.2)
            except Empty:
                pass
            except Exception as e:
                LOG.exception(e)
                if self._processing_queue:
                    self.tts.end_audio()
                    self._processing_queue = False

    def show_visemes(self, pairs):
        """
            Send viseme data to enclosure

            Args:
                pairs(list): Visime and timing pair

            Returns:
                True if button has been pressed.
        """
        if self.enclosure:
            self.enclosure.mouth_viseme(time(), pairs)

    def pause(self):
        """pause thread"""
        self._paused = True
        # TODO is this desired?
        # if self.playback_process:
        #    self.playback_process.terminate()

    def resume(self):
        """resume thread"""
        self._paused = False

    def clear(self):
        """ Clear all pending actions for the TTS playback thread. """
        self.clear_queue()

    def blink(self, rate=1.0):
        """ Blink mycroft's eyes """
        if self.enclosure and random.random() < rate:
            self.enclosure.eyes_blink("b")

    def stop(self):
        """ Stop thread """
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
        super(TTS, self).__init__()
        self.tts_name = self.__class__.__name__
        self.bus = BUS()
        self.lang = lang or config.get("lang") or 'en-us'
        self.config = config or {}
        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []

        self.voice = config.get("voice")
        self.filename = join(get_ram_directory(self.tts_name),
                             'tts.' + self.audio_ext)
        self.enclosure = None
        random.seed()
        self.queue = Queue()
        self.playback = PlaybackThread(self.queue)
        # NOTE playback start call has been omitted and moved to init method
        # init is called by mycroft, but non mycroft usage wont call it,
        # meaning outside mycroft the enclosure is not set, bus is dummy and
        # playback thread is not used, playback queue is not wanted
        # if some module is calling get_tts (which is the correct usage)
        self.clear_cache()
        self.spellings = self.load_spellings()

    def load_spellings(self, config=None):
        """Load phonetic spellings of words as dictionary."""
        path = join('text', self.lang.lower(), 'phonetic_spellings.txt')
        spellings_file = resolve_resource_file(path, config=config)
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

    def get_tts(self, sentence, wav_file):
        """Abstract method that a tts implementation needs to implement.

        Should get data from tts.

        Arguments:
            sentence(str): Sentence to synthesize
            wav_file(str): output file

        Returns:
            tuple: (wav_file, phoneme)
        """
        pass

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

    def execute(self, sentence, ident=None, listen=False):
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

        create_signal("isSpeaking")
        try:
            self._execute(sentence, ident, listen)
        except Exception:
            # If an error occurs end the audio sequence through an empty entry
            self.queue.put(EMPTY_PLAYBACK_QUEUE_TUPLE)
            # Re-raise to allow the Exception to be handled externally as well.
            raise

    def _execute(self, sentence, ident, listen):
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    sentence = sentence.replace(word,
                                                self.spellings[word.lower()])

        chunks = self._preprocess_sentence(sentence)
        # Apply the listen flag to the last chunk, set the rest to False
        chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                  for i in range(len(chunks))]

        for sentence, l in chunks:
            key = str(hashlib.md5(
                sentence.encode('utf-8', 'ignore')).hexdigest())
            cache_dir = get_ram_directory(self.tts_name)
            wav_file = os.path.join(cache_dir, key + '.' + self.audio_ext)

            if os.path.exists(wav_file):
                LOG.debug("TTS cache hit")
                phonemes = self.load_phonemes(key)
            else:
                wav_file, phonemes = self.get_tts(sentence, wav_file)
                if phonemes:
                    self.save_phonemes(key, phonemes)
                else:
                    phonemes = get_phonemes(sentence)

            vis = self.viseme(phonemes) if phonemes else None
            self.queue.put((self.audio_ext, wav_file, vis, ident, l))

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
        pass

    def save_phonemes(self, key, phonemes):
        """Cache phonemes

        Arguments:
            key (str):        Hash key for the sentence
            phonemes (str):   phoneme string to save
        """
        cache_dir = get_ram_directory(self.tts_name)
        pho_file = os.path.join(cache_dir, key + ".pho")
        try:
            with open(pho_file, "w") as cachefile:
                cachefile.write(phonemes)
        except Exception:
            LOG.exception("Failed to write {} to cache".format(pho_file))
            pass

    def load_phonemes(self, key):
        """Load phonemes from cache file.

        Arguments:
            key (str): Key identifying phoneme cache
        """
        cache_dir = get_ram_directory(self.tts_name)
        pho_file = os.path.join(cache_dir, key + ".pho")
        if os.path.exists(pho_file):
            try:
                with open(pho_file, "r") as cachefile:
                    phonemes = cachefile.read().strip()
                return phonemes
            except Exception:
                LOG.debug("Failed to read .PHO from cache")
        return None

    def stop(self):
        try:
            self.playback.stop()
            self.playback.join()
        except Exception as e:
            pass

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

        return wav_file

    def get_tts(self, sentence, wav_file):
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
