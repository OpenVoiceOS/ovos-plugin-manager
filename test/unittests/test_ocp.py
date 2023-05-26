import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestOCPTemplate(unittest.TestCase):
    def test_ocp_stream_extractor(self):
        from ovos_plugin_manager.templates.ocp import OCPStreamExtractor
        # TODO


class TestOCP(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.STREAM_EXTRACTOR
    CONFIG_TYPE = PluginConfigTypes.STREAM_EXTRACTOR
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.ocp import find_ocp_plugins
        find_ocp_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    def test_stream_handler(self):
        from ovos_plugin_manager.ocp import StreamHandler
        # TODO
