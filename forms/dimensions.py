from forms.morphable import Morphable
from setting import FloatSetting


class Dimensions(Morphable):
    '''
        represents mower dimensions form
    '''
    target_width_m = FloatSetting(
        'Target Width', 'Width of the Target', 'm', 0.05, 0.5, 0.005)
    target_length_m = FloatSetting(
        'Target Height', 'Length of the Target', 'm', 0.05, 0.5, 0.005)
    target_radius_m = FloatSetting(
        'Target Radius', 'Radius of the Target', 'm', 0.01, 0.5, 0.005)
    target_offset_pc = FloatSetting('Target Offset', 'Target Y Offset', '%')
    cutter1_dia_m = FloatSetting(
        'Cutter 1 Diameter', 'Cutter 1 Diameter', 'm', 0.0, 0.3, 0.005)
    cutter2_dia_m = FloatSetting(
        'Cutter 2 Diameter', 'Cutter 2 Diameter', 'm', 0.0, 0.3, 0.005)
    body_width_m = FloatSetting(
        'Body Width', 'Width of the Body', 'm', 0.05, 1.0, 0.01)
    body_length_m = FloatSetting(
        'Body Length', 'Length of the Body', 'm', 0.1, 1.0, 0.01)

    def __init__(self):
        self.target_width_m = 0.2
        self.target_length_m = 0.3
        self.target_radius_m = 0.020
        self.target_offset_pc = 0
        self.cutter1_dia_m = 0.2
        self.cutter2_dia_m = 0.2
        self.body_width_m = 0.25
        self.body_length_m = 0.4
