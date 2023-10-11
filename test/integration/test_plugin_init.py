import unittest
from unittest.mock import patch


class TestPluginInit(unittest.TestCase):
    @patch("ovos_utils.log.LOG")
    def test_init_logging(self, log):
        from ovos_plugin_manager.tts import load_tts_plugin
        plugin = load_tts_plugin("ovos-tts-plugin-espeakng")
        log.reset_mock()
        tts = plugin()
        log.debug.assert_any_call(f"Amplitude: None")
        log.debug.assert_any_call(tts.config)
