import unittest


class TestLed(unittest.TestCase):
    def test_color(self):
        from ovos_plugin_manager.hardware.led import Color

        # Check types
        self.assertIsInstance(Color.BLACK, Color)
        self.assertIsInstance(Color.BLACK.value, tuple)

        # from_name
        self.assertEqual(Color.WHITE, Color.from_name('white'))
        with self.assertRaises(ValueError):
            Color.from_name('not a color')

        # as_rgb_tuple
        self.assertIsInstance(Color.RED.as_rgb_tuple(), tuple)

        # from_hex
        self.assertEqual(Color.from_hex('#ffffff'), Color.from_hex("#FFFFFF"))
        self.assertEqual(Color.from_hex('000000'), Color.BLACK.as_rgb_tuple())
        self.assertEqual(Color.from_hex('ff0000'), Color.RED.as_rgb_tuple())
        self.assertEqual(Color.from_hex('00FF00'), Color.GREEN.as_rgb_tuple())
        self.assertEqual(Color.from_hex('#0000fF'), Color.BLUE.as_rgb_tuple())

        # theme
        self.assertFalse(hasattr(Color, '_THEME'))
        self.assertEqual(Color.THEME.as_rgb_tuple(),
                         Color.WHITE.as_rgb_tuple())

        Color.set_theme('#fafafa')
        self.assertTrue(hasattr(Color, '_THEME'))
        self.assertEqual(Color.THEME.as_rgb_tuple(), Color.from_hex('#fafafa'))

        Color.set_theme('#aaaaaa')
        self.assertEqual(Color.THEME.as_rgb_tuple(), Color.from_hex('#aaaaaa'))

        Color.set_theme('#FFFF0000')
        self.assertEqual(Color.THEME.as_rgb_tuple(), (255, 0, 0))

    def test_abstract_led(self):
        from ovos_plugin_manager.hardware.led import AbstractLed
        # TODO

    def test_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import LedAnimation
        # TODO

    def test_breathe_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            BreatheLedAnimation
        # TODO

    def test_chase_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            ChaseLedAnimation
        # TODO

    def test_fill_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import FillLedAnimation
        # TODO

    def test_refill_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            RefillLedAnimation
        # TODO

    def test_bounce_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            BounceLedAnimation
        # TODO

    def test_Blink_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            BlinkLedAnimation
        # TODO

    def test_alternating_led_animation(self):
        from ovos_plugin_manager.hardware.led.animations import \
            AlternatingLedAnimation
        # TODO

    def test_animations(self):
        from ovos_plugin_manager.hardware.led.animations import animations, \
            LedAnimation
        for key, val in animations.items():
            self.assertIsInstance(key, str)
            self.assertTrue(issubclass(val, LedAnimation))


class TestFan(unittest.TestCase):
    from ovos_plugin_manager.hardware.fan import AbstractFan
    # TODO


class TestSwitches(unittest.TestCase):
    from ovos_plugin_manager.hardware.switches import AbstractSwitches
    # TODO
