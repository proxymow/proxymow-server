from forms.morphable import Morphable
from setting import TextSetting
from forms.lawn import Lawn
from forms.device import Device
from forms.connection import Connection
from forms.hotspot import Hotspot


class Profile(Morphable):
    '''
        represents a profile
    '''
    pk_att_name = 'name'
    name = TextSetting('Profile Name', 'Name of the profile',
                       None, '^.{6,}$', 'must have at least 6 characters')
    description = TextSetting('Profile Description', 'Profile description')

    def __init__(self, name='', description=''):
        self.name = name
        self.description = description
        self.lawn = Lawn()
        self.device = Device()
        self.connection = Connection()
        self.hotspot = Hotspot()
