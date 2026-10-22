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


class TestPHALPluginMouthEvents(unittest.TestCase):
    """Tests for mouth event activation, deactivation, and delegate methods."""

    def setUp(self) -> None:
        """Create a plugin instance."""
        self.plugin: PHALPlugin = _make_plugin()

    def test_mouth_events_initially_true(self) -> None:
        """mouth_events_active is True after _activate_mouth_events called during init."""
        self.assertTrue(self.plugin.mouth_events_active)

    def test_deactivate_mouth_events(self) -> None:
        """_deactivate_mouth_events sets mouth_events_active to False."""
        self.plugin._deactivate_mouth_events()
        self.assertFalse(self.plugin.mouth_events_active)

    def test_activate_mouth_events(self) -> None:
        """_activate_mouth_events sets mouth_events_active to True."""
        self.plugin._deactivate_mouth_events()
        self.plugin._activate_mouth_events()
        self.assertTrue(self.plugin.mouth_events_active)

    def _activate(self) -> None:
        """Helper: ensure mouth events are active."""
        self.plugin._activate_mouth_events()

    def _deactivate(self) -> None:
        """Helper: ensure mouth events are inactive."""
        self.plugin._deactivate_mouth_events()

    def test_on_mouth_talk_active(self) -> None:
        """_on_mouth_talk delegates to on_talk when active."""
        self._activate()
        self.plugin.on_talk = MagicMock()
        self.plugin._on_mouth_talk(MagicMock())
        self.plugin.on_talk.assert_called_once()

    def test_on_mouth_talk_inactive(self) -> None:
        """_on_mouth_talk does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_talk = MagicMock()
        self.plugin._on_mouth_talk(MagicMock())
        self.plugin.on_talk.assert_not_called()

    def test_on_mouth_think_active(self) -> None:
        """_on_mouth_think delegates to on_think when active."""
        self._activate()
        self.plugin.on_think = MagicMock()
        self.plugin._on_mouth_think(MagicMock())
        self.plugin.on_think.assert_called_once()

    def test_on_mouth_think_inactive(self) -> None:
        """_on_mouth_think does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_think = MagicMock()
        self.plugin._on_mouth_think(MagicMock())
        self.plugin.on_think.assert_not_called()

    def test_on_mouth_listen_active(self) -> None:
        """_on_mouth_listen delegates to on_listen when active."""
        self._activate()
        self.plugin.on_listen = MagicMock()
        self.plugin._on_mouth_listen(MagicMock())
        self.plugin.on_listen.assert_called_once()

    def test_on_mouth_listen_inactive(self) -> None:
        """_on_mouth_listen does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_listen = MagicMock()
        self.plugin._on_mouth_listen(MagicMock())
        self.plugin.on_listen.assert_not_called()

    def test_on_mouth_smile_active(self) -> None:
        """_on_mouth_smile delegates to on_smile when active."""
        self._activate()
        self.plugin.on_smile = MagicMock()
        self.plugin._on_mouth_smile(MagicMock())
        self.plugin.on_smile.assert_called_once()

    def test_on_mouth_smile_inactive(self) -> None:
        """_on_mouth_smile does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_smile = MagicMock()
        self.plugin._on_mouth_smile(MagicMock())
        self.plugin.on_smile.assert_not_called()

    def test_on_mouth_viseme_active(self) -> None:
        """_on_mouth_viseme delegates to on_viseme when active."""
        self._activate()
        self.plugin.on_viseme = MagicMock()
        self.plugin._on_mouth_viseme(MagicMock())
        self.plugin.on_viseme.assert_called_once()

    def test_on_mouth_viseme_inactive(self) -> None:
        """_on_mouth_viseme does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_viseme = MagicMock()
        self.plugin._on_mouth_viseme(MagicMock())
        self.plugin.on_viseme.assert_not_called()

    def test_on_mouth_viseme_list_active(self) -> None:
        """_on_mouth_viseme_list delegates to on_viseme_list when active."""
        self._activate()
        self.plugin.on_viseme_list = MagicMock()
        self.plugin._on_mouth_viseme_list(MagicMock())
        self.plugin.on_viseme_list.assert_called_once()

    def test_on_mouth_viseme_list_inactive(self) -> None:
        """_on_mouth_viseme_list does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_viseme_list = MagicMock()
        self.plugin._on_mouth_viseme_list(MagicMock())
        self.plugin.on_viseme_list.assert_not_called()

    def test_on_mouth_reset_active(self) -> None:
        """_on_mouth_reset delegates to on_display_reset when active."""
        self._activate()
        self.plugin.on_display_reset = MagicMock()
        self.plugin._on_mouth_reset(MagicMock())
        self.plugin.on_display_reset.assert_called_once()

    def test_on_mouth_reset_inactive(self) -> None:
        """_on_mouth_reset does not delegate when inactive."""
        self._deactivate()
        self.plugin.on_display_reset = MagicMock()
        self.plugin._on_mouth_reset(MagicMock())
        self.plugin.on_display_reset.assert_not_called()


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

    def test_on_reset(self) -> None:
        """on_reset does not raise."""
        self.plugin.on_reset()

    def test_on_no_internet(self) -> None:
        """on_no_internet does not raise."""
        self.plugin.on_no_internet()

    def test_on_system_reset(self) -> None:
        """on_system_reset does not raise."""
        self.plugin.on_system_reset()

    def test_on_system_mute(self) -> None:
        """on_system_mute does not raise."""
        self.plugin.on_system_mute()

    def test_on_system_unmute(self) -> None:
        """on_system_unmute does not raise."""
        self.plugin.on_system_unmute()

    def test_on_system_blink(self) -> None:
        """on_system_blink does not raise."""
        self.plugin.on_system_blink()

    def test_on_eyes_on(self) -> None:
        """on_eyes_on does not raise."""
        self.plugin.on_eyes_on()

    def test_on_eyes_off(self) -> None:
        """on_eyes_off does not raise."""
        self.plugin.on_eyes_off()

    def test_on_eyes_fill(self) -> None:
        """on_eyes_fill does not raise."""
        self.plugin.on_eyes_fill()

    def test_on_eyes_blink(self) -> None:
        """on_eyes_blink does not raise."""
        self.plugin.on_eyes_blink()

    def test_on_eyes_narrow(self) -> None:
        """on_eyes_narrow does not raise."""
        self.plugin.on_eyes_narrow()

    def test_on_eyes_look(self) -> None:
        """on_eyes_look does not raise."""
        self.plugin.on_eyes_look()

    def test_on_eyes_color(self) -> None:
        """on_eyes_color does not raise."""
        self.plugin.on_eyes_color()

    def test_on_eyes_brightness(self) -> None:
        """on_eyes_brightness does not raise."""
        self.plugin.on_eyes_brightness()

    def test_on_eyes_reset(self) -> None:
        """on_eyes_reset does not raise."""
        self.plugin.on_eyes_reset()

    def test_on_eyes_timed_spin(self) -> None:
        """on_eyes_timed_spin does not raise."""
        self.plugin.on_eyes_timed_spin()

    def test_on_eyes_volume(self) -> None:
        """on_eyes_volume does not raise."""
        self.plugin.on_eyes_volume()

    def test_on_eyes_spin(self) -> None:
        """on_eyes_spin does not raise."""
        self.plugin.on_eyes_spin()

    def test_on_eyes_set_pixel(self) -> None:
        """on_eyes_set_pixel does not raise."""
        self.plugin.on_eyes_set_pixel()

    def test_on_display_reset(self) -> None:
        """on_display_reset does not raise."""
        self.plugin.on_display_reset()

    def test_on_talk(self) -> None:
        """on_talk does not raise."""
        self.plugin.on_talk()

    def test_on_think(self) -> None:
        """on_think does not raise."""
        self.plugin.on_think()

    def test_on_listen(self) -> None:
        """on_listen does not raise."""
        self.plugin.on_listen()

    def test_on_smile(self) -> None:
        """on_smile does not raise."""
        self.plugin.on_smile()

    def test_on_viseme(self) -> None:
        """on_viseme does not raise."""
        self.plugin.on_viseme()

    def test_on_viseme_list(self) -> None:
        """on_viseme_list does not raise."""
        self.plugin.on_viseme_list()

    def test_on_text(self) -> None:
        """on_text does not raise."""
        self.plugin.on_text()

    def test_on_display(self) -> None:
        """on_display does not raise."""
        self.plugin.on_display()

    def test_on_weather_display(self) -> None:
        """on_weather_display does not raise."""
        self.plugin.on_weather_display()

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

    def test_shutdown_deactivates_mouth_events(self) -> None:
        """shutdown deactivates mouth events."""
        plugin = _make_plugin()
        plugin.shutdown()
        self.assertFalse(plugin.mouth_events_active)


class TestAdminPluginExtended(unittest.TestCase):
    """Tests for AdminPlugin (inherits PHALPlugin)."""

    def test_admin_plugin_runtime_requirements(self) -> None:
        """AdminPlugin inherits runtime_requirements from PHALPlugin."""
        reqs = AdminPlugin.runtime_requirements
        self.assertFalse(reqs.requires_internet)


if __name__ == "__main__":
    unittest.main()
