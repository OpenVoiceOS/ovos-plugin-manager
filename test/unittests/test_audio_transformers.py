import unittest
import time
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes, ReadWriteStream


class TestReadWriteStream(unittest.TestCase):
    def test_write_and_read(self):
        # Initialize the stream
        stream = ReadWriteStream()

        # Write some data to the stream
        stream.write(b'1234567890abcdefghijklmnopqrstuvwxyz')

        # Read some data from the stream
        self.assertEqual(stream.read(10), b'1234567890')

        # Read more data with a timeout
        self.assertEqual(stream.read(5, timeout=1), b'abcde')

    def test_clear_buffer(self):
        # Initialize the stream
        stream = ReadWriteStream()

        # Write some data to the stream
        stream.write(b'1234567890abcdefghijklmnopqrstuvwxyz')

        # Clear the buffer
        stream.clear()
        self.assertEqual(len(stream), 0)

    def test_write_with_max_size(self):
        # Initialize the stream with a max size of 20 bytes
        stream = ReadWriteStream(max_size=20)

        # Write some data to the stream
        stream.write(b'1234567890abcdefghijklmnopqrstuvwxyz')

        # The buffer should have been trimmed to the last 20 bytes
        self.assertEqual(stream.read(20), b'ghijklmnopqrstuvwxyz')

    def test_clear_buffer_with_max_size(self):
        # Initialize the stream with a max size of 20 bytes
        stream = ReadWriteStream(max_size=20)

        # Write some data to the stream
        stream.write(b'1234567890abcdefghijklmnopqrstuvwxyz')

        # Clear the buffer
        stream.clear()
        self.assertEqual(len(stream), 0)


class TestAudioTransformersTemplate(unittest.TestCase):
    def test_audio_transformer(self):
        pass
        # TODO


class TestAudioTransformers(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.AUDIO_TRANSFORMER
    CONFIG_TYPE = PluginConfigTypes.AUDIO_TRANSFORMER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.audio_transformers import \
            find_audio_transformer_plugins
        find_audio_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.audio_transformers import \
            load_audio_transformer_plugin
        load_audio_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.audio_transformers import \
            get_audio_transformer_configs
        get_audio_transformer_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.audio_transformers import \
            get_audio_transformer_module_configs
        get_audio_transformer_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)
