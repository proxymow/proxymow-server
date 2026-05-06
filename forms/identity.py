from forms.morphable import Morphable
from setting import TextSetting, IntSetting, EnumerationSetting


class Identity(Morphable):
    '''
        represents a mower identity form
    '''
    ip = TextSetting('IP Address',
                     'IP Address on network',
                     None,
                     '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
                     'must be in 1.2.3.4 format'
                     )
    port = IntSetting('Port', 'Network Port', None, 0, 65565, 1)
    type = EnumerationSetting(
        'Type', 'Type of Mower', ['virtual', 'hybrid-udp', 'physical-udp', 'hybrid-ble', 'physical-ble'], {})

    def __init__(self):
        self.ip = '0.0.0.0'
        self.port = 5005
        self.type = 'virtual'
