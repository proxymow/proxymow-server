from forms.morphable import Morphable
from setting import TextSetting


class Strategy(Morphable):
    '''
        represents a navigation strategy
    '''

    pk_att_name = 'name'
    name = TextSetting('Strategy Name', 'Name of the strategy', None,
                       '^.{6,}$', 'must have at least 6 characters', char_width=32)
    description = TextSetting('Strategy Description',
                              'Strategy description', char_width=48)

    def __init__(self, name='', description=''):
        self.name = name
        self.description = description
