import unittest
from copy import deepcopy
from unittest.mock import patch


class TestLed(unittest.TestCase):
    def test_color(self):
        from ovos_plugin_manager.hardware.led import Color
        self.assertIsInstance(Color.BLACK, Color)
        self.assertIsInstance(Color.BLACK.value, tuple)
        self.assertEqual(Color.WHITE, Color.from_name('white'))
        self.assertIsInstance(Color.RED.as_rgb_tuple(), tuple)
        with self.assertRaises(ValueError):
            Color.from_name('not a color')
