import unittest

from unittest.mock import patch, Mock
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

_TEST_CONFIG = {
    "language": {
        "detection_module": "good",
        "translation_module": "good",
        "good": {"a": "b"}
    }
}
_FALLBACK_CONFIG = {
    "language": {
        "detection_module": "bad",
        "translation_module": "bad",
        "bad": {"fallback_module": "good"},
        "good": {"a": "b"}
    }
}


class TestLanguageTemplate(unittest.TestCase):
    def test_language_detector(self):
        from ovos_plugin_manager.templates.language import LanguageDetector
        # TODO
        
    def test_language_translator(self):
        from ovos_plugin_manager.templates.language import LanguageTranslator
        # TODO


class TestLanguageTranslator(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TRANSLATE
    CONFIG_TYPE = PluginConfigTypes.TRANSLATE
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.language import find_tx_plugins
        find_tx_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.language import load_tx_plugin
        load_tx_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.language import get_tx_configs
        get_tx_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.language import \
            get_tx_module_configs
        get_tx_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)


class TestLanguageDetector(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.LANG_DETECT
    CONFIG_TYPE = PluginConfigTypes.LANG_DETECT
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.language import find_lang_detect_plugins
        find_lang_detect_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.language import load_lang_detect_plugin
        load_lang_detect_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.language import get_lang_detect_configs
        get_lang_detect_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.language import \
            get_lang_detect_module_configs
        get_lang_detect_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)


class TestLangDetectionFactory(unittest.TestCase):
    @patch("ovos_plugin_manager.language.load_lang_detect_plugin")
    def test_get_class(self, load_plugin):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory

        mock_class = Mock()
        load_plugin.return_value = mock_class

        self.assertEqual(OVOSLangDetectionFactory.get_class(_TEST_CONFIG), mock_class)
        load_plugin.assert_called_with("good")

        # Test invalid module config
        conf = {"language": {}}
        with self.assertRaises(ValueError):
            OVOSLangDetectionFactory.get_class(conf)

    @patch("ovos_plugin_manager.language.load_lang_detect_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_create(self, config, load_plugin):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory
        plug_instance = Mock()
        mock_plugin = Mock(return_value=plug_instance)

        config.return_value = _TEST_CONFIG
        load_plugin.return_value = mock_plugin

        # Create from core config
        plug = OVOSLangDetectionFactory.create()
        load_plugin.assert_called_once_with('good')
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEquals(plug_instance, plug)

        # Create plugin fully specified in passed config
        mock_plugin.reset_mock()
        plug = OVOSLangDetectionFactory.create(_TEST_CONFIG)
        load_plugin.assert_called_with("good")
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEquals(plug_instance, plug)

    def test_create_fallback(self):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory
        real_get_class = OVOSLangDetectionFactory.get_class
        mock_class = Mock()
        call_args = None
        bad_call_args = None
        from copy import deepcopy

        def _copy_args(*args):
            nonlocal call_args, bad_call_args
            if args[0]["module"] == "bad":
                bad_call_args = deepcopy(args)
                return None
            call_args = deepcopy(args)
            return mock_class

        mock_get_class = Mock(side_effect=_copy_args)
        OVOSLangDetectionFactory.get_class = mock_get_class

        OVOSLangDetectionFactory.create(config=_FALLBACK_CONFIG)
        mock_get_class.assert_called()
        self.assertEqual(call_args[0]["module"], 'good')
        self.assertEqual(bad_call_args[0]["module"], 'bad')
        mock_class.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        OVOSLangDetectionFactory.get_class = real_get_class


class TestLangTranslationFactory(unittest.TestCase):

    @patch("ovos_plugin_manager.language.load_tx_plugin")
    def test_get_class(self, load_plugin):
        from ovos_plugin_manager.language import OVOSLangTranslationFactory

        mock_class = Mock()
        load_plugin.return_value = mock_class

        self.assertEqual(OVOSLangTranslationFactory.get_class(_TEST_CONFIG), mock_class)
        load_plugin.assert_called_with("good")

        # Test invalid module config
        conf = {"language": {}}
        with self.assertRaises(ValueError):
            OVOSLangTranslationFactory.get_class(conf)

    @patch("ovos_plugin_manager.language.load_tx_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_create(self, config, load_plugin):
        from ovos_plugin_manager.language import OVOSLangTranslationFactory
        plug_instance = Mock()
        mock_plugin = Mock(return_value=plug_instance)

        config.return_value = _TEST_CONFIG
        load_plugin.return_value = mock_plugin

        # Create from core config
        plug = OVOSLangTranslationFactory.create()
        load_plugin.assert_called_once_with('good')
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEquals(plug_instance, plug)

        # Create plugin fully specified in passed config
        mock_plugin.reset_mock()
        plug = OVOSLangTranslationFactory.create(_TEST_CONFIG)
        load_plugin.assert_called_with("good")
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEquals(plug_instance, plug)

    def test_create_fallback(self):
        from ovos_plugin_manager.language import OVOSLangTranslationFactory
        real_get_class = OVOSLangTranslationFactory.get_class
        mock_class = Mock()
        call_args = None
        bad_call_args = None
        from copy import deepcopy

        def _copy_args(*args):
            nonlocal call_args, bad_call_args
            if args[0]["module"] == "bad":
                bad_call_args = deepcopy(args)
                return None
            call_args = deepcopy(args)
            return mock_class

        mock_get_class = Mock(side_effect=_copy_args)
        OVOSLangTranslationFactory.get_class = mock_get_class

        OVOSLangTranslationFactory.create(config=_FALLBACK_CONFIG)
        mock_get_class.assert_called()
        self.assertEqual(call_args[0]["module"], 'good')
        self.assertEqual(bad_call_args[0]["module"], 'bad')
        mock_class.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        OVOSLangTranslationFactory.get_class = real_get_class
