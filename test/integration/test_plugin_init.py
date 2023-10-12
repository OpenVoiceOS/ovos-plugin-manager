import unittest
import importlib
import ovos_plugin_manager.tts

from os import environ
from os.path import join, dirname, isdir, isfile
from shutil import rmtree
from unittest.mock import patch, Mock

environ["OVOS_DEFAULT_LOG_NAME"] = "test"
environ["OVOS_DEFAULT_LOG_LEVEL"] = "DEBUG"


class TestPluginInit(unittest.TestCase):
    # @patch("ovos_utils.log.LOG")
    # def test_init_logging(self, log):
    #     from ovos_plugin_manager.tts import load_tts_plugin
    #     plugin = load_tts_plugin("ovos-tts-plugin-espeakng")
    #     log.reset_mock()
    #     tts = plugin()
    #     log.debug.assert_any_call(f"Amplitude: None")
    #     log.debug.assert_any_call(tts.config)
    #     tts.shutdown()

    def test_log_method_called(self):
        from ovos_utils.log import LOG
        from ovos_plugin_manager.tts import load_tts_plugin
        real_debug = LOG.debug
        LOG.debug = Mock()

        plugin = load_tts_plugin("ovos-tts-plugin-espeakng")
        tts = plugin()
        LOG.info(LOG.debug.call_args_list)
        LOG.debug.assert_any_call(f"Amplitude: None")
        LOG.debug.assert_any_call(tts.config)
        tts.shutdown()

        LOG.debug = real_debug

    # @patch("mycroft.Configuration")
    # def test_log_output(self, config):
    #     from ovos_utils.log import LOG
    #     from ovos_plugin_manager.tts import load_tts_plugin
    #
    #     # Init log config
    #     test_log_dir = join(dirname(__file__), "logs")
    #     test_log_level = "DEBUG"
    #     environ["OVOS_DEFAULT_LOG_NAME"] = "test"
    #
    #     # Mock config for `mycroft` module init
    #     config.return_vaule = {
    #         "log_level": test_log_level,
    #         "logs": {
    #             "path": test_log_dir,
    #             "max_bytes": 50000000,
    #             "backup_count": 1,
    #             "diagnostic": False
    #         }
    #     }
    #     LOG.init({"path": test_log_dir, "level": test_log_level})
    #
    #     plugin = load_tts_plugin("ovos-tts-plugin-espeakng")
    #     self.assertEqual(LOG.base_path, test_log_dir, LOG.base_path)
    #     self.assertEqual(LOG.level, test_log_level, LOG.level)
    #
    #     tts = plugin()
    #
    #     self.assertEqual(LOG.base_path, test_log_dir, LOG.base_path)
    #     self.assertEqual(LOG.level, test_log_level, LOG.level)
    #     self.assertTrue(isdir(test_log_dir), test_log_dir)
    #     self.assertTrue(isfile(join(test_log_dir, "test.log")))
    #     with open(join(test_log_dir, "test.log"), 'r') as f:
    #         logs = f.read()
    #     self.assertIn("Amplitude: ", logs)
    #     self.assertIn(f"{tts.config}", logs)
    #
    #     # Cleanup
    #     tts.shutdown()
    #     rmtree(test_log_dir)
