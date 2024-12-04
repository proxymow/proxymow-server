from forms.morphable import Morphable
from setting import FloatSetting


class Lawn(Morphable):
    '''
        represents a lawn
    '''

    width_m = FloatSetting('Lawn Width', 'Width of lawn', 'm', 1.0, 20.0, 0.1)
    length_m = FloatSetting(
        'Lawn Length', 'Length of lawn', 'm', 1.0, 20.0, 0.1)
    border_m = FloatSetting(
        'Lawn Border', 'Border around lawn creating arena', 'm', 0.0, 1.0, 0.01)

    def __init__(self):
        self.width_m = 4.0
        self.length_m = 4.0
        self.border_m = 0.1
