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

    @patch("ovos_plugin_manager.utils.config.Configuration", return_value={"lang": "en-US"})
    @patch("ovos_plugin_manager.language.load_lang_detect_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_create(self, config, load_plugin, _cfg_utils):
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
        self.assertEqual(plug_instance, plug)

        # Create plugin fully specified in passed config
        mock_plugin.reset_mock()
        plug = OVOSLangDetectionFactory.create(_TEST_CONFIG)
        load_plugin.assert_called_with("good")
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEqual(plug_instance, plug)

    @patch("ovos_plugin_manager.utils.config.Configuration", return_value={"lang": "en-US"})
    def test_create_fallback(self, _):
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
        try:
            OVOSLangDetectionFactory.create(config=_FALLBACK_CONFIG)
            mock_get_class.assert_called()
            self.assertEqual(call_args[0]["module"], 'good')
            self.assertEqual(bad_call_args[0]["module"], 'bad')
            mock_class.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                       **{'module': 'good', 'lang': 'en-US'}})
        finally:
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

    @patch("ovos_plugin_manager.utils.config.Configuration", return_value={"lang": "en-US"})
    @patch("ovos_plugin_manager.language.load_tx_plugin")
    @patch("ovos_plugin_manager.language.Configuration")
    def test_create(self, config, load_plugin, _cfg_utils):
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
        self.assertEqual(plug_instance, plug)

        # Create plugin fully specified in passed config
        mock_plugin.reset_mock()
        plug = OVOSLangTranslationFactory.create(_TEST_CONFIG)
        load_plugin.assert_called_with("good")
        mock_plugin.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                    **{'module': 'good', 'lang': 'en-US'}})
        self.assertEqual(plug_instance, plug)

    @patch("ovos_plugin_manager.utils.config.Configuration", return_value={"lang": "en-US"})
    def test_create_fallback(self, _):
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
        try:
            OVOSLangTranslationFactory.create(config=_FALLBACK_CONFIG)
            mock_get_class.assert_called()
            self.assertEqual(call_args[0]["module"], 'good')
            self.assertEqual(bad_call_args[0]["module"], 'bad')
            mock_class.assert_called_once_with(config={**_TEST_CONFIG["language"]["good"],
                                                       **{'module': 'good', 'lang': 'en-US'}})
        finally:
            OVOSLangTranslationFactory.get_class = real_get_class


# --- the fallback chain walk (T-5111) ----------------------------------------

# A factory follows `fallback_module` from one link of the chain to the next.
# Whether a link has a configuration block of its own says nothing about whether
# its plugin is installed, so the walk must not stop at a link that carries no
# block. The default `language` section of ovos-config ends its detector chain
# at `ovos-lang-detect-ngram-lm`, which carries no block, and the walk stopped
# one link early and reported the middle link as the failure.

_CHAIN_WITHOUT_BLOCKS = {
    "language": {
        "detection_module": "bad",
        "translation_module": "bad",
        "bad": {"fallback_module": "good"},
        # `good` deliberately carries NO configuration block of its own.
    }
}
_CYCLIC_CHAIN = {
    "language": {
        "detection_module": "bad",
        "translation_module": "bad",
        "bad": {"fallback_module": "worse"},
        "worse": {"fallback_module": "bad"},
    }
}


class TestLanguageFallbackChain(unittest.TestCase):
    """The walk follows the chain, not the configuration keys."""

    def _factory(self, which):
        from ovos_plugin_manager.language import (OVOSLangDetectionFactory,
                                                  OVOSLangTranslationFactory)
        return {"detect": OVOSLangDetectionFactory,
                "translate": OVOSLangTranslationFactory}[which]

    def _run(self, which, config):
        """Create through `which` factory; every module but `good` fails."""
        factory = self._factory(which)
        real_get_class = factory.get_class
        tried = []
        made = Mock()

        def _get_class(cfg):
            tried.append(cfg["module"])
            if cfg["module"] == "good":
                return made
            raise RuntimeError(f"{cfg['module']} is not installed")

        factory.get_class = Mock(side_effect=_get_class)
        try:
            return factory.create(config=config), tried
        finally:
            factory.get_class = real_get_class

    @patch("ovos_plugin_manager.utils.config.Configuration",
           return_value={"lang": "en-US"})
    def test_detect_follows_a_fallback_with_no_config_block(self, _):
        got, tried = self._run("detect", _CHAIN_WITHOUT_BLOCKS)
        self.assertEqual(tried, ["bad", "good"])
        self.assertIsNotNone(got)

    @patch("ovos_plugin_manager.utils.config.Configuration",
           return_value={"lang": "en-US"})
    def test_translate_follows_a_fallback_with_no_config_block(self, _):
        got, tried = self._run("translate", _CHAIN_WITHOUT_BLOCKS)
        self.assertEqual(tried, ["bad", "good"])
        self.assertIsNotNone(got)

    @patch("ovos_plugin_manager.utils.config.Configuration",
           return_value={"lang": "en-US"})
    def test_detect_stops_on_a_cyclic_chain(self, _):
        """A chain that points back at itself raises, and does not recurse."""
        with self.assertRaises(Exception) as ctx:
            self._run("detect", _CYCLIC_CHAIN)
        self.assertNotIsInstance(ctx.exception, RecursionError)

    @patch("ovos_plugin_manager.utils.config.Configuration",
           return_value={"lang": "en-US"})
    def test_detect_tries_each_link_once_on_a_cyclic_chain(self, _):
        from ovos_plugin_manager.language import OVOSLangDetectionFactory
        real_get_class = OVOSLangDetectionFactory.get_class
        tried = []

        def _get_class(cfg):
            tried.append(cfg["module"])
            raise RuntimeError("nothing is installed")

        OVOSLangDetectionFactory.get_class = Mock(side_effect=_get_class)
        try:
            with self.assertRaises(Exception):
                OVOSLangDetectionFactory.create(config=_CYCLIC_CHAIN)
        finally:
            OVOSLangDetectionFactory.get_class = real_get_class
        self.assertEqual(tried, ["bad", "worse"])

    @patch("ovos_plugin_manager.utils.config.Configuration",
           return_value={"lang": "en-US"})
    def test_create_does_not_write_to_the_caller_config(self, _):
        """The factory must not edit the live Configuration it was handed."""
        from copy import deepcopy
        config = deepcopy(_CHAIN_WITHOUT_BLOCKS)
        before = deepcopy(config)
        self._run("detect", config)
        self.assertEqual(config, before)
