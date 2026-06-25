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


class TestPHALPluginIsBareBase(unittest.TestCase):
    """The base wires no bus events and carries no enclosure/lifecycle handlers."""

    def test_no_bus_subscriptions_on_init(self) -> None:
        """The base plugin does not wire any bus events on construction."""
        plugin = _make_plugin()
        self.assertEqual(plugin.bus.on.call_args_list, [])

    def test_no_enclosure_abstraction_attributes(self) -> None:
        """The dropped enclosure abstraction leaves no attributes behind."""
        plugin = _make_plugin()
        self.assertFalse(hasattr(plugin, "register_enclosure_namespace"))
        self.assertFalse(hasattr(plugin, "register_core_events"))
        self.assertFalse(hasattr(plugin, "mouth_events_active"))
        self.assertFalse(hasattr(plugin, "on_eyes_on"))
        self.assertFalse(hasattr(plugin, "on_weather_display"))

    def test_no_lifecycle_handlers(self) -> None:
        """The record/speak/wake/sleep handlers moved to the listener mix-in."""
        plugin = _make_plugin()
        for name in ("on_record_begin", "on_record_end", "on_audio_output_start",
                     "on_audio_output_end", "on_awake", "on_sleep", "on_speak"):
            self.assertFalse(hasattr(plugin, name), name)


class TestPHALPluginLifecycle(unittest.TestCase):
    """Tests for the bare plugin lifecycle (run/shutdown)."""

    def test_run_does_not_raise(self) -> None:
        _make_plugin().run()

    def test_shutdown_sets_running_false(self) -> None:
        """shutdown sets _running to False without touching the bus."""
        plugin = _make_plugin()
        plugin.shutdown()
        self.assertFalse(plugin._running)
        self.assertEqual(plugin.bus.remove.call_args_list, [])


class TestAdminPluginExtended(unittest.TestCase):
    """Tests for AdminPlugin (inherits PHALPlugin)."""

    def test_admin_plugin_runtime_requirements(self) -> None:
        """AdminPlugin inherits runtime_requirements from PHALPlugin."""
        reqs = AdminPlugin.runtime_requirements
        self.assertFalse(reqs.requires_internet)


if __name__ == "__main__":
    unittest.main()
