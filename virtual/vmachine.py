import threading

import random


class Pin():

    OUT = 1

    def __init__(self, _arg1, _arg2):
        pass

    def value(self, arg1):
        self.state = arg1


class PWM_Helper:
    def start(self, arg1):
        pass

    def freq(self, arg1):
        pass

    def duty(self, arg1):
        pass


class ADC_Helper:
    def read(self):
        return random.randrange(1024)


def PWM(_):
    """Dummy"""
    pwm_helper = PWM_Helper()
    return pwm_helper


def ADC(_):
    """Dummy"""

    adc_helper = ADC_Helper()
    return adc_helper


class Timer():

    """Dummy"""

    def __init__(self, arg1):
        pass

    def init(self, period, _mode, callback, args=None):
        timer = threading.Timer(period / 1000, callback, args)
        timer.start()
