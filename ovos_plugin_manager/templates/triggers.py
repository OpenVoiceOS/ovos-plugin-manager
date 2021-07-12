import time


class LocalTrigger:
    def __init__(self, name, time_between_checks=1):
        self.name = name
        self.last_check = time.time()
        self.time_between_checks = time_between_checks
        self.bus = None

    def bind(self, bus):
        self.bus = bus

    @property
    def data(self):
        return {"name": self.name,
                "last_check": self.last_check,
                "time_between_checks": self.time_between_checks}

    def initialize(self):
        """ perform any initialization actions """
        pass

    def evaluate(self):
        """ evaluate trigger, return True or False"""
        return False

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass
