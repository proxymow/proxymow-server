from forms.morphable import Morphable
from setting import FloatSetting, IntSetting


class Motion(Morphable):
    '''
    represents a mower motion form

    axle_track_m: float = 0.25              # motion 1
    wheel_dia_m: float = 0.12               # motion 3
    motor_full_speed_rpm: float = 30        # motion 4
    set_rotation_speed_percent: int = 50    # motion 5
    set_drive_speed_percent: int = 50       # motion 6

    '''
    axle_track_m = FloatSetting(
        'Axle Track', 'Distance between wheels', 'm', 0.05, 0.5, 0.005)
    wheel_dia_m = FloatSetting(
        'Wheel Diameter', 'Wheel Diameter', 'm', 0.05, 0.25, 0.005)
    motor_full_speed_rpm = FloatSetting(
        'Motor Speed', 'Motor Speed', 'rpm', 10, 600, 5)
    set_rotation_speed_percent = IntSetting(
        'Set Rotation Speed', 'Initial turning rotation speed', '%', 0, 100, 1)
    set_drive_speed_percent = IntSetting(
        'Set Drive Speed', 'Initial driving speed', '%', 0, 100, 1)

    def __init__(self):
        self.axle_track_m = 0.28
        self.wheel_dia_m = 0.15
        self.motor_full_speed_rpm = 30
        self.set_rotation_speed_percent = 80
        self.set_drive_speed_percent = 60
