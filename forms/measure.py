from forms.morphable import Morphable
from setting import TextSetting, FloatSetting, IntSetting


class Scaled(Morphable):
    '''
        represents a scaled scoring measure
    '''
    pk_att_name = 'name'

    name = TextSetting('Name', 'Name of the measure', None)
    lower = FloatSetting(
        'Lower Range', 'The lower range', None, rmin=0, rmax=1.0, step=0.01)
    scale = FloatSetting('Scale Factor', 'The scale factor',
                         None, rmin=0, rmax=2.0, step=0.01, incl_slider=False)
    upper = FloatSetting(
        'Upper Range', 'The upper range', None, rmin=0, rmax=1.0, step=0.01)
    maxscore = IntSetting('Maximum Score', 'The maximum score', None)


class Setpoint(Morphable):
    '''
        represents a setpoint scoring measure
    '''
    pk_att_name = 'name'

    name = TextSetting('Name', 'Name of the measure', None)
    lower = FloatSetting(
        'Lower Range', 'The lower range', None, rmin=0, rmax=1.0, step=0.01)
    setpoint = FloatSetting('Setpoint', 'The target value',
                            None, rmin=0, rmax=1.0, step=0.01, incl_slider=False)
    upper = FloatSetting(
        'Upper Range', 'The upper range', None, rmin=0, rmax=1.0, step=0.01)
    maxscore = IntSetting('Maximum Score', 'The maximum score', None)
