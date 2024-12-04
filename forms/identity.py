from forms.morphable import Morphable
from setting import TextSetting, IntSetting, EnumerationSetting


class Identity(Morphable):
    '''
    represents a mower identity form

    ip: str = '0.0.0.0'                     # identity 1
    port: int = 5005                        # identity 2
    '''
    ip = TextSetting('IP Address',
                     'IP Address on network',
                     None,
                     '^(?!0)(?!.*\\.$)((1?\\d?\\d|25[0-5]|2[0-4]\\d)(\\.|$)){4}$',
                     'must be in 1.2.3.4 format'
                     )
    port = IntSetting('Port', 'Network Port', None, 0, 65565, 1)
    type = EnumerationSetting(
        'Type', 'Type of Mower', ['virtual', 'hybrid', 'physical'], {})

    def __init__(self):
        self.ip = '0.0.0.0'
        self.port = 5005
        self.type = 'virtual'
