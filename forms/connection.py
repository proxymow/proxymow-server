from forms.morphable import Morphable
from setting import IntSetting, TextSetting, PasswordSetting


class Connection(Morphable):
    '''
    represents a database connection form

    '''
    host = TextSetting('IP Address',
                     'IP Address of Database Server',
                     None,
                     '^(?!0)(?!.*\\.$)((1?\\d?\\d|25[0-5]|2[0-4]\\d)(\\.|$)){4}$',
                     'must be in 1.2.3.4 format'
                     )
    port = IntSetting('Port', 'Database Network Port', None, 0, 65565, 1)
    database = TextSetting('Database', 'database name')
    user = TextSetting('Username', 'username for db server')
    password = PasswordSetting('Password', 'password for db server')

    def __init__(self):
        self.host = '192.0.2.0'
        self.port = 3306
        self.database = 'proxymow'
        self.user = 'db_user'
        self.password = 'db_password'
