import unittest

from unittest.mock import patch, Mock
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


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
    TEST_LANG = "en-us"

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
    TEST_LANG = "en-us"

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
    def test_mappings(self):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory
        self.assertIsInstance(OVOSLangDetectionFactory.MAPPINGS, dict)
        for conf in OVOSLangDetectionFactory.MAPPINGS:
            self.assertIsInstance(conf, str)
            self.assertIsInstance(OVOSLangDetectionFactory.MAPPINGS[conf],
                                  str)
            self.assertNotEqual(conf, OVOSLangDetectionFactory.MAPPINGS[conf])

    @patch("ovos_plugin_manager.language.load_lang_detect_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_get_class(self, config, load_plugin):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory
        test_config = {"language": {
            "detection_module": "libretranslate"
        }}
        mock_class = Mock()
        config.return_value = test_config
        load_plugin.return_value = mock_class

        # Test mapped plugin from config
        self.assertEquals(OVOSLangDetectionFactory.get_class(), mock_class)
        load_plugin.assert_called_with("libretranslate_detection_plug")

        # Test explicitly specified mapped plugin
        conf = {"module": "google"}
        self.assertEquals(OVOSLangDetectionFactory.get_class(conf), mock_class)
        load_plugin.assert_called_with("googletranslate_detection_plug")

        # Test unmapped plugin
        conf = {"language": {"detection_module": "real-detect-plug"}}
        self.assertEquals(OVOSLangDetectionFactory.get_class(conf), mock_class)
        load_plugin.assert_called_with("real-detect-plug")

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
        default_config = {
            "lang": "core_lang",
            "language": {
                "detection_module": "google",
                "lang": "detect"
            }
        }
        config.return_value = default_config
        load_plugin.return_value = mock_plugin

        # Create from core config
        plug = OVOSLangDetectionFactory.create()
        load_plugin.assert_called_once_with('googletranslate_detection_plug')
        mock_plugin.assert_called_once_with(
            config={'lang': "detect",
                    "module": "googletranslate_detection_plug"})
        self.assertEquals(plug_instance, plug)

        # Create plugin fully specified in passed config
        config_with_module = {"detection_module": "detect-plugin",
                              "lang": "lang"}
        plug = OVOSLangDetectionFactory.create(config_with_module)
        load_plugin.assert_called_with("detect-plugin")
        mock_plugin.assert_called_with(config={"module": "detect-plugin",
                                               "lang": "lang"})
        self.assertEquals(plug_instance, plug)

        # Create plugin fallback module config parsing
        config_with_fallback_module = {"module": "test-detect-plugin",
                                       "lang": "lang"}
        plug = OVOSLangDetectionFactory.create(config_with_fallback_module)
        load_plugin.assert_called_with("test-detect-plugin")
        mock_plugin.assert_called_with(config=config_with_fallback_module)
        self.assertEquals(plug_instance, plug)
        # TODO: Test exception handling fallback to libretranslate


class TestLangTranslationFactory(unittest.TestCase):
    def test_mappings(self):
        from ovos_plugin_manager.language import OVOSLangTranslationFactory
        self.assertIsInstance(OVOSLangTranslationFactory.MAPPINGS, dict)
        for conf in OVOSLangTranslationFactory.MAPPINGS:
            self.assertIsInstance(conf, str)
            self.assertIsInstance(OVOSLangTranslationFactory.MAPPINGS[conf],
                                  str)
            self.assertNotEqual(conf, OVOSLangTranslationFactory.MAPPINGS[conf])

    @patch("ovos_plugin_manager.language.load_tx_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_get_class(self, config, load_plugin):
        from ovos_plugin_manager.language import OVOSLangTranslationFactory
        test_config = {"language": {
            "translation_module": "libretranslate"
        }}
        mock_class = Mock()
        config.return_value = test_config
        load_plugin.return_value = mock_class

        # Test mapped plugin from config
        self.assertEquals(OVOSLangTranslationFactory.get_class(), mock_class)
        load_plugin.assert_called_with("libretranslate_plug")

        # Test explicitly specified mapped plugin
        conf = {"module": "google"}
        self.assertEquals(OVOSLangTranslationFactory.get_class(conf),
                          mock_class)
        load_plugin.assert_called_with("googletranslate_plug")

        # Test unmapped plugin
        conf = {"language": {"translation_module": "real-detect-plug"}}
        self.assertEquals(OVOSLangTranslationFactory.get_class(conf), mock_class)
        load_plugin.assert_called_with("real-detect-plug")

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
        default_config = {
            "lang": "core_lang",
            "language": {
                "translation_module": "google",
                "lang": "tx"
            }
        }
        config.return_value = default_config
        load_plugin.return_value = mock_plugin

        # Create from core config
        plug = OVOSLangTranslationFactory.create()
        load_plugin.assert_called_once_with('googletranslate_plug')
        mock_plugin.assert_called_once_with(
            config={'lang': "tx", "module": "googletranslate_plug"})
        self.assertEquals(plug_instance, plug)

        # Create plugin fully specified in passed config
        config_with_module = {"translation_module": "translate-plugin",
                              "lang": "lang"}
        plug = OVOSLangTranslationFactory.create(config_with_module)
        load_plugin.assert_called_with("translate-plugin")
        mock_plugin.assert_called_with(config={"module": "translate-plugin",
                                               "lang": "lang"})
        self.assertEquals(plug_instance, plug)

        # Create plugin fallback module config parsing
        config_with_fallback_module = {"module": "test-translate-plugin",
                                       "lang": "lang"}
        plug = OVOSLangTranslationFactory.create(config_with_fallback_module)
        load_plugin.assert_called_with("test-translate-plugin")
        mock_plugin.assert_called_with(config=config_with_fallback_module)
        self.assertEquals(plug_instance, plug)

        # TODO: Test exception handling fallback to libretranslate
