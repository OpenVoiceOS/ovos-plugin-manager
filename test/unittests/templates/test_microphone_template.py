import unittest
from unittest.mock import patch, Mock

_TEST_CONFIG = {
    "microphone": {
        "module": "dummy",
        "dummy": {
            "sample_width": 1,
            "sample_channels": 1,
            "chunk_size": 2048
        },
        "ovos-microphone-plugin-alsa": {
            "sample_width": 2,
            "sample_channels": 1,
            "chunk_size": 4096
        }
    }
}


class TestMicrophoneTemplate(unittest.TestCase):
    def test_microphone_init(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        # Default
        mic = Microphone()
        self.assertIsInstance(mic, Microphone)
        self.assertIsInstance(mic.sample_rate, int)
        self.assertIsInstance(mic.sample_width, int)
        self.assertIsInstance(mic.sample_channels, int)
        self.assertIsInstance(mic.chunk_size, int)

        # Partial override with kwargs
        mic_2 = Microphone(**_TEST_CONFIG['microphone']['dummy'])
        self.assertIsInstance(mic_2, Microphone)
        self.assertIsInstance(mic_2.sample_rate, int)
        self.assertEqual(mic_2.sample_width, 1)
        self.assertEqual(mic_2.sample_channels, 1)
        self.assertEqual(mic_2.chunk_size, 2048)

        # Override positional params
        mic_3 = Microphone(1, 2, 3, 4)
        self.assertIsInstance(mic_3, Microphone)
        self.assertEqual(mic_3.sample_rate, 1)
        self.assertEqual(mic_3.sample_width, 2)
        self.assertEqual(mic_3.sample_channels, 3)
        self.assertEqual(mic_3.chunk_size, 4)

        self.assertNotEquals(mic, mic_2)
        self.assertNotEquals(mic, mic_3)

    def test_properties(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        mic = Microphone()
        self.assertIsInstance(mic.frames_per_chunk, int)
        self.assertGreaterEqual(mic.frames_per_chunk, 0)
        self.assertIsInstance(mic.seconds_per_chunk, float)
        self.assertGreaterEqual(mic.seconds_per_chunk, 0)

    def test_methods(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        # Test failure cases
        mic = Microphone()
        with self.assertRaises(NotImplementedError):
            mic.start()
        with self.assertRaises(NotImplementedError):
            mic.read_chunk()
        with self.assertRaises(NotImplementedError):
            mic.stop()

        mock_start = Mock()
        mock_read = Mock(return_value=b'1234')
        mock_stop = Mock()

        class MockMic(Microphone):
            def start(self):
                mock_start()

            def read_chunk(self):
                return mock_read()

            def stop(self):
                mock_stop()

        # Test mic
        mic = MockMic()
        mic.start()
        mock_start.assert_called_once()
        chunk = mic.read_chunk()
        self.assertEqual(chunk, b'1234')
        mock_read.assert_called_once()
        mic.stop()
        mock_stop.assert_called_once()
