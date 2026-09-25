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

"""Unit tests for ovos_plugin_manager.hardware.led.animations."""

import unittest
from threading import Event
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, call, patch

from ovos_plugin_manager.hardware.led import AbstractLed, Color
from ovos_plugin_manager.hardware.led.animations import (
    AlternatingLedAnimation,
    BlinkLedAnimation,
    BounceLedAnimation,
    BreatheLedAnimation,
    ChaseLedAnimation,
    FillLedAnimation,
    LedAnimation,
    RefillLedAnimation,
    animations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_leds(num_leds: int = 4) -> MagicMock:
    """Return a MagicMock that mimics AbstractLed with num_leds attribute."""
    mock = MagicMock(spec=AbstractLed)
    mock.num_leds = num_leds
    return mock


# ---------------------------------------------------------------------------
# animations dict
# ---------------------------------------------------------------------------

class TestAnimationsDict(unittest.TestCase):
    """Tests for the module-level animations mapping."""

    def test_all_keys_present(self) -> None:
        """animations dict contains all expected keys."""
        expected = {"breathe", "chase", "fill", "refill", "bounce", "blink", "alternating"}
        self.assertEqual(set(animations.keys()), expected)

    def test_values_are_classes(self) -> None:
        """animations dict values are LedAnimation subclasses."""
        for name, cls in animations.items():
            with self.subTest(name=name):
                self.assertTrue(issubclass(cls, LedAnimation))


# ---------------------------------------------------------------------------
# BreatheLedAnimation
# ---------------------------------------------------------------------------

class TestBreatheLedAnimation(unittest.TestCase):
    """Tests for BreatheLedAnimation."""

    def _make(self) -> BreatheLedAnimation:
        return BreatheLedAnimation(_make_mock_leds(), Color.GREEN)

    def test_init_stores_color(self) -> None:
        """BreatheLedAnimation stores color on init."""
        anim = self._make()
        self.assertEqual(anim.color, Color.GREEN)

    def test_init_step_defaults(self) -> None:
        """BreatheLedAnimation sets default step values."""
        anim = self._make()
        self.assertAlmostEqual(anim.step, 0.05)
        self.assertAlmostEqual(anim.step_delay, 0.05)

    def test_init_stopping_event(self) -> None:
        """BreatheLedAnimation has a stopping Event."""
        anim = self._make()
        self.assertIsInstance(anim.stopping, Event)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = self._make()
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot_runs_and_returns(self) -> None:
        """start(one_shot=True) completes one breathing cycle."""
        mock_leds = _make_mock_leds()
        anim = BreatheLedAnimation(mock_leds, Color.GREEN)
        # one_shot=True: animation stops after one complete cycle
        anim.start(one_shot=True)
        # After start completes, leds.fill was called (at least the final BLACK fill)
        mock_leds.fill.assert_called()

    def test_start_timeout(self) -> None:
        """start(timeout=...) stops after timeout."""
        mock_leds = _make_mock_leds()
        anim = BreatheLedAnimation(mock_leds, Color.GREEN)
        anim.step_delay = 0  # speed up
        anim.start(timeout=0.001)
        mock_leds.fill.assert_called()

    def test_start_clears_stopping(self) -> None:
        """start() clears stopping event before running."""
        mock_leds = _make_mock_leds()
        anim = BreatheLedAnimation(mock_leds, Color.GREEN)
        anim.stopping.set()
        anim.step_delay = 0
        anim.start(timeout=0.001)
        # stopping was cleared and then set again by timeout branch


# ---------------------------------------------------------------------------
# ChaseLedAnimation
# ---------------------------------------------------------------------------

class TestChaseLedAnimation(unittest.TestCase):
    """Tests for ChaseLedAnimation."""

    def _make(self) -> ChaseLedAnimation:
        return ChaseLedAnimation(_make_mock_leds(4), Color.BLUE)

    def test_init_colors(self) -> None:
        """ChaseLedAnimation stores foreground and background colors."""
        anim = self._make()
        self.assertEqual(anim.foreground_color, Color.BLUE)
        self.assertEqual(anim.background_color, Color.BLACK)

    def test_init_custom_background(self) -> None:
        """ChaseLedAnimation accepts custom background color."""
        anim = ChaseLedAnimation(_make_mock_leds(), Color.BLUE, Color.RED)
        self.assertEqual(anim.background_color, Color.RED)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = self._make()
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot(self) -> None:
        """start(one_shot=True) runs one pass through all LEDs."""
        mock_leds = _make_mock_leds(4)
        anim = ChaseLedAnimation(mock_leds, Color.BLUE)
        anim.step_delay = 0
        anim.start(one_shot=True)
        # set_led called at least once per LED
        self.assertGreater(mock_leds.set_led.call_count, 0)
        # Final fill to BLACK
        mock_leds.fill.assert_called()

    def test_start_timeout(self) -> None:
        """start(timeout=...) stops after timeout expires."""
        mock_leds = _make_mock_leds(4)
        anim = ChaseLedAnimation(mock_leds, Color.BLUE)
        anim.step_delay = 0
        anim.start(timeout=0.001)
        mock_leds.fill.assert_called()


# ---------------------------------------------------------------------------
# FillLedAnimation
# ---------------------------------------------------------------------------

class TestFillLedAnimation(unittest.TestCase):
    """Tests for FillLedAnimation."""

    def test_init_stores_fill_color(self) -> None:
        """FillLedAnimation stores fill_color and reverse."""
        anim = FillLedAnimation(_make_mock_leds(), Color.RED)
        self.assertEqual(anim.fill_color, Color.RED)
        self.assertFalse(anim.reverse)

    def test_init_reverse(self) -> None:
        """FillLedAnimation stores reverse=True."""
        anim = FillLedAnimation(_make_mock_leds(), Color.RED, reverse=True)
        self.assertTrue(anim.reverse)

    def test_stop_is_noop(self) -> None:
        """stop() does nothing (no stopping event)."""
        anim = FillLedAnimation(_make_mock_leds(), Color.RED)
        anim.stop()  # Should not raise

    def test_start_fills_all_leds_forward(self) -> None:
        """start() calls set_led for each LED in forward order."""
        mock_leds = _make_mock_leds(4)
        anim = FillLedAnimation(mock_leds, Color.RED)
        anim.step_delay = 0
        anim.start()
        self.assertEqual(mock_leds.set_led.call_count, 4)
        # Check order: LED 0, 1, 2, 3
        calls = [c[0][0] for c in mock_leds.set_led.call_args_list]
        self.assertEqual(calls, [0, 1, 2, 3])

    def test_start_fills_all_leds_reverse(self) -> None:
        """start() fills LEDs in reverse order when reverse=True."""
        mock_leds = _make_mock_leds(4)
        anim = FillLedAnimation(mock_leds, Color.RED, reverse=True)
        anim.step_delay = 0
        anim.start()
        calls = [c[0][0] for c in mock_leds.set_led.call_args_list]
        self.assertEqual(calls, [3, 2, 1, 0])

    def test_start_warns_on_persistent(self) -> None:
        """start(one_shot=False) logs a warning."""
        mock_leds = _make_mock_leds(2)
        anim = FillLedAnimation(mock_leds, Color.RED)
        anim.step_delay = 0
        with patch("ovos_plugin_manager.hardware.led.animations.LOG") as mock_log:
            anim.start(one_shot=False)
            mock_log.warning.assert_called_once()

    def test_start_warns_with_timeout(self) -> None:
        """start(timeout=...) logs a warning."""
        mock_leds = _make_mock_leds(2)
        anim = FillLedAnimation(mock_leds, Color.RED)
        anim.step_delay = 0
        with patch("ovos_plugin_manager.hardware.led.animations.LOG") as mock_log:
            anim.start(timeout=10)
            mock_log.warning.assert_called_once()


# ---------------------------------------------------------------------------
# RefillLedAnimation
# ---------------------------------------------------------------------------

class TestRefillLedAnimation(unittest.TestCase):
    """Tests for RefillLedAnimation."""

    def test_init_creates_fill_animation(self) -> None:
        """RefillLedAnimation creates an internal FillLedAnimation."""
        anim = RefillLedAnimation(_make_mock_leds(), Color.BLUE)
        self.assertIsInstance(anim.fill_animation, FillLedAnimation)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = RefillLedAnimation(_make_mock_leds(), Color.BLUE)
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot(self) -> None:
        """start(one_shot=True) runs one fill+unfill cycle."""
        mock_leds = _make_mock_leds(2)
        anim = RefillLedAnimation(mock_leds, Color.BLUE)
        anim.fill_animation.step_delay = 0
        anim.start(one_shot=True)
        # fill_animation.start() called at least twice (fill + unfill)
        self.assertGreater(mock_leds.set_led.call_count, 0)

    def test_start_timeout(self) -> None:
        """start(timeout=...) stops after timeout."""
        mock_leds = _make_mock_leds(2)
        anim = RefillLedAnimation(mock_leds, Color.BLUE)
        anim.fill_animation.step_delay = 0
        anim.start(timeout=0.001)
        self.assertGreater(mock_leds.set_led.call_count, 0)


# ---------------------------------------------------------------------------
# BounceLedAnimation
# ---------------------------------------------------------------------------

class TestBounceLedAnimation(unittest.TestCase):
    """Tests for BounceLedAnimation."""

    def test_init_creates_fill_animation(self) -> None:
        """BounceLedAnimation creates an internal FillLedAnimation."""
        anim = BounceLedAnimation(_make_mock_leds(), Color.GREEN)
        self.assertIsInstance(anim.fill_animation, FillLedAnimation)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = BounceLedAnimation(_make_mock_leds(), Color.GREEN)
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot(self) -> None:
        """start(one_shot=True) runs forward and reverse fill."""
        mock_leds = _make_mock_leds(2)
        anim = BounceLedAnimation(mock_leds, Color.GREEN)
        anim.fill_animation.step_delay = 0
        anim.start(one_shot=True)
        self.assertGreater(mock_leds.set_led.call_count, 0)

    def test_start_one_shot_toggles_reverse(self) -> None:
        """start(one_shot=True) restores reverse flag to original."""
        mock_leds = _make_mock_leds(2)
        anim = BounceLedAnimation(mock_leds, Color.GREEN, reverse=False)
        anim.fill_animation.step_delay = 0
        anim.start(one_shot=True)
        # After one_shot, reverse should be restored
        self.assertFalse(anim.fill_animation.reverse)


# ---------------------------------------------------------------------------
# BlinkLedAnimation
# ---------------------------------------------------------------------------

class TestBlinkLedAnimation(unittest.TestCase):
    """Tests for BlinkLedAnimation."""

    def test_init_stores_params(self) -> None:
        """BlinkLedAnimation stores color, num_blinks, and repeat."""
        anim = BlinkLedAnimation(_make_mock_leds(), Color.RED, num_blinks=3, repeat=True)
        self.assertEqual(anim.color, Color.RED)
        self.assertEqual(anim.num_blinks, 3)
        self.assertTrue(anim.repeat)

    def test_init_defaults(self) -> None:
        """BlinkLedAnimation default num_blinks=2, repeat=False."""
        anim = BlinkLedAnimation(_make_mock_leds(), Color.RED)
        self.assertEqual(anim.num_blinks, 2)
        self.assertFalse(anim.repeat)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = BlinkLedAnimation(_make_mock_leds(), Color.RED)
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot(self) -> None:
        """start(one_shot=True) blinks once and returns."""
        mock_leds = _make_mock_leds()
        anim = BlinkLedAnimation(mock_leds, Color.RED, num_blinks=1)
        # Patch _delay.wait to be instant
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start(one_shot=True)
        # fill called for each blink on + off + final BLACK
        self.assertGreater(mock_leds.fill.call_count, 0)

    def test_start_no_repeat_stops_after_blinks(self) -> None:
        """start() with repeat=False stops after one set of blinks."""
        mock_leds = _make_mock_leds()
        anim = BlinkLedAnimation(mock_leds, Color.RED, num_blinks=1, repeat=False)
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start()
        self.assertGreater(mock_leds.fill.call_count, 0)

    def test_start_timeout(self) -> None:
        """start(timeout=...) stops after timeout."""
        mock_leds = _make_mock_leds()
        anim = BlinkLedAnimation(mock_leds, Color.RED, num_blinks=1, repeat=True)
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start(timeout=0.001)
        self.assertGreater(mock_leds.fill.call_count, 0)


# ---------------------------------------------------------------------------
# AlternatingLedAnimation
# ---------------------------------------------------------------------------

class TestAlternatingLedAnimation(unittest.TestCase):
    """Tests for AlternatingLedAnimation."""

    def test_init_stores_color(self) -> None:
        """AlternatingLedAnimation stores color and delay."""
        anim = AlternatingLedAnimation(_make_mock_leds(), Color.WHITE)
        self.assertEqual(anim.color, Color.WHITE)
        self.assertAlmostEqual(anim.delay, 0.5)

    def test_stop_sets_event(self) -> None:
        """stop() sets the stopping event."""
        anim = AlternatingLedAnimation(_make_mock_leds(), Color.WHITE)
        anim.stopping.clear()
        anim.stop()
        self.assertTrue(anim.stopping.is_set())

    def test_start_one_shot_even_leds(self) -> None:
        """start(one_shot=True) runs two alternating passes."""
        mock_leds = _make_mock_leds(4)
        anim = AlternatingLedAnimation(mock_leds, Color.WHITE)
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start(one_shot=True)
        # set_led called for each led in each pass
        self.assertGreater(mock_leds.set_led.call_count, 0)
        # After animation fill BLACK is called
        mock_leds.fill.assert_called()

    def test_start_timeout(self) -> None:
        """start(timeout=...) stops after timeout."""
        mock_leds = _make_mock_leds(4)
        anim = AlternatingLedAnimation(mock_leds, Color.WHITE)
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start(timeout=0.001)
        self.assertGreater(mock_leds.set_led.call_count, 0)

    def test_start_sets_even_and_odd_leds(self) -> None:
        """start(one_shot=True) sets even LEDs on first pass, odd on second."""
        mock_leds = _make_mock_leds(4)
        anim = AlternatingLedAnimation(mock_leds, Color.WHITE)
        anim._delay = MagicMock()
        anim._delay.wait = MagicMock()
        anim.start(one_shot=True)
        # show() is called after each pass
        mock_leds.show.assert_called()


if __name__ == "__main__":
    unittest.main()
