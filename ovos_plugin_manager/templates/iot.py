import enum
import itertools
import random
import time
from threading import Thread
from time import sleep

from ovos_config import Configuration
from ovos_utils import camel_case_split
from ovos_utils.colors import Color
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from ovos_utils.messagebus import get_mycroft_bus

from ovos_plugin_manager.utils.config import get_plugin_config


class IOTDeviceType(str, enum.Enum):
    """ recognized device types handled by commonIOT"""
    SENSOR = "sensor"
    PLUG = "plug"
    SWITCH = "switch"
    BULB = "bulb"
    RGB_BULB = "bulbRGB"
    RGBW_BULB = "bulbRGBW"
    TV = "tv"
    RADIO = "radio"
    HEATER = "heater"
    AC = "ac"
    CAMERA = "camera"
    MEDIA_PLAYER = "media_player"
    VACUUM = "vacuum"


class IOTCapabilties(enum.Enum):
    """ actions recognized by commonIOT and exposed by voice intents """
    REPORT_STATUS = enum.auto()
    TURN_ON = enum.auto()
    TURN_OFF = enum.auto()
    BLINK_LIGHT = enum.auto()
    BEACON_LIGHT = enum.auto()
    REPORT_COLOR = enum.auto()
    CHANGE_COLOR = enum.auto()
    REPORT_BRIGHTNESS = enum.auto()
    CHANGE_BRIGHTNESS = enum.auto()
    GET_PICTURE = enum.auto()
    PAUSE_PLAYBACK = enum.auto()
    RESUME_PLAYBACK = enum.auto()
    STOP_PLAYBACK = enum.auto()
    NEXT_PLAYBACK = enum.auto()
    PREV_PLAYBACK = enum.auto()


class IOTScannerPlugin:
    """ this class is loaded by CommonIOT and yields IOTDevices"""
    def __init__(self, bus=None, name="", config=None):
        self.config_core = Configuration()
        name = name or camel_case_split(self.__class__.__name__).replace(" ", "-").lower()
        self.config = config or get_plugin_config(self.config_core, "iot", name)
        self.bus = bus or get_mycroft_bus()
        self.log = LOG
        self.name = name

    def scan(self):
        raise NotImplemented("scan method must be implemented by subclasses")

    def get_device(self, ip):
        for device in self.scan():
            if device.host == ip:
                return device
        return None


class IOTAbstractDevice:
    capabilities = []

    def __init__(self, device_id, host=None, name="abstract_device",
                 area=None, device_type=IOTDeviceType.SENSOR,
                 raw_data=None):
        self._device_type = device_type
        self._device_id = device_id
        self._name = name or self.__class__.__name__
        self._host = host
        self._area = area
        self._raw = raw_data or {
            "name": name, "host": host,
            "area": area, "device_id": device_id}
        self.mode = ""
        self._timer = None

    @property
    def as_dict(self):
        return {
            "host": self.host,
            "device_id": self.device_id,
            "name": self.name,
            "area": self.device_area,
            "device_type": self.device_type,
            "state": self.is_on,
            "raw": self.raw_data
        }

    @property
    def device_id(self):
        return self._device_id

    @property
    def device_type(self):
        return self._device_type

    @property
    def host(self):
        return self._host

    @property
    def name(self):
        return self._name

    @property
    def raw_data(self):
        return self._raw

    @property
    def is_online(self):
        return True

    @property
    def is_on(self):
        return True

    @property
    def is_off(self):
        return not self.is_on

    @property
    def device_display_model(self):
        # for usage in GUI, TODO document format
        return {}

    @property
    def device_area(self):
        # TODO document format
        return self._area

    def __repr__(self):
        return self.name + ":" + self.host


class Sensor(IOTAbstractDevice):
    capabilities = [
        IOTCapabilties.REPORT_STATUS
    ]

    def __init__(self, device_id, host=None, name="generic_sensor",
                 area=None, device_type=IOTDeviceType.SENSOR, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)


