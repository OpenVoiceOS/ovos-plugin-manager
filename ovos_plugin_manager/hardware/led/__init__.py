from abc import abstractmethod
from typing import Union

class AbstractLed:
    @property
    @abstractmethod
    def num_leds(self) -> int:
        """
        Return the logical number of addressable LEDs.
        """

    @property
    @abstractmethod
    def capabilities(self) -> dict:
        """
        Return a dict of capabilities this object supports
        """

    @abstractmethod
    def set_led(self, led_idx: int, color: tuple, immediate: bool = True):
        """
        Set a specific LED to a particular color.
        :param led_idx: index of LED to modify
        :param color: RGB color value as ints
        :param immediate: If true, update LED immediately, else wait for `show`
        """

    # TODO: get_led?

    @abstractmethod
    def fill(self, color: tuple):
        """
        Set all LEDs to a particular color.
        :param color: RGB color value as a tuple of ints
        """

    @abstractmethod
    def show(self):
        """
        Update LEDs to match values set in this class.
        """

    @abstractmethod
    def shutdown(self):
        """
        Perform any cleanup and turn off LEDs.
        """

    @staticmethod
    def scale_brightness(color_val: int, bright_val: float) -> float:
        """
        Scale an individual color value by a specified brightness.
        :param color_val: 0-255 R, G, or B value
        :param bright_val: 0.0-1.0 brightness scalar value
        :returns: Float modified color value to account for brightness
        """
        return min(255.0, color_val * bright_val)

    def get_capabilities(self) -> dict:
        """
        Backwards-compatible method to return `self.capabilities`
        """
        return self.capabilities
