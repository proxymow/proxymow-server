from forms.morphable import Morphable
from setting import TextSetting, EnumerationSetting


class Pairing(Morphable):
    '''
        represents a pairing between lawn and mower => navigation strategy & mowing pattern

        name: str
        description: str
        profile: Dropdown
        mower: Dropdown
        strategy: Dropdown
        pattern: Dropdown

    '''

    pk_att_name = 'name'
    wildcard_opts = {'*': '*'}
    name = TextSetting('Pairing Name', 'Name of the pairing',
                       None, '^.{6,}$', 'must have at least 6 characters')
    description = TextSetting('Pairing Description', 'Pairing description')
    profile = EnumerationSetting(
        'Profile', 'The selected profile', 'profiles', wildcard_opts)
    mower = EnumerationSetting(
        'Mower', 'The selected mower', 'mowers', wildcard_opts)
    strategy = EnumerationSetting(
        'Strategy', 'The best strategy', 'strategies', {None: "None"})
    pattern = EnumerationSetting(
        'Pattern', 'The mowing pattern', 'patterns', {None: "None"})

    def __init__(self, name=''):
        self.name = name
        self.description = ''
        self.profile = None
        self.mower = None
        self.strategy = None
        self.pattern = 'Fence'
