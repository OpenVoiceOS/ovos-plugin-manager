# Copyright 2024, OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Extended unit tests for ovos_plugin_manager.templates.phal.PHALPlugin."""

import unittest
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.phal import AdminPlugin, PHALPlugin, PHALValidator


def _make_plugin(name: str = "test-phal") -> PHALPlugin:
    """Create a PHALPlugin instance with a mocked bus and no thread start."""
    bus: MagicMock = MagicMock()
    with patch("ovos_plugin_manager.templates.phal.get_mycroft_bus", return_value=bus), \
         patch("ovos_plugin_manager.templates.phal.Configuration", return_value={}), \
         patch.object(PHALPlugin, "start"):
        plugin = PHALPlugin(bus=bus, name=name, config={})
    return plugin


class TestPHALPluginRuntimeRequirements(unittest.TestCase):
    """Tests for PHALPlugin.runtime_requirements."""

    def test_runtime_requirements_no_internet(self) -> None:
        """runtime_requirements declares no internet required."""
        reqs = PHALPlugin.runtime_requirements
        self.assertFalse(reqs.internet_before_load)
        self.assertFalse(reqs.requires_internet)

    def test_runtime_requirements_no_network(self) -> None:
        """runtime_requirements declares no network required."""
        reqs = PHALPlugin.runtime_requirements
        self.assertFalse(reqs.network_before_load)
        self.assertFalse(reqs.requires_network)

    def test_runtime_requirements_fallbacks_allowed(self) -> None:
        """runtime_requirements allows no-internet and no-network fallbacks."""
        reqs = PHALPlugin.runtime_requirements
        self.assertTrue(reqs.no_internet_fallback)
        self.assertTrue(reqs.no_network_fallback)


class TestPHALPluginCoreEvents(unittest.TestCase):
    """Tests for the core lifecycle bus subscriptions wired on init."""

    def test_register_core_events_subscribes(self) -> None:
        """register_core_events wires the audio/wake/speak lifecycle events."""
        plugin = _make_plugin()
        wired = {call.args[0] for call in plugin.bus.on.call_args_list}
        self.assertEqual(wired, {
            "recognizer_loop:record_begin",
            "recognizer_loop:record_end",
            "recognizer_loop:sleep",
            "recognizer_loop:audio_output_start",
            "recognizer_loop:audio_output_end",
            "mycroft.awoken",
            "speak",
        })

    def test_no_enclosure_namespace_wired(self) -> None:
        """No enclosure.* subscriptions are wired by the base plugin."""
        plugin = _make_plugin()
        wired = {call.args[0] for call in plugin.bus.on.call_args_list}
        self.assertFalse(any(t.startswith("enclosure.") for t in wired))

    def test_no_enclosure_abstraction_attributes(self) -> None:
        """The dropped enclosure abstraction leaves no attributes behind."""
        plugin = _make_plugin()
        self.assertFalse(hasattr(plugin, "register_enclosure_namespace"))
        self.assertFalse(hasattr(plugin, "mouth_events_active"))
        self.assertFalse(hasattr(plugin, "on_eyes_on"))
        self.assertFalse(hasattr(plugin, "on_weather_display"))


class TestPHALPluginEventHandlers(unittest.TestCase):
    """Tests for PHALPlugin stub event handler methods (all are no-ops by default)."""

    def setUp(self) -> None:
        """Create a plugin instance."""
        self.plugin: PHALPlugin = _make_plugin()

    def test_on_record_begin(self) -> None:
        """on_record_begin does not raise."""
        self.plugin.on_record_begin()

    def test_on_record_end(self) -> None:
        """on_record_end does not raise."""
        self.plugin.on_record_end()

    def test_on_audio_output_start(self) -> None:
        """on_audio_output_start does not raise."""
        self.plugin.on_audio_output_start()

    def test_on_audio_output_end(self) -> None:
        """on_audio_output_end does not raise."""
        self.plugin.on_audio_output_end()

    def test_on_awake(self) -> None:
        """on_awake does not raise."""
        self.plugin.on_awake()

    def test_on_sleep(self) -> None:
        """on_sleep does not raise."""
        self.plugin.on_sleep()

    def test_on_speak(self) -> None:
        """on_speak does not raise."""
        self.plugin.on_speak()

    def test_run(self) -> None:
        """run does not raise."""
        self.plugin.run()


class TestPHALPluginShutdown(unittest.TestCase):
    """Tests for PHALPlugin.shutdown."""

    def test_shutdown_sets_running_false(self) -> None:
        """shutdown sets _running to False."""
        plugin = _make_plugin()
        plugin.shutdown()
        self.assertFalse(plugin._running)

    def test_shutdown_removes_core_events(self) -> None:
        """shutdown removes the core lifecycle subscriptions."""
        plugin = _make_plugin()
        plugin.shutdown()
        removed = {call.args[0] for call in plugin.bus.remove.call_args_list}
        self.assertEqual(removed, {
            "mycroft.awoken",
            "recognizer_loop:sleep",
            "speak",
            "recognizer_loop:record_begin",
            "recognizer_loop:record_end",
            "recognizer_loop:audio_output_start",
            "recognizer_loop:audio_output_end",
        })


class TestAdminPluginExtended(unittest.TestCase):
    """Tests for AdminPlugin (inherits PHALPlugin)."""

    def test_admin_plugin_runtime_requirements(self) -> None:
        """AdminPlugin inherits runtime_requirements from PHALPlugin."""
        reqs = AdminPlugin.runtime_requirements
        self.assertFalse(reqs.requires_internet)


if __name__ == "__main__":
    unittest.main()