class Plug(Sensor):
    capabilities = Sensor.capabilities + [
        IOTCapabilties.TURN_ON,
        IOTCapabilties.TURN_OFF
    ]

    def __init__(self, device_id, host=None, name="generic_plug",
                 area=None, device_type=IOTDeviceType.PLUG, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    def reset(self):
        self.mode = ""
        self._timer = None
        self.turn_on()

    # status change
    def turn_on(self):
        pass

    def turn_off(self):
        raise NotImplementedError

    def toggle(self):
        if self.is_off:
            self.turn_on()
        else:
            self.turn_off()

    def __repr__(self):
        return self.name + ":" + self.host


class Switch(Plug):
    def __init__(self, device_id, host=None, name="generic_switch",
                 area=None, device_type=IOTDeviceType.SWITCH, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)


class MediaPlayer(Plug):
    capabilities = Plug.capabilities + [
        PAUSE_PLAYBACK,
        RESUME_PLAYBACK,
        STOP_PLAYBACK,
        NEXT_PLAYBACK,
        PREV_PLAYBACK
    ]

    def __init__(self, device_id, host=None, name="generic_media_player",
                 area=None, device_type=IOTDeviceType.MEDIA_PLAYER, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    def resume(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def pause(self):
        raise NotImplemented

    def play_next(self):
        raise NotImplemented

    def play_prev(self):
        raise NotImplemented


class Radio(MediaPlayer):
    def __init__(self, device_id, host=None, name="generic_radio",
                 area=None, device_type=IOTDeviceType.RADIO, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    # TODO - basic radion actions, change_station etc
    def resume(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def pause(self):
        raise NotImplemented

    def play_next(self):
        raise NotImplemented

    def play_prev(self):
        raise NotImplemented


class TV(MediaPlayer):
    def __init__(self, device_id, host=None, name="generic_tv",
                 area=None, device_type=IOTDeviceType.TV, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    # TODO - basic tv actions, change_channel etc
    def resume(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def pause(self):
        raise NotImplemented

    def play_next(self):
        raise NotImplemented

    def play_prev(self):
        raise NotImplemented


class Heater(Plug):
    def __init__(self, device_id, host=None, name="generic_heater",
                 area=None, device_type=IOTDeviceType.HEATERT, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    # only has on/off for now
    # TODO - get temperature


class AirConditioner(Plug):
    def __init__(self, device_id, host=None, name="generic_ac",
                 area=None, device_type=IOTDeviceType.AC, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    # only has on/off for now
    # TODO - get temperature


class Vacuum(Plug):
    def __init__(self, device_id, host=None, name="generic_vacuum",
                 area=None, device_type=IOTDeviceType.VACUUM, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    # only has on/off for now
    # TODO - vacuum stuff


class Bulb(Plug):
    capabilities = Plug.capabilities + [
        IOTCapabilties.REPORT_BRIGHTNESS,
        IOTCapabilties.CHANGE_BRIGHTNESS,
        IOTCapabilties.BLINK_LIGHT,
        IOTCapabilties.BEACON_LIGHT
    ]

    def __init__(self, device_id, host=None, name="generic_bulb",
                 area=None, device_type=IOTDeviceType.BULB, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    def change_color(self, color="white"):
        if isinstance(color, Color):
            if color.rgb255 == (0, 0, 0):
                self.turn_off()
            else:
                if self.is_off:
                    self.turn_on()
                if Color.from_name("white") != color:
                    print("ERROR: bulb does not support color change")
        else:
            color = Color.from_name(color)
            self.change_color(color)

    @property
    def color(self):
        if self.is_off:
            return Color.from_name("black")
        return Color.from_name("white")

    @property
    def brightness(self):
        """
        Return current brightness 0-100%
        """
        return self.brightness_255 * 100 / 255

    @property
    def brightness_255(self):
        """
        Return current brightness 0-255
        """
        return 255

    def change_brightness(self, value, percent=True):
        pass

    def set_low_brightness(self):
        self.change_brightness(25)

    def set_high_brightness(self):
        self.change_brightness(100)

    @property
    def as_dict(self):
        return {
            "host": self.host,
            "name": self.name,
            "brightness": self.brightness_255,
            "color": self.color.as_dict,
            "device_type": "bulb",
            "state": self.is_on,
            "raw": self.raw_data
        }

    def reset(self):
        self.mode = ""
        self._timer = None
        if self.is_off:
            self.turn_on()
        self.set_high_brightness()

    def beacon_slow(self, speed=0.9):

        assert 0 <= speed <= 1

        if self.is_off:
            self.turn_on()
        self.mode = "beacon"

        def cycle():
            while self.mode == "beacon":
                i = 5
                while i < 100:
                    i += 5
                    self.change_brightness(i)
                    sleep(1 - speed)

                while i > 5:
                    i -= 5
                    self.change_brightness(i)
                    sleep(1 - speed)

        self._timer = Thread(target=cycle)
        self._timer.setDaemon(True)
        self._timer.start()

    def beacon(self, speed=0.7):

        assert 0 <= speed <= 1

        if self.is_off:
            self.turn_on()
        self.mode = "beacon"

        def cycle():
            while self.mode == "beacon":
                self.change_brightness(100)
                sleep(1 - speed)
                self.change_brightness(50)
                sleep(1 - speed)
                self.change_brightness(1)
                sleep(1 - speed)
                self.change_brightness(50)

        self._timer = Thread(target=cycle)
        self._timer.setDaemon(True)
        self._timer.start()

    def blink(self, speed=0):

        assert 0 <= speed <= 1

        self.mode = "blink"
        if self.is_off:
            self.turn_on()

        def cycle():
            while self.mode == "blink":
                self.turn_off()
                sleep(1 - speed)
                self.turn_on()
                sleep(1 - speed)

        self._timer = Thread(target=cycle)
        self._timer.setDaemon(True)
        self._timer.start()


class RGBBulb(Bulb):
    capabilities = Bulb.capabilities + [
        IOTCapabilties.REPORT_COLOR,
        IOTCapabilties.CHANGE_COLOR
    ]

    def __init__(self, device_id, host=None, name="generic_rgb_bulb",
                 area=None, device_type=IOTDeviceType.RGB_BULB, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    def reset(self):
        super().reset()
        self.change_color("white")

    @property
    def as_dict(self):
        return {
            "host": self.host,
            "name": self.name,
            "device_type": "rgb bulb",
            "brightness": self.brightness_255,
            "state": self.is_on,
            "raw": self.raw_data
        }

    # color operations
    def change_color_hex(self, hexcolor):
        self.change_color(Color.from_hex(hexcolor))

    def change_color_hsv(self, h, s, v):
        self.change_color(Color.from_hsv(h, s, v))

    def change_color_rgb(self, r, g, b):
        self.change_color(Color.from_rgb(r, g, b))

    def cross_fade(self, color1, color2, steps=100):
        if isinstance(color1, Color):
            color1 = color1.rgb255
        if isinstance(color2, Color):
            color2 = color2.rgb255
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        for i in range(1, steps + 1):
            r = r1 - int(i * float(r1 - r2) // steps)
            g = g1 - int(i * float(g1 - g2) // steps)
            b = b1 - int(i * float(b1 - b2) // steps)

            self.change_color_rgb(r, g, b)

    def color_cycle(self, color_time=2, cross_fade=False):
        self.mode = "color_cycle"
        # print("Light mode: {mode}".format(mode=self.mode))
        if self.is_off:
            self.turn_on()

        def cycle_color():

            class Red(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(255, 0, 0)

            class Orange(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(255, 125, 0)

            class Yellow(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(255, 255, 0)

            class SpringGreen(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(125, 255, 0)

            class Green(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(0, 255, 0)

            class Turquoise(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(0, 255, 125)

            class Cyan(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(0, 255, 255)

            class Ocean(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(0, 125, 255)

            class Blue(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(0, 0, 255)

            class Violet(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(125, 0, 255)

            class Magenta(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(255, 0, 255)

            class Raspberry(Color):
                def __new__(cls, *args, **kwargs):
                    return Color.from_rgb(255, 0, 125)

            colorwheel = [Red(), Orange(), Yellow(), SpringGreen(),
                          Green(), Turquoise(), Cyan(), Ocean(),
                          Blue(), Violet(), Magenta(), Raspberry()]

            # use cycle() to treat the list in a circular fashion
            colorpool = itertools.cycle(colorwheel)

            # get the first color before the loop
            color = next(colorpool)

            while self.mode == "color_cycle":
                # set to color and wait
                self.change_color(color)
                time.sleep(color_time)

                # fade from color to next color
                next_color = next(colorpool)
                if cross_fade:
                    self.cross_fade(color, next_color)

                # ready for next loop
                color = next_color

        self._timer = Thread(target=cycle_color)
        self._timer.setDaemon(True)
        self._timer.start()

    def random_color_cycle(self, color_time=2):
        self.mode = "random_color_cycle"
        if self.is_off:
            self.turn_on()

        def cycle_color():

            while self.mode == "random_color_cycle":
                # set to color and wait
                self.random_color()
                time.sleep(color_time)

        self._timer = Thread(target=cycle_color)
        self._timer.setDaemon(True)
        self._timer.start()

    def random_color(self):
        color = Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.change_color(color)


class RGBWBulb(RGBBulb):
    def __init__(self, device_id, host=None, name="generic_rgbw_bulb",
                 area=None, device_type=IOTDeviceType.RGBW_BULB, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    @property
    def as_dict(self):
        return {
            "host": self.host,
            "name": self.name,
            "device_type": "rgbw bulb",
            "brightness": self.brightness_255,
            "color": self.color.as_dict,
            "state": self.is_on,
            "raw": self.raw_data
        }


class Camera(Sensor):
    capabilities = Sensor.capabilities + [
        IOTCapabilties.GET_PICTURE
    ]

    def __init__(self, device_id, host=None, name="generic_camera",
                 area=None, device_type=IOTDeviceType.CAMERA, raw_data=None):
        super().__init__(device_id, host, name, area, device_type, raw_data)

    def get_picture(self):
        return NotImplemented



