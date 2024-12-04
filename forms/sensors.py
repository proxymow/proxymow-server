from forms.morphable import Morphable
from setting import ExpressionSetting


class Sensors(Morphable):
    '''
        represents a mower sensors form
    '''

    name_list = ExpressionSetting(
        'Names', 'Comma-separated list of sensor names', char_width=48)
    factor_list = ExpressionSetting(
        'Scale Factors', 'Comma-separated list of sensor scale factors', char_width=48)

    def __init__(self):
        self.name_list = ''
        self.factor_list = ''
