from setting import TextSetting
from forms.morphable import Morphable
from forms.identity import Identity
from forms.dimensions import Dimensions
from forms.motion import Motion
from forms.sensors import Sensors


class Mower(Morphable):
    '''
    represents a mower form
    '''

    _pk_att_name = 'name'
    name = TextSetting('Mower Name', 'Name of the mower',
                       None, '^.{6,}$', 'must have at least 6 characters')

    def __init__(self, name=''):
        self.name = name
        self.identity = Identity()
        self.dimensions = Dimensions()
        self.motion = Motion()
        self.sensors = Sensors()
