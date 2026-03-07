import unittest
from copy import copy
from queue import Queue
from threading import Event
from typing import Optional, Set, List, Tuple
from unittest.mock import patch, Mock, MagicMock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_plugin_manager.utils.audio import AudioData


# ---------------------------------------------------------------------------
# Minimal concrete implementations for testing abstract base classes
# ---------------------------------------------------------------------------

class _DummySTT:
    """Concrete STT for testing (no metaclass hassles)."""
    from ovos_plugin_manager.templates.stt import STT as _Base

    class _Impl(_Base):
        @property
        def available_languages(self) -> Set[str]:
            return {"en-US", "de-DE"}

        def execute(self, audio, language=None) -> str:
            return "hello"


_ConcreteSTT = _DummySTT._Impl


class _ConcreteStreamThread:
    from ovos_plugin_manager.templates.stt import StreamThread as _Base

    class _Impl(_Base):
        def handle_audio_stream(self, audio, language):
            for chunk in audio:
                pass
            self.text = "streamed result"


_ConcreteStreamThread = _ConcreteStreamThread._Impl


class _ConcreteStreamingSTT:
    from ovos_plugin_manager.templates.stt import StreamingSTT as _Base

    class _Impl(_Base):
        @property
        def available_languages(self) -> Set[str]:
            return {"en-US"}

        def execute(self, audio=None, language=None):
            return self.stream_stop()

        def create_streaming_thread(self):
            return _ConcreteStreamThread(self.queue, self.lang)


_ConcreteStreamingSTT = _ConcreteStreamingSTT._Impl


