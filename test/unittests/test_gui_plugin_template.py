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

"""Unit tests for AbstractGUIPlugin and GUIExtension in templates/gui.py."""

import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from ovos_bus_client import Message
from ovos_utils.fakebus import FakeBus

from ovos_plugin_manager.templates.gui import AbstractGUIPlugin, GUIExtension


class _ConcreteGUIPlugin(AbstractGUIPlugin):
    """Minimal concrete AbstractGUIPlugin for testing."""

    def __init__(self, config: Dict[str, Any], bus=None) -> None:
        """Initialise plugin."""
        super().__init__(config, bus=bus)
        self.idle_called = False
        self.namespace_activated = None
        self.last_template = None
        self.last_skill = None
        self.last_data = None

    def handle_show_idle(self, skill_id: str, data: Dict[str, Any], site_id: str = "default") -> None:
        """Mark idle as called."""
        self.idle_called = True
        self.last_skill = skill_id
        self.last_data = data

    def on_namespace_activated(self, skill_id: str, site_id: str = "default") -> None:
        """Track activation."""
        self.namespace_activated = skill_id

    def on_idle(self) -> None:
        """Mark idle state."""
        self.idle_called = True


class TestAbstractGUIPlugin(unittest.TestCase):
    """Tests for AbstractGUIPlugin template class."""

    def setUp(self) -> None:
        """Create plugin instance."""
        self.bus = FakeBus()
        self.plugin = _ConcreteGUIPlugin(config={"test": True}, bus=self.bus)

    def test_init_config(self) -> None:
        """Plugin stores config."""
        self.assertEqual(self.plugin.config, {"test": True})

    def test_init_bus(self) -> None:
        """Plugin stores bus."""
        self.assertIs(self.plugin.bus, self.bus)

    def test_dispatch_known_template(self) -> None:
        """dispatch_template calls correct handler for known template."""
        self.plugin.dispatch_template("SYSTEM_idle", "test_skill", {"key": "val"})
        self.assertTrue(self.plugin.idle_called)
        self.assertEqual(self.plugin.last_skill, "test_skill")
        self.assertEqual(self.plugin.last_data, {"key": "val"})

    def test_dispatch_unknown_template(self) -> None:
        """dispatch_template logs warning for unknown template (no exception)."""
        # Should not raise
        self.plugin.dispatch_template("UNKNOWN_TEMPLATE", "skill", {})

    def test_dispatch_handler_exception_does_not_propagate(self) -> None:
        """dispatch_template catches handler exceptions."""

        class _RaisingPlugin(_ConcreteGUIPlugin):
            """Plugin that raises on handle_show_idle."""

            def handle_show_idle(self, skill_id: str, data: Dict[str, Any],
                                 site_id: str = "default") -> None:
                """Raise on purpose."""
                raise RuntimeError("test error")

        plugin = _RaisingPlugin({})
        # Should not propagate
        plugin.dispatch_template("SYSTEM_idle", "skill", {})

    def test_all_noop_handlers(self) -> None:
        """All default no-op handlers can be called without errors."""
        noop_templates = [
            "SYSTEM_loading", "SYSTEM_status", "SYSTEM_error", "SYSTEM_text",
            "SYSTEM_image", "SYSTEM_animated_image", "SYSTEM_list", "SYSTEM_grid",
            "SYSTEM_table", "SYSTEM_html", "SYSTEM_url", "SYSTEM_audio_player",
            "SYSTEM_video_player", "SYSTEM_clock", "SYSTEM_timer", "SYSTEM_weather",
            "SYSTEM_map", "SYSTEM_confirm", "SYSTEM_select", "SYSTEM_face",
            "SYSTEM_ocp_now_playing", "SYSTEM_ocp_search", "SYSTEM_ocp_playlist",
        ]
        for tmpl in noop_templates:
            with self.subTest(template=tmpl):
                self.plugin.dispatch_template(tmpl, "skill", {})

    def test_on_namespace_activated(self) -> None:
        """on_namespace_activated hook is callable."""
        self.plugin.on_namespace_activated("my_skill")
        self.assertEqual(self.plugin.namespace_activated, "my_skill")

    def test_on_namespace_deactivated(self) -> None:
        """on_namespace_deactivated is a no-op by default."""
        # Should not raise
        self.plugin.on_namespace_deactivated("skill_id")

    def test_on_idle(self) -> None:
        """on_idle hook is callable."""
        self.plugin.on_idle()
        self.assertTrue(self.plugin.idle_called)

    def test_on_status_event(self) -> None:
        """on_status_event is a no-op by default."""
        self.plugin.on_status_event("speak", {"utterance": "hello"})

    def test_on_session_update(self) -> None:
        """on_session_update is a no-op by default."""
        self.plugin.on_session_update("skill_id", {"key": "val"})

    def test_template_handlers_dict(self) -> None:
        """_TEMPLATE_HANDLERS maps template names to method names."""
        self.assertIn("SYSTEM_idle", _ConcreteGUIPlugin._TEMPLATE_HANDLERS)
        self.assertIn("SYSTEM_weather", _ConcreteGUIPlugin._TEMPLATE_HANDLERS)

    def test_init_no_bus(self) -> None:
        """Plugin can be created without a bus."""
        plugin = _ConcreteGUIPlugin({})
        self.assertIsNone(plugin.bus)


class TestGUIExtensionHandleRemoveNamespace(unittest.TestCase):
    """Tests for GUIExtension.handle_remove_namespace."""

    def _make_ext(self) -> GUIExtension:
        """Create a GUIExtension with all heavy init mocked out."""
        bus = FakeBus()
        with patch.object(GUIExtension, "__init__", lambda self, *a, **kw: None):
            ext = GUIExtension.__new__(GUIExtension)
        ext.bus = bus
        ext.config = {}
        ext.gui = MagicMock()
        ext.preload_gui = False
        ext.permanent = False
        ext.homescreen_manager = None
        return ext

    def test_handle_remove_namespace_with_skill_id(self) -> None:
        """handle_remove_namespace emits gui.clear.namespace when skill_id given."""
        ext = self._make_ext()
        emitted = []
        ext.bus.on("gui.clear.namespace", lambda m: emitted.append(m))
        msg = Message("mycroft.gui.screen.close", {"skill_id": "test_skill"})
        ext.handle_remove_namespace(msg)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0].data["__from"], "test_skill")

    def test_handle_remove_namespace_without_skill_id(self) -> None:
        """handle_remove_namespace does nothing when no skill_id."""
        ext = self._make_ext()
        emitted = []
        ext.bus.on("gui.clear.namespace", lambda m: emitted.append(m))
        msg = Message("mycroft.gui.screen.close", {})
        ext.handle_remove_namespace(msg)
        self.assertEqual(len(emitted), 0)

    def test_bind_homescreen_not_configured(self) -> None:
        """bind_homescreen does nothing when homescreen_supported not set."""
        ext = self._make_ext()
        ext.bind_homescreen()
        self.assertIsNone(ext.homescreen_manager)


if __name__ == "__main__":
    unittest.main()
