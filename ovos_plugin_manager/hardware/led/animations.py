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
from threading import Event
from time import time, sleep
from typing import Optional

from abstract_hardware_interface.led import AbstractLed, Color


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


class LoopFillLedAnimation(LedAnimation):
    def __init__(self, leds: AbstractLed, fill_color: Color,
                 reverse: bool = False):
        LedAnimation.__init__(self, leds)
        self.fill_color_tuple = fill_color.as_rgb_tuple()
        self.reverse = reverse
        self.step_delay = 0.02

    def start(self, timeout=None):
        leds = list(range(0, self.leds.num_leds))
        if self.reverse:
            leds.reverse()
        for led in leds:
            self.leds.set_led(led, self.fill_color_tuple)
            sleep(self.step_delay)

    def stop(self):
        pass


animations = {
    'breathe': BreatheLedAnimation,
    'chase': ChaseLedAnimation,
    'loop_fill': LoopFillLedAnimation
}
