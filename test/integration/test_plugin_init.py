import unittest

from os import environ
from os.path import join, dirname, isdir, isfile
from shutil import rmtree
from unittest.mock import patch

environ["OVOS_DEFAULT_LOG_LEVEL"] = "DEBUG"


class TestPluginInit(unittest.TestCase):
    @patch("mycroft.Configuration")
    def test_log_output(self, config):
        # Init log config
        test_log_dir = join(dirname(__file__), "logs")
        test_log_level = "DEBUG"
        test_log_name = "test"

        from ovos_utils.log import LOG
        from ovos_plugin_manager.tts import load_tts_plugin

        # Mock config for `mycroft` module init
        config.return_vaule = {
            "log_level": test_log_level,
            "logs": {
                "path": test_log_dir,
                "max_bytes": 50000000,
                "backup_count": 1,
                "diagnostic": False
            }
        }

        # This is basically what `init_service_logger` does but with test config
        LOG.init({"path": test_log_dir, "level": test_log_level})
        LOG.name = test_log_name

        plugin = load_tts_plugin("ovos-tts-plugin-espeakng")
        self.assertEqual(LOG.base_path, test_log_dir, LOG.base_path)
        self.assertEqual(LOG.level, test_log_level, LOG.level)
        self.assertEqual(LOG.name, test_log_name, LOG.name)

        tts = plugin()

        self.assertEqual(LOG.base_path, test_log_dir, LOG.base_path)
        self.assertEqual(LOG.level, test_log_level, LOG.level)
        self.assertEqual(LOG.name, test_log_name, LOG.name)
        self.assertTrue(isdir(test_log_dir), test_log_dir)
        self.assertTrue(isfile(join(test_log_dir, "test.log")))
        with open(join(test_log_dir, "test.log"), 'r') as f:
            logs = f.read()
        self.assertIn("Amplitude: ", logs)
        self.assertIn(f"{tts.config}", logs)

        # Cleanup
        tts.shutdown()
        rmtree(test_log_dir)
