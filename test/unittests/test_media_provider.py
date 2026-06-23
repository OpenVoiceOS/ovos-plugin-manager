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


class TestQueryContextGating(unittest.TestCase):
    """Context-aware routing: serves() = matches() AND device/policy compatible."""

    def _provider(self, **attrs):
        from ovos_plugin_manager.templates.media_provider import MediaProvider

        class _P(MediaProvider):
            def is_available(self): return True
            def search(self, signals, lang="en-us"): return []
        for k, v in attrs.items():
            setattr(_P, k, v)
        return _P()

    def test_query_context_permissive_by_default(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        ctx = QueryContext()
        self.assertTrue(ctx.allows_playback([PlaybackType.VIDEO]))
        self.assertTrue(ctx.allows_genres(["adult"]))

    def test_serves_without_context_equals_matches(self):
        p = self._provider(name="m", media={MediaType.MOVIE},
                           playback_type={PlaybackType.VIDEO})
        sig = Signals.as_query(medium=MediaType.MOVIE, playback_type=PlaybackType.VIDEO)
        self.assertTrue(p.matches(sig))
        self.assertTrue(p.serves(sig))            # no context → permissive
        self.assertTrue(p.serves(sig, None))

    def test_video_provider_skipped_on_audio_only_device(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        p = self._provider(name="v", media={MediaType.MOVIE},
                           playback_type={PlaybackType.VIDEO})
        sig = Signals.as_query(medium=MediaType.MOVIE, playback_type=PlaybackType.VIDEO)
        self.assertFalse(p.serves(sig, QueryContext(supported_playback_types={"audio"})))
        self.assertTrue(p.serves(sig, QueryContext(supported_playback_types={"audio", "video"})))

    def test_adult_provider_skipped_when_policy_blocks(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext
        p = self._provider(name="x", media={MediaType.MOVIE}, genre_filter={"adult"})
        sig = Signals.as_query(medium=MediaType.MOVIE, content_genres=["adult"])
        self.assertFalse(p.serves(sig, QueryContext(blocked_genres={"adult"})))
        self.assertTrue(p.serves(sig, QueryContext()))

    def test_search_context_defaults_to_search(self):
        from ovos_plugin_manager.templates.media_provider import QueryContext

        class _P2(self._provider().__class__.__bases__[0]):
            name = "s"
            media = {MediaType.MUSIC}
            def is_available(self): return True
            def search(self, signals, lang="en-us"):
                return [_release()]
        p = _P2()
        out = p.search_context(Signals.as_query(medium=MediaType.MUSIC),
                               context=QueryContext(), lang="en-us")
        self.assertEqual(len(out), 1)
        # search_safe also accepts context and never raises
        self.assertEqual(len(p.search_safe(Signals.as_query(), QueryContext())), 1)
