import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus


class TestPHALShutdownHandlerLeak(unittest.TestCase):
    """Regression tests for PHALPlugin.shutdown() removing exactly the
    handlers it registered on the bus.

    Previously `shutdown()` called `bus.remove(topic, <handler>)` with a
    hardcoded handler that in several cases did not match the callable
    actually passed to `bus.on()` in `register_enclosure_namespace()` /
    `register_core_events()` (e.g. "enclosure.mouth.talk" was registered
    with `_on_mouth_talk` but removed with `on_talk`), and
    "recognizer_loop:audio_output_end" was registered but never removed at
    all. Since bus listener removal is an identity check on the handler,
    those listeners survived `shutdown()` and kept reacting to events.
    """

    @patch("ovos_plugin_manager.templates.phal.Configuration", return_value={})
    def _make_plugin(self, mock_cfg, bus, name="test-phal"):
        from ovos_plugin_manager.templates.phal import PHALPlugin
        with patch.object(PHALPlugin, "start"):
            plugin = PHALPlugin(bus=bus, name=name, config={})
        return plugin

    def test_shutdown_removes_every_registered_listener(self):
        bus = FakeBus()
        plugin = self._make_plugin(bus=bus)

        self.assertTrue(len(plugin._registered_handlers) > 0)
        for topic, _handler in plugin._registered_handlers:
            self.assertGreaterEqual(len(bus.ee.listeners(topic)), 1,
                                     f"handler for {topic} was not registered on the bus")

        plugin.shutdown()

        for topic, _handler in plugin._registered_handlers:
            self.assertEqual(len(bus.ee.listeners(topic)), 0,
                              f"a listener for {topic} survived shutdown()")

    def test_shutdown_stops_dispatch_for_named_signatures(self):
        # the two topics explicitly called out as broken: a mismatched
        # handler pair (mouth.talk) and a topic missing from shutdown
        # entirely (audio_output_end)
        from ovos_plugin_manager.templates.phal import PHALPlugin
        bus = FakeBus()
        with patch.object(PHALPlugin, "on_talk") as mock_talk, \
                patch.object(PHALPlugin, "on_audio_output_end") as mock_end:
            plugin = self._make_plugin(bus=bus)

            bus.emit(Message("enclosure.mouth.talk"))
            bus.emit(Message("recognizer_loop:audio_output_end"))
            self.assertTrue(mock_talk.called)
            self.assertTrue(mock_end.called)
            mock_talk.reset_mock()
            mock_end.reset_mock()

            plugin.shutdown()

            bus.emit(Message("enclosure.mouth.talk"))
            bus.emit(Message("recognizer_loop:audio_output_end"))
            self.assertFalse(mock_talk.called,
                              "on_talk still fires after shutdown()")
            self.assertFalse(mock_end.called,
                              "on_audio_output_end still fires after shutdown()")

    def test_shutdown_does_not_affect_other_instance(self):
        bus = FakeBus()
        plugin_a = self._make_plugin(bus=bus, name="phal-a")
        plugin_b = self._make_plugin(bus=bus, name="phal-b")

        counts_before = {topic: len(bus.ee.listeners(topic))
                          for topic, _h in plugin_b._registered_handlers}

        plugin_a.shutdown()

        for topic, _handler in plugin_b._registered_handlers:
            # plugin_a's own listener for this shared topic is gone, but
            # plugin_b's must still be there
            self.assertEqual(len(bus.ee.listeners(topic)), counts_before[topic] - 1,
                              f"shutting down plugin_a removed plugin_b's "
                              f"listener for {topic}")


if __name__ == "__main__":
    unittest.main()
