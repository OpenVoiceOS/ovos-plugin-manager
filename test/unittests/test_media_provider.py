import unittest
from unittest.mock import patch, Mock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

from mediavocab import MediaType, Release, Work, Signals
from mediavocab.taxonomy import PlaybackType


def _release(title="Song", media_type=MediaType.MUSIC, conf=0.9, uri="http://x"):
    return Release(work=Work(title=title, media_type=media_type),
                   uri=uri, match_confidence=conf)


class DummyProvider:
    """Built once per test; subclass-style via attributes set in tests."""


class TestMediaProviderTemplate(unittest.TestCase):
    def setUp(self):
        from ovos_plugin_manager.templates.media_provider import MediaProvider

        class _Prov(MediaProvider):
            name = "dummy"
            media = {MediaType.MUSIC}
            playback_type = {PlaybackType.AUDIO}

            def is_available(self):
                return True

            def search(self, signals, lang="en-us"):
                return [_release(title=signals.title or "x")]

        self.cls = _Prov

    def test_three_axis_routing(self):
        p = self.cls()
        # matching medium passes
        self.assertTrue(p.matches(Signals(title="q", medium=MediaType.MUSIC)))
        # wrong medium is gated out
        self.assertFalse(p.matches(Signals(title="q", medium=MediaType.MOVIE)))
        # no preference passes
        self.assertTrue(p.matches(Signals(title="q")))
        # playback_type gate
        self.assertFalse(p.matches(Signals(title="q",
                                           playback_type=PlaybackType.VIDEO)))

    def test_search_returns_releases(self):
        p = self.cls()
        res = p.search(Signals(title="hello"))
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], Release)
        self.assertEqual(res[0].work.title, "hello")

    def test_featured_default_empty(self):
        self.assertEqual(self.cls().featured_media(), [])

    def test_search_safe_swallows_errors(self):
        from ovos_plugin_manager.templates.media_provider import MediaProvider

        class _Boom(MediaProvider):
            name = "boom"

            def is_available(self):
                return True

            def search(self, signals, lang="en-us"):
                raise RuntimeError("kaboom")

        self.assertEqual(_Boom().search_safe(Signals(title="x")), [])


class TestMediaProviderDiscovery(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.MEDIA_PROVIDER
    CONFIG_TYPE = PluginConfigTypes.MEDIA_PROVIDER

    def test_entrypoint_strings(self):
        self.assertEqual(PluginTypes.MEDIA_PROVIDER.value, "opm.media.provider")
        self.assertEqual(PluginConfigTypes.MEDIA_PROVIDER.value,
                         "opm.media.provider.config")

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.media_provider import find_media_provider_plugins
        find_media_provider_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.media_provider import load_media_provider_plugin
        load_media_provider_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.media_provider import get_media_provider_configs
        get_media_provider_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.media_provider.find_media_provider_plugins")
    def test_load_media_providers_filters_unavailable_and_disabled(self, find):
        from ovos_plugin_manager.media_provider import load_media_providers

        avail = Mock()
        avail.return_value.is_available.return_value = True
        unavail = Mock()
        unavail.return_value.is_available.return_value = False
        disabled = Mock()

        find.return_value = {"good": avail, "bad": unavail, "off": disabled}
        loaded = load_media_providers(config={"off": {"enabled": False}})

        self.assertIn("good", loaded)
        self.assertNotIn("bad", loaded)   # is_available() False
        self.assertNotIn("off", loaded)   # disabled in config
        disabled.assert_not_called()      # never instantiated


if __name__ == "__main__":
    unittest.main()
