from forms.morphable import Morphable
from setting import TextSetting


class Hotspot(Morphable):
    '''
        represents a hotspot

    '''
    name = TextSetting('Hotspot', 'name of the preferred hotspot')

    def __init__(self):
        self.name = 'Proxymow-0000x'
