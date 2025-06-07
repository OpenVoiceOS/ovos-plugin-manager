import unittest
from unittest.mock import MagicMock
from unittest.mock import patch, Mock

from ovos_bus_client.session import Session
from ovos_utils.fakebus import FakeBus, Message

from ovos_plugin_manager.templates.tts import TTS, TTSContext
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestTTSTemplate(unittest.TestCase):
    tts = TTS()  # dummy engine

    def test_ssml(self):
        sentence = "<speak>Prosody can be used to change the way words " \
                   "sound. The following words are " \
                   "<prosody volume='x-loud'> " \
                   "quite a bit louder than the rest of this passage. " \
                   "</prosody> Each morning when I wake up, " \
                   "<prosody rate='x-slow'>I speak quite slowly and " \
                   "deliberately until I have my coffee.</prosody> I can " \
                   "also change the pitch of my voice using prosody. " \
                   "Do you like <prosody pitch='+5%'> speech with a pitch " \
                   "that is higher, </prosody> or <prosody pitch='-10%'> " \
                   "is a lower pitch preferable?</prosody></speak>"
        sentence_no_ssml = "Prosody can be used to change the way " \
                           "words sound. The following words are quite " \
                           "a bit louder than the rest of this passage. " \
                           "Each morning when I wake up, I speak quite " \
                           "slowly and deliberately until I have my " \
                           "coffee. I can also change the pitch of my " \
                           "voice using prosody. Do you like speech " \
                           "with a pitch that is higher, or is " \
                           "a lower pitch preferable?"
        sentence_bad_ssml = "<foo_invalid>" + sentence + \
                            "</foo_invalid end=whatever>"
        sentence_extra_ssml = "<whispered>whisper tts<\\whispered>"

        tts = TTS()  # dummy engine
        # test valid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence), sentence)

        # test extra ssml
        tts.ssml_tags = ['whispered']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         sentence_extra_ssml)

        # test unsupported extra ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         "whisper tts")

        # test mixed valid / invalid ssml
        tts.ssml_tags = ['speak', 'prosody']
        self.assertEqual(tts.validate_ssml(sentence_bad_ssml), sentence)

        # test unsupported ssml
        tts.ssml_tags = []
        self.assertEqual(tts.validate_ssml(sentence), sentence_no_ssml)

        self.assertEqual(tts.validate_ssml(sentence_bad_ssml),
                         sentence_no_ssml)

        self.assertEqual(TTS.remove_ssml(sentence), sentence_no_ssml)

    def test_format_speak_tags_with_speech(self):
        valid_output = "<speak>Speak This.</speak>"
        no_tags = TTS.format_speak_tags("Speak This.")
        self.assertEqual(no_tags, valid_output)

        leading_only = TTS.format_speak_tags("<speak>Speak This.")
        self.assertEqual(leading_only, valid_output)

        leading_with_exclusion = TTS.format_speak_tags("Nope.<speak>Speak This.")
        self.assertEqual(leading_with_exclusion, valid_output)

        trailing_only = TTS.format_speak_tags("Speak This.</speak>")
        self.assertEqual(trailing_only, valid_output)

        trailing_with_exclusion = TTS.format_speak_tags("Speak This.</speak> But not this.")
        self.assertEqual(trailing_with_exclusion, valid_output)

        tagged = TTS.format_speak_tags("<speak>Speak This.</speak>")
        self.assertEqual(tagged, valid_output)

        tagged_with_exclusion = TTS.format_speak_tags("Don't<speak>Speak This.</speak>But Not this.")
        self.assertEqual(tagged_with_exclusion, valid_output)

    def test_format_speak_tags_empty(self):
        leading_closure = TTS.format_speak_tags("</speak>hello.")
        self.assertFalse(leading_closure)

        trailing_open = TTS.format_speak_tags("hello.<speak>")
        self.assertFalse(trailing_open)

    def test_format_speak_tags_with_speech_no_tags(self):
        valid_output = "Speak This."
        no_tags = TTS.format_speak_tags("Speak This.", False)
        self.assertEqual(no_tags, valid_output)

        leading_only = TTS.format_speak_tags("<speak>Speak This.", False)
        self.assertEqual(leading_only, valid_output)

        leading_with_exclusion = TTS.format_speak_tags("Nope.<speak>Speak This.", False)
        self.assertEqual(leading_with_exclusion, valid_output)

        trailing_only = TTS.format_speak_tags("Speak This.</speak>", False)
        self.assertEqual(trailing_only, valid_output)

        trailing_with_exclusion = TTS.format_speak_tags("Speak This.</speak> But not this.", False)
        self.assertEqual(trailing_with_exclusion, valid_output)

        tagged = TTS.format_speak_tags("<speak>Speak This.</speak>", False)
        self.assertEqual(tagged, valid_output)

        tagged_with_exclusion = TTS.format_speak_tags("Don't<speak>Speak This.</speak>But Not this.", False)
        self.assertEqual(tagged_with_exclusion, valid_output)

    def test_tts_validator(self):
        from ovos_plugin_manager.templates.tts import TTSValidator
        # TODO


