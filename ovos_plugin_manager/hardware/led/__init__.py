"""
DEPRECATED: Use ovos_hardware_helpers.led instead.

This module maintains backwards compatibility with the old Color enum while
re-exporting AbstractLed from ovos-hardware-helpers. New code should use
ovos_hardware_helpers.led and ovos_color_parser.models.sRGBAColor.
"""
from enum import Enum
from typing import Union
from ovos_utils.log import log_deprecation
from ovos_plugin_manager.version import VERSION_MAJOR

# Log deprecation on import
_deprecation_version = f"{VERSION_MAJOR + 1}.0"
log_deprecation("ovos_plugin_manager.hardware.led is deprecated, use ovos_hardware_helpers.led instead",
                func_name="led module",
                func_module="ovos_plugin_manager.hardware.led",
                deprecation_version=_deprecation_version)

# Keep the legacy Color enum for backwards compatibility
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
        hex_code = hex_code.lstrip('#').strip().lower()
        if hex_code.startswith("ff") and len(hex_code) == 8:
            hex_code = hex_code[2:]
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


__all__ = ["AbstractLed", "Color"]


def __getattr__(name: str):
    """Lazy import to make ovos-hardware-helpers an optional dependency."""
    if name == "AbstractLed":
        try:
            from ovos_hardware_helpers.led import AbstractLed
            return AbstractLed
        except ModuleNotFoundError as e:
            raise ImportError(
                f"ovos-hardware-helpers is not installed. "
                f"Install it with: pip install ovos-hardware-helpers"
            ) from e
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
