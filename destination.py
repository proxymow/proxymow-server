from enum import Enum, auto


class Attitude(Enum):
    DEFAULT = auto()
    FWD_DRIVE = auto()
    FWD_MOW = auto()
    REV_DRIVE = auto()
    REV_MOW = auto()


class Destination():
    '''
        Represents a target point and the attitude towards it
    '''

    def __init__(self, x, y, attitude=Attitude.DEFAULT):
        '''
            Constructor
        '''
        self.target_x = x
        self.target_y = y
        self.attitude = attitude

    def __repr__(self):
        return('({}, {}) {}'.format(self.target_x, self.target_y, self.attitude))