class TestTTS(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TTS
    CONFIG_TYPE = PluginConfigTypes.TTS
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "tts"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.tts import find_tts_plugins
        find_tts_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.tts import load_tts_plugin
        load_tts_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.tts import get_tts_configs
        get_tts_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.tts import get_tts_module_configs
        get_tts_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.tts import get_tts_lang_configs
        get_tts_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.tts import get_tts_supported_langs
        get_tts_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_tts_config(self, get_config):
        from ovos_plugin_manager.tts import get_tts_config
        get_tts_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION, None)

    def test_get_voice_id(self):
        from ovos_plugin_manager.tts import get_voice_id
        # TODO

    def test_scan_voices(self):
        from ovos_plugin_manager.tts import scan_voices
        # TODO

    def test_get_voices(self):
        from ovos_plugin_manager.tts import get_voices
        # TODO


class TestTTSFactory(unittest.TestCase):

    @patch("ovos_plugin_manager.tts.load_tts_plugin")
    def test_get_class(self, load_plugin):
        from ovos_plugin_manager.tts import OVOSTTSFactory
        global_config = {"tts": {"module": "ovos-tts-plugin-dummy"}}
        tts_config = {"module": "test-tts-plugin-test"}

        # Test load plugin mapped global config
        OVOSTTSFactory.get_class(global_config)
        load_plugin.assert_called_with("ovos-tts-plugin-dummy")

        # Test load plugin explicit TTS config
        OVOSTTSFactory.get_class(tts_config)
        load_plugin.assert_called_with("test-tts-plugin-test")

    @patch("ovos_plugin_manager.tts.OVOSTTSFactory.get_class")
    def test_create(self, get_class):
        from ovos_plugin_manager.tts import OVOSTTSFactory
        plugin_class = Mock()
        get_class.return_value = plugin_class

        global_config = {"lang": "en-gb",
                         "tts": {"module": "ovos-tts-plugin-dummy",
                                 "ovos-tts-plugin-dummy": {"config": True,
                                                           "lang": "en-ca"}}}
        tts_config = {"lang": "es-es",
                      "module": "test-tts-plugin-test"}

        tts_config_2 = {"lang": "es-es",
                        "module": "test-tts-plugin-test",
                        "test-tts-plugin-test": {"config": True,
                                                 "lang": "es-mx"}}

        # Test create with global config and lang override
        plugin = OVOSTTSFactory.create(global_config)
        expected_config = {"module": "ovos-tts-plugin-dummy",
                           "config": True,
                           "lang": "en-ca"}
        get_class.assert_called_once_with(expected_config)
        plugin_class.assert_called_once_with(config=expected_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with TTS config and no module config
        plugin = OVOSTTSFactory.create(tts_config)
        get_class.assert_called_with(tts_config)
        plugin_class.assert_called_with(config=tts_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with TTS config with module-specific config
        plugin = OVOSTTSFactory.create(tts_config_2)
        expected_config = {"module": "test-tts-plugin-test",
                           "config": True, "lang": "es-mx"}
        get_class.assert_called_with(expected_config)
        plugin_class.assert_called_with(config=expected_config)
        self.assertEqual(plugin, plugin_class())


class TestTTSContext(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.tts.TextToSpeechCache", autospec=True)
    def test_tts_context_get_cache(self, cache_mock):
        tts_context = TTSContext("plug", "voice", "lang")

        result = tts_context.get_cache()

        self.assertEqual(result, cache_mock.return_value)
        self.assertEqual(result, tts_context._caches[tts_context.tts_id])


class TestTTSCache(unittest.TestCase):
    def setUp(self):
        self.tts_mock = TTS(config={"some_config_key": "some_config_value"})
        self.tts_mock.stopwatch = MagicMock()
        self.tts_mock.queue = MagicMock()
        self.tts_mock.playback = MagicMock()

    @patch("ovos_plugin_manager.templates.tts.hash_sentence", return_value="fake_hash")
    @patch("ovos_plugin_manager.templates.tts.TTSContext")
    def test_tts_synth(self, tts_context_mock, hash_sentence_mock):
        tts_context_mock.get_cache.return_value = MagicMock()
        tts_context_mock.get_cache.return_value.define_audio_file.return_value.path = "fake_audio_path"

        sentence = "Hello world!"
        result = self.tts_mock.synth(sentence, tts_context_mock)

        tts_context_mock.get_cache.assert_called_once_with("wav", self.tts_mock.config)
        tts_context_mock.get_cache.return_value.define_audio_file.assert_called_once_with("fake_hash")
        self.assertEqual(result, (tts_context_mock.get_cache.return_value.define_audio_file.return_value, None))

    @patch("ovos_plugin_manager.templates.tts.hash_sentence", return_value="fake_hash")
    def test_tts_synth_cache_enabled(self, hash_sentence_mock):
        tts_context_mock = MagicMock()
        tts_context_mock.tts_id = "fake_tts_id"
        tts_context_mock.get_cache.return_value = MagicMock()
        tts_context_mock.get_cache.return_value.cached_sentences = {}
        tts_context_mock.get_cache.return_value.define_audio_file.return_value.path = "fake_audio_path"
        tts_context_mock._caches = {tts_context_mock.tts_id: tts_context_mock.get_cache.return_value}

        sentence = "Hello world!"
        self.tts_mock.enable_cache = True
        result = self.tts_mock.synth(sentence, tts_context_mock)

        tts_context_mock.get_cache.assert_called_once_with("wav", self.tts_mock.config)
        tts_context_mock.get_cache.return_value.define_audio_file.assert_called_once_with("fake_hash")
        self.assertEqual(result, (tts_context_mock.get_cache.return_value.define_audio_file.return_value, None))
        self.assertIn("fake_hash", tts_context_mock.get_cache.return_value.cached_sentences)

    @patch("ovos_plugin_manager.templates.tts.hash_sentence", return_value="fake_hash")
    def test_tts_synth_cache_disabled(self, hash_sentence_mock):
        tts_context_mock = MagicMock()
        tts_context_mock.tts_id = "fake_tts_id"
        tts_context_mock.get_cache.return_value = MagicMock()
        tts_context_mock.get_cache.return_value.cached_sentences = {}
        tts_context_mock.get_cache.return_value.define_audio_file.return_value.path = "fake_audio_path"
        tts_context_mock._caches = {tts_context_mock.tts_id: tts_context_mock.get_cache.return_value}

        sentence = "Hello world!"
        self.tts_mock.enable_cache = False
        result = self.tts_mock.synth(sentence, tts_context_mock)

        tts_context_mock.get_cache.assert_called_once_with("wav", self.tts_mock.config)
        tts_context_mock.get_cache.return_value.define_audio_file.assert_called_once_with("fake_hash")
        self.assertEqual(result, (tts_context_mock.get_cache.return_value.define_audio_file.return_value, None))
        self.assertNotIn("fake_hash", tts_context_mock.get_cache.return_value.cached_sentences)


class DummyTTS(TTS):
    def __init__(self, config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        """
        Initializes the TTS engine with specified parameters.

        Args:
            config (dict): Configuration settings for the TTS engine.
            validator (TTSValidator): Validator for verifying installation.
            audio_ext (str): Default audio file extension (default is 'wav').
            phonetic_spelling (bool): Whether to use phonetic spelling (default is True).
            ssml_tags (list): Supported SSML tags (default is None).
        """
        config = {"lang": "en-US"}
        super().__init__(config, validator, audio_ext, phonetic_spelling, ssml_tags)

    def get_tts(self, sentence, wav_file, lang=None, voice=None):
        """Abstract method that a tts implementation needs to implement.

        Args:
            sentence (str): The input sentence to synthesize.
            wav_file (str): The output file path for the synthesized audio.
            lang (str, optional): The requested language (defaults to self.lang).
            voice (str, optional): The requested voice (defaults to self.voice).

        Returns:
            tuple: (wav_file, phoneme)
        """
        return wav_file, None

class TestSession(unittest.TestCase):
    def test_tts_session(self):
        sess = Session(session_id="123", lang="en-US")
        m = Message("speak",
                    context={"session": sess.serialize()})

        tts = DummyTTS()
        tts._plugin_id = "dummy"
        self.assertEqual(tts.voice, "default")  # no voice set
        self.assertEqual(tts.lang, "en-US")  # from config

        # test that session makes it all the way to the TTS.queue
        kwargs = {"message": m}
        tts.execute("test sentence", **kwargs)
        path, visemes, listen, tts_id, message = tts.queue.get()
        self.assertEqual(message, m)
        self.assertEqual(message.context["session"]["session_id"], sess.session_id)

        # test that lang from Session is used
        ctxt = tts._get_ctxt(kwargs)
        self.assertEqual(ctxt.plugin_id, tts.plugin_id)
        self.assertEqual(ctxt.lang, sess.lang)
        self.assertEqual(ctxt.tts_id, f"{tts.plugin_id}/default/en-US")
        self.assertEqual(ctxt.synth_kwargs, {'lang': 'en-US', "voice": "default"})

        sess = Session(session_id="123",
                       lang="klingon")
        m = Message("speak",
                    context={"session": sess.serialize()})
        kwargs = {"message": m, "voice": "Daghor"}
        ctxt = tts._get_ctxt(kwargs)
        self.assertEqual(ctxt.lang, sess.lang)
        self.assertEqual(ctxt.tts_id, f"{tts.plugin_id}/Daghor/klingon")
        self.assertEqual(ctxt.synth_kwargs, {'lang': 'klingon', 'voice': 'Daghor'})
