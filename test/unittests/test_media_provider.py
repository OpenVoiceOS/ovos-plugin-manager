import unittest
from unittest.mock import patch, Mock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

from mediavocab import MediaType, Release, Work, Signals


def _release(title="Song", media_type=MediaType.MUSIC, conf=0.9, uri="http://x"):
    return Release(work=Work(title=title, media_type=media_type),
                   uri=uri, match_confidence=conf)


class TestMediaProviderTemplate(unittest.TestCase):
    """The contract is one method: search(signals, context) -> list[Release]."""

    def setUp(self):
        from ovos_plugin_manager.templates.media_provider import MediaProvider

        class _Prov(MediaProvider):
            name = "dummy"

            def search(self, signals, context):
                # a provider may self-filter on context
                if not context.allows_playback(["audio"]):
                    return []
                return [_release(title=signals.title or "x")]

        self.cls = _Prov

    def test_search_returns_releases(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        res = self.cls().search(Signals(title="hello"), QueryContext())
        self.assertEqual(len(res), 1)
        self.assertIsInstance(res[0], Release)
        self.assertEqual(res[0].work.title, "hello")

    def test_provider_may_self_filter_on_context(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        p = self.cls()
        # device that can't play audio → provider returns nothing
        self.assertEqual(
            p.search(Signals(title="x"),
                     QueryContext(supported_playback_types={"video"})), [])

    def test_search_is_the_only_abstract_method(self):
        from ovos_plugin_manager.templates.media_provider import MediaProvider

        class _Incomplete(MediaProvider):
            pass

        with self.assertRaises(TypeError):
            _Incomplete()  # search() not implemented

    def test_shutdown_is_a_noop_by_default(self):
        self.cls().shutdown()  # must not raise

    def test_config_defaults_to_empty_dict(self):
        self.assertEqual(self.cls().config, {})
        self.assertEqual(self.cls(config={"k": 1}).config, {"k": 1})


class TestQueryContext(unittest.TestCase):
    def test_permissive_by_default(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        ctx = QueryContext()
        self.assertTrue(ctx.allows_playback(["video"]))
        self.assertTrue(ctx.allows_genres(["adult"]))

    def test_allows_playback_gate(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        ctx = QueryContext(supported_playback_types={"audio"})
        self.assertTrue(ctx.allows_playback(["audio"]))
        self.assertFalse(ctx.allows_playback(["video"]))
        self.assertTrue(ctx.allows_playback(["audio", "video"]))

    def test_allows_genres_gate(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        ctx = QueryContext(blocked_genres={"adult"})
        self.assertFalse(ctx.allows_genres(["adult"]))
        self.assertTrue(ctx.allows_genres(["pop"]))


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
    def test_load_media_providers_filters_disabled(self, find):
        from ovos_plugin_manager.media_provider import load_media_providers

        good = Mock()
        disabled = Mock()
        find.return_value = {"good": good, "off": disabled}
        loaded = load_media_providers(config={"off": {"enabled": False}})

        self.assertIn("good", loaded)
        self.assertNotIn("off", loaded)   # disabled in config
        disabled.assert_not_called()      # never instantiated


if __name__ == "__main__":
    unittest.main()
