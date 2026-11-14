from forms.morphable import Morphable
from setting import IntSetting, FloatSetting


class Dimensions(Morphable):
    '''
        represents mower dimensions form
    '''
    target_upper_base_m = FloatSetting(
        'Target Upper Base', 'Top width of the Target', 'm', 0.0, 1.0, 0.005)
    target_lower_base_m = FloatSetting(
        'Target Lower Base', 'Base width of the Target', 'm', 0.0, 1.0, 0.005)
    target_length_m = FloatSetting(
        'Target Height', 'Length of the Target', 'm', 0.0, 1.0, 0.005)
    target_radius_m = FloatSetting(
        'Target Radius', 'Radius of the Target', 'm', 0.0, 0.5, 0.005)
    target_rotation_ccw_deg = IntSetting(
        'Target Rotation', 'CCW Rotation of the Target', 'degrees', 0, 360, 1)
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
        self.target_lower_base_m = 0.212
        self.target_upper_base_m = 0.085
        self.target_length_m = 0.17
        self.target_radius_m = 0.020
        self.target_rotation_ccw_deg = 270
        self.target_offset_pc = 50
        self.cutter1_dia_m = 0.2
        self.cutter2_dia_m = 0.2
        self.body_width_m = 0.3
        self.body_length_m = 0.5

    def upgrade(self, data_dict):
        if data_dict is not None and 'target_lower_base_m' not in data_dict:
            '''
                version 2.2.0 xml configuration upgrade
                ---------------------------------------
                3-point target shapes => 4-point target shapes
                mower.dimensions.target_width_m has been deprecated
                    in favour of target_lower_base_m & target_upper_base_m
                legacy target_width_m has been substituted for target_lower_base_m
            '''
            self.target_lower_base_m = data_dict['target_width_m']
            msg_lines = ['! version 2.2.0 xml configuration upgrade',
                   '! 3-point target shapes => 4-point target shapes',
                   '! mower.dimensions.target_width_m has been deprecated',
                   '!   in favour of target_lower_base_m & target_upper_base_m',
                   '! legacy target_width_m has been substituted for target_lower_base_m']
            if self._logger:
                [self._logger.warning(line) for line in msg_lines]

