from abc import abstractmethod
from threading import Event
from time import time, sleep
from typing import Optional

from ovos_plugin_manager.hardware.led import AbstractLed, Color


class LedAnimation:
    def __init__(self, leds: AbstractLed, **kwargs):
        self.leds = leds

    @abstractmethod
    def start(self, timeout: Optional[int] = None):
        """
        Start the animation.
        :param timeout: Optional timeout in seconds after which animation stops
        """

    @abstractmethod
    def stop(self):
        """
        Stop the animation and reset LEDs to black.
        """
        # TODO: Get state before animation and restore it here


class BreatheLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, color: Color):
        LedAnimation.__init__(self, leds)
        self.color_tuple = color.as_rgb_tuple()
        self.step = 0.05
        self.step_delay = 0.05
        self.stopping = Event()

    def start(self, timeout=None):
        self.stopping.clear()
        end_time = time() + timeout if timeout else None
        brightness = 1
        step = -1 * self.step
        while not self.stopping.is_set():
            if brightness >= 1:  # Going Down
                step = -1 * self.step
            elif brightness <= 0:
                step = self.step

            brightness += step
            self.leds.fill(tuple(brightness * part for part in self.color_tuple))
            sleep(self.step_delay)
            if end_time and time() > end_time:
                self.stopping.set()

    def stop(self):
        self.stopping.set()
        # TODO: Get LED state at start and restore it here
        self.leds.fill(Color.BLACK)


class ChaseLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, foreground_color: Color,
                 background_color: Color = Color.BLACK):
        LedAnimation.__init__(self, leds)
        self.foreground_color_tuple: tuple = foreground_color.as_rgb_tuple()
        self.background_color_tuple: tuple = background_color.as_rgb_tuple()
        self.step = 0.05
        self.step_delay = 0.1
        self.stopping = Event()

    def start(self, timeout=None):
        self.stopping.clear()
        end_time = time() + timeout if timeout else None

        self.leds.fill(self.background_color_tuple)
        while not self.stopping.is_set():
            for led in range(0, self.leds.num_leds):
                self.leds.set_led(led, self.foreground_color_tuple)
                sleep(self.step_delay)
                self.leds.set_led(led, self.background_color_tuple)
            if end_time and time() > end_time:
                self.stopping.set()

    def stop(self):
        self.stopping.set()


class FillLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, fill_color: Color,
                 reverse: bool = False):
        LedAnimation.__init__(self, leds)
        self.fill_color_tuple = fill_color.as_rgb_tuple()
        self.reverse = reverse
        self.step_delay = 0.05

    def start(self, timeout=None):
        leds = list(range(0, self.leds.num_leds))
        if self.reverse:
            leds.reverse()
        for led in leds:
            self.leds.set_led(led, self.fill_color_tuple)
            sleep(self.step_delay)

    def stop(self):
        pass


class RefillLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, fill_color: Color,
                 reverse: bool = False):
        LedAnimation.__init__(self, leds)
        self.stopping = Event()
        self.fill_color = fill_color
        self.fill_animation = FillLedAnimation(leds, fill_color, reverse)

    def start(self, timeout=None):
        self.stopping.clear()
        end_time = time() + timeout if timeout else None

        while not self.stopping.is_set():
            self.fill_animation.start()
            self.fill_animation.fill_color_tuple = Color.BLACK.as_rgb_tuple()
            self.fill_animation.start()
            self.fill_animation.fill_color_tuple = self.fill_color.as_rgb_tuple()
            if end_time and time() > end_time:
                self.stopping.set()

    def stop(self):
        self.stopping.set()


class BounceLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, fill_color: Color,
                 reverse: bool = False):
        LedAnimation.__init__(self, leds)
        self.stopping = Event()
        self.fill_color = fill_color
        self.fill_animation = FillLedAnimation(leds, fill_color, reverse)

    def start(self, timeout=None):
        self.stopping.clear()
        end_time = time() + timeout if timeout else None

        while not self.stopping.is_set():
            self.fill_animation.start()
            self.fill_animation.reverse = not self.fill_animation.reverse
            self.fill_animation.fill_color_tuple = Color.BLACK.as_rgb_tuple()
            self.fill_animation.start()
            self.fill_animation.reverse = not self.fill_animation.reverse
            self.fill_animation.fill_color_tuple = self.fill_color.as_rgb_tuple()
            if end_time and time() > end_time:
                self.stopping.set()

    def stop(self):
        self.stopping.set()

animations = {
    'breathe': BreatheLedAnimation,
    'chase': ChaseLedAnimation,
    'fill': FillLedAnimation,
    'refill': RefillLedAnimation,
    'bounce': BounceLedAnimation
}
