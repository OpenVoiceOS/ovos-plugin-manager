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

"""Unit tests for ovos_plugin_manager.gui module (discovery + factory)."""

import unittest
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.utils import PluginTypes


class TestGUIModuleFunctions(unittest.TestCase):
    """Tests for find/load/get functions in ovos_plugin_manager.gui."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_gui_adapter_plugins(self, mock_find: MagicMock) -> None:
        """find_gui_adapter_plugins uses GUI_ADAPTER plugin type."""
        from ovos_plugin_manager.gui import find_gui_adapter_plugins
        mock_find.return_value = {}
        find_gui_adapter_plugins()
        mock_find.assert_called_once_with(PluginTypes.GUI_ADAPTER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_gui_adapter_plugin(self, mock_load: MagicMock) -> None:
        """load_gui_adapter_plugin calls load_plugin with GUI_ADAPTER."""
        from ovos_plugin_manager.gui import load_gui_adapter_plugin
        mock_load.return_value = MagicMock()
        load_gui_adapter_plugin("my-adapter")
        mock_load.assert_called_once_with("my-adapter", PluginTypes.GUI_ADAPTER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_gui_plugins(self, mock_find: MagicMock) -> None:
        """find_gui_plugins calls find_plugins with GUI."""
        from ovos_plugin_manager.gui import find_gui_plugins
        mock_find.return_value = {}
        find_gui_plugins()
        mock_find.assert_called_once_with(PluginTypes.GUI)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_gui_plugin(self, mock_load: MagicMock) -> None:
        """load_gui_plugin calls load_plugin with GUI."""
        from ovos_plugin_manager.gui import load_gui_plugin
        mock_load.return_value = MagicMock()
        load_gui_plugin("my-gui")
        mock_load.assert_called_once_with("my-gui", PluginTypes.GUI)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_gui_configs(self, mock_load: MagicMock) -> None:
        """get_gui_configs calls load_configs_for_plugin_type with GUI."""
        from ovos_plugin_manager.gui import get_gui_configs
        mock_load.return_value = {}
        result = get_gui_configs()
        self.assertEqual(result, {})

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_gui_module_configs_list(self, mock_load: MagicMock) -> None:
        """get_gui_module_configs wraps list config in dict."""
        from ovos_plugin_manager.gui import get_gui_module_configs
        mock_load.return_value = [{"key": "val"}]
        result = get_gui_module_configs("my-gui")
        self.assertIsInstance(result, dict)
        self.assertIn("my-gui", result)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_gui_module_configs_dict(self, mock_load: MagicMock) -> None:
        """get_gui_module_configs returns dict unchanged."""
        from ovos_plugin_manager.gui import get_gui_module_configs
        mock_load.return_value = {"my-gui": [{"key": "val"}]}
        result = get_gui_module_configs("my-gui")
        self.assertIsInstance(result, dict)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_gui_config(self, mock_get: MagicMock) -> None:
        """get_gui_config calls get_plugin_config."""
        from ovos_plugin_manager.gui import get_gui_config
        mock_get.return_value = {"module": "test"}
        result = get_gui_config()
        self.assertEqual(result["module"], "test")


class TestOVOSGuiFactory(unittest.TestCase):
    """Tests for OVOSGuiFactory."""

    @patch("ovos_plugin_manager.gui.get_gui_config")
    def test_get_class_generic(self, mock_config: MagicMock) -> None:
        """get_class returns GUIExtension when module is 'generic'."""
        from ovos_plugin_manager.gui import OVOSGuiFactory
        from ovos_plugin_manager.templates.gui import GUIExtension
        mock_config.return_value = {"module": "generic"}
        clazz = OVOSGuiFactory.get_class()
        self.assertIs(clazz, GUIExtension)

    @patch("ovos_plugin_manager.gui.load_gui_plugin")
    @patch("ovos_plugin_manager.gui.get_gui_config")
    def test_get_class_custom(self, mock_config: MagicMock,
                              mock_load: MagicMock) -> None:
        """get_class calls load_gui_plugin for non-generic modules."""
        from ovos_plugin_manager.gui import OVOSGuiFactory
        mock_config.return_value = {"module": "custom-gui"}
        mock_cls = MagicMock()
        mock_load.return_value = mock_cls
        clazz = OVOSGuiFactory.get_class()
        mock_load.assert_called_once_with("custom-gui")
        self.assertIs(clazz, mock_cls)


if __name__ == "__main__":
    unittest.main()
