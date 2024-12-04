from forms.morphable import Morphable


class Point(Morphable):
    '''
        Represents a cartesian indexed percentage point
    '''
    pk_att_name = 'index'

    def __init__(self, i=-1, x=-1, y=-1):
        '''
            Constructor
        '''
        self.index = i
        self.x = x
        self.y = y

    @property
    def ncy(self):
        return 100 - self.y  # non-cartesian

    def __repr__(self):
        return 'index:{0} ({1}, {2})'.format(self.index, self.x, self.y)

    def inc_index(self):
        self.index += 1
        return self