class TestSTTTemplate(unittest.TestCase):

    def test_stt_lang_from_config(self):
        stt = _ConcreteSTT(config={"lang": "de-DE"})
        self.assertEqual(stt.lang, "de-DE")

    def test_stt_lang_setter(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        stt.lang = "pt-BR"
        self.assertEqual(stt.lang, "pt-BR")

    def test_stt_available_languages(self):
        stt = _ConcreteSTT()
        self.assertIn("en-US", stt.available_languages)
        self.assertIn("de-DE", stt.available_languages)

    def test_stt_transcribe_returns_list(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        audio = MagicMock(spec=AudioData)
        result = stt.transcribe(audio, lang="en-US")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        text, conf = result[0]
        self.assertIsInstance(text, str)
        self.assertIsInstance(conf, float)
        self.assertEqual(conf, 1.0)

    def test_stt_transcribe_auto_lang_no_detector(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        audio = MagicMock(spec=AudioData)
        # auto lang without a detector bound: should fall back to execute()
        result = stt.transcribe(audio, lang="auto")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0][0], "hello")

    def test_stt_bind_detector(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        detector = MagicMock()
        detector.detect.return_value = ("en-US", 0.99)
        stt.bind(detector)
        self.assertIs(stt._detector, detector)

    def test_stt_detect_language_without_detector(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        audio = MagicMock(spec=AudioData)
        with self.assertRaises(NotImplementedError):
            stt.detect_language(audio)

    def test_stt_detect_language_with_detector(self):
        stt = _ConcreteSTT(config={"lang": "en-US"})
        detector = MagicMock()
        detector.detect.return_value = ("de-DE", 0.95)
        stt.bind(detector)
        audio = MagicMock(spec=AudioData)
        lang, prob = stt.detect_language(audio)
        self.assertEqual(lang, "de-DE")
        self.assertAlmostEqual(prob, 0.95)

    def test_stt_can_stream_default_false(self):
        stt = _ConcreteSTT()
        self.assertFalse(stt.can_stream)

    def test_stream_thread_run_and_finalize(self):
        q = Queue()
        thread = _ConcreteStreamThread(q, "en-US")
        self.assertEqual(thread.language, "en-US")

        # feed data and signal end
        q.put(b"chunk1")
        q.put(b"chunk2")
        q.put(None)
        thread.run()
        self.assertEqual(thread.finalize(), "streamed result")

    def test_streaming_stt_can_stream_true(self):
        stt = _ConcreteStreamingSTT(config={"lang": "en-US"})
        self.assertTrue(stt.can_stream)

    def test_streaming_stt_stream_lifecycle(self):
        stt = _ConcreteStreamingSTT(config={"lang": "en-US"})
        stt.stream_start("en-US")
        self.assertIsNotNone(stt.stream)
        self.assertIsNotNone(stt.queue)

        stt.stream_data(b"audio_chunk")
        result = stt.stream_stop()
        self.assertEqual(result, "streamed result")
        self.assertIsNone(stt.stream)
        self.assertIsNone(stt.queue)
        self.assertTrue(stt.transcript_ready.is_set())

    def test_streaming_stt_stop_without_stream(self):
        stt = _ConcreteStreamingSTT(config={"lang": "en-US"})
        # stream_stop on an uninitialised stream should return None
        result = stt.stream_stop()
        self.assertIsNone(result)
    

class TestSTT(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.STT
    CONFIG_TYPE = PluginConfigTypes.STT
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "stt"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.stt import find_stt_plugins
        find_stt_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.stt import load_stt_plugin
        load_stt_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.stt import get_stt_configs
        get_stt_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.stt import get_stt_module_configs
        get_stt_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.stt import get_stt_lang_configs
        get_stt_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.stt import get_stt_supported_langs
        get_stt_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_stt_config(self, get_config):
        from ovos_plugin_manager.stt import get_stt_config
        config = copy(self.TEST_CONFIG)
        get_stt_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION, None)
        self.assertEqual(config, self.TEST_CONFIG)


class TestSTTFactory(unittest.TestCase):

    @patch("ovos_plugin_manager.stt.load_stt_plugin")
    def test_get_class(self, load_plugin):
        from ovos_plugin_manager.stt import OVOSSTTFactory
        global_config = {"stt": {"module": "ovos-stt-plugin-dummy"}}
        tts_config = {"module": "test-stt-plugin-test"}

        # Test load plugin mapped global config
        OVOSSTTFactory.get_class(global_config)
        load_plugin.assert_called_with("ovos-stt-plugin-dummy")

        # Test load plugin explicit STT config
        OVOSSTTFactory.get_class(tts_config)
        load_plugin.assert_called_with("test-stt-plugin-test")

    @patch("ovos_plugin_manager.stt.OVOSSTTFactory.get_class")
    def test_create(self, get_class):
        from ovos_plugin_manager.stt import OVOSSTTFactory
        plugin_class = Mock()
        get_class.return_value = plugin_class

        global_config = {"lang": "en-gb",
                         "stt": {"module": "ovos-stt-plugin-dummy",
                                 "ovos-stt-plugin-dummy": {"config": True,
                                                           "lang": "en-ca"}}}
        stt_config = {"lang": "es-es",
                      "module": "test-stt-plugin-test"}

        stt_config_2 = {"lang": "es-es",
                        "module": "test-stt-plugin-test",
                        "test-stt-plugin-test": {"config": True,
                                                 "lang": "es-mx"}}

        # Test create with global config and lang override
        plugin = OVOSSTTFactory.create(global_config)
        expected_config = {"module": "ovos-stt-plugin-dummy",
                           "config": True,
                           "lang": "en-ca"}
        get_class.assert_called_once_with(expected_config)
        plugin_class.assert_called_once_with(expected_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with STT config and no module config
        plugin = OVOSSTTFactory.create(stt_config)
        get_class.assert_called_with(stt_config)
        plugin_class.assert_called_with(stt_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with STT config with module-specific config
        plugin = OVOSSTTFactory.create(stt_config_2)
        expected_config = {"module": "test-stt-plugin-test",
                           "config": True, "lang": "es-mx"}
        get_class.assert_called_with(expected_config)
        plugin_class.assert_called_with(expected_config)
        self.assertEqual(plugin, plugin_class())

