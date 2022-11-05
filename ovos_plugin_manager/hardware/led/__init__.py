# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from abc import abstractmethod
from enum import Enum
from typing import Union


class Color(Enum):
    """
    Enum class for colors. For theme support, call Color.set_theme() with a
    valid hex value.
    """
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)

    YELLOW = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    CYAN = (0, 255, 255)

    BURNT_ORANGE = (173, 64, 0)

    MYCROFT_BLUE = (34, 167, 240)
    NEON_ORANGE = (255, 134, 0)
    OVOS_RED = (255, 26, 26)

    THEME = ()

    def as_rgb_tuple(self) -> tuple:
        """
        Get an RGB tuple representation of the color.
        """
        if self.name == Color.THEME.name:
            if not hasattr(self, '_THEME'):
                return Color.WHITE.as_rgb_tuple()
            return self._THEME
        assert isinstance(self.value, tuple)
        return self.value

    @staticmethod
    def from_hex(hex_code: str) -> tuple:
        """
        Get a color RGB tuple from a hex code
        @param hex_code: RGB hex code, optionally starting with '#'
        @return: tuple RGB values
        """
        hex_code = hex_code.lstrip('#').strip()
        if len(hex_code) != 6:
            raise ValueError(f"Expected 6-character hex code, got: {hex_code}")
        return tuple(int(hex_code[i:i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def from_name(cls, color: str):
        """
        Get a Color object by name.
        :param color: string color corresponding on a name in the Color enum
        :returns: Color enum object for the requested string color
        """
        for c in cls:
            if c.name.lower() == color.lower():
                return c
        raise ValueError(f'{color} is not a valid Color')

    @classmethod
    def set_theme(cls, color: str):
        try:
            cls._THEME = Color.from_hex(color)
        except ValueError:
            cls._THEME = Color.WHITE.as_rgb_tuple()


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
    def fill(self, color: Union[Color, tuple]):
        """
        Set all LEDs to a particular color.
        :param color: RGB color value as Color or tuple of ints
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
