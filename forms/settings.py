import logging
from html_tool_pane import HtmlToolPane
from setting import *  # @UnusedWildImport
from forms.morphable import Morphable
import configurations
import constants


class Sibling():
    pass


class CoreSettings(Morphable):
    @classmethod
    def class_var_names(cls, sort=True):
        is_root = len(cls.__mro__) <= 4
        if is_root:
            # root class - preserve definition order
            cls_hier = cls.__dict__.keys()
        else:
            # child class with inherited members - use sort order
            cls_hier = dir(cls)

        namelist = [attribute for attribute in cls_hier
                    if not attribute.startswith('_') and
                    not callable(getattr(cls, attribute))
                    ]
        if sort:
            namelist.sort(key=lambda x: type(getattr(cls, x)).__name__)
        return namelist

    @classmethod
    def class_settings(cls, sort=True):
        stg_dict = {}
        for cv_name in cls.class_var_names(sort):
            cv_val = getattr(cls, cv_name)
            if isinstance(cv_val, BaseSetting):
                stg_dict[cv_name] = cv_val
        return stg_dict

    def get_settings_as_toolpane(self, tp_id, tp_class, sort=True):
        child = self.__class__
        tp_config = []
        for cv_name, cv_stg in child.class_settings(sort).items():
            # self._logger.debug('setting: {0} {1}'.format(cv_name, type(cv_stg)))
            tool = cv_stg.get_tool(cv_name, getattr(self, cv_name), True)
            if tool is not None:
                tp_config.append(tool)

        toolpane = HtmlToolPane(tp_id, tp_class, tp_config)
        return toolpane


class BaseSettings(CoreSettings):

    # class variable settings
    queue = HiddenSetting()
    client = HiddenSetting()
    annotate = BooleanSetting('Annotate', 'Annotate with capture time')
    display_colour = BooleanSetting('Display Colour', 'Colour display')
    undistort_strength = FloatSetting(
        'Undistort Strength', 'Strength of the distortion correction', '', 0.0, 5.0, 0.01)
    undistort_zoom = FloatSetting(
        'Undistort Zoom', 'Zoom Factor', '', 1.0, 4.0, 0.01)

    def __init__(self, child):
        self._debug = True
        self._logger = logging.getLogger('vision')
        # create property with setting type defaults
        for stg_name, stg in child.class_settings().items():
            setattr(self, stg_name, stg.default)

        # specify special defaults
        self.annotate = True
        self.undistort_zoom = 1.0

    def __contains__(self, key):
        return key in vars(self)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, newvalue):

        setattr(self, key, newvalue)

    def align_with_config(self, config):
        child = self.__class__
        for stg_name, stg in child.class_settings().items():
            if not isinstance(stg, HiddenSetting):
                db_key = 'optical.' + stg_name
                config_value = config[db_key]
                setattr(self, stg_name, config_value)

    def save_settings(self, config):
        child = self.__class__
        for stg_name, stg in child.class_settings().items():
            # skip system settings
            if stg.label is not None:
                db_key = 'optical.' + stg_name
                stg_value = getattr(self, stg_name)
                self._logger.debug(
                    'save_settings {0} = {1}'.format(db_key, stg_value))
                config[db_key] = stg_value

    def align_with_dict(self, qsp_dict):
        child = self.__class__
        stgs_dict = child.class_settings()
        for qsp_name, qsp_value_string in qsp_dict.items():
            if qsp_name in stgs_dict:
                stg = stgs_dict[qsp_name]
                if isinstance(stg, BooleanSetting):
                    qsp_value = (qsp_value_string == '1')
                else:
                    try:
                        qsp_value = eval(qsp_value_string)
                    except Exception:
                        qsp_value = qsp_value_string
                setattr(self, qsp_name, qsp_value)

    def align_with_qs(self, qs):
        qsp_dict = {nvp[0]: nvp[1]
                    for nvp in [qsp.split("=") for qsp in qs.split("&")]}
        self.align_with_dict(qsp_dict)

    def get_settings_as_dict(self):
        child = self.__class__
        sdict = {}
        for cv_name, cv_stg in child.class_settings().items():
            self._logger.debug(
                'get settings as dict: {0} {1}'.format(cv_name, type(cv_stg)))
            sdict[cv_name] = getattr(self, cv_name)
        return sdict

    def get_qs(self):
        child = self.__class__
        qsp_list = []
        for cv_name, cv_stg in child.class_settings().items():
            cv_val = getattr(self, cv_name)
            self._logger.debug(
                'Settings get_qs {0} {1}'.format(cv_name, cv_val))
            qsp = cv_name + '='
            if isinstance(cv_stg, BooleanSetting):
                qsp += '1' if cv_val else '0'
            else:
                # others
                qsp += str(cv_val)
            qsp_list.append(qsp)
        return '&'.join(qsp_list)

    def get_filtered_settings(self):
        # return filtered dictionary of settings for vision interface
        child = self.__class__
        sdict = {}
        for cv_name in child.class_settings():
            sdict[cv_name] = getattr(self, cv_name)
        return sdict

    def clone(self, initial_state=None):
        cls = self.__class__
        new_ob = cls()
        if isinstance(initial_state, str) and initial_state is not None and initial_state != '':
            # query string
            new_ob.align_with_qs(initial_state)
        elif isinstance(initial_state, configurations.Config):
            new_ob.align_with_config(initial_state)
        return new_ob

    def __repr__(self):
        s = ''
        for (k, v) in self.__dict__.items():
            s += k + ' = ' + str(v) + '\n'
        return s


class SimpleSettings(BaseSettings):

    # class variable settings
    _res_opts = {'{0}x{1}'.format(r[0], r[1]): '{0}x{1}{2}'.format(
        r[0], r[1], '*' if r[0] == 1536 else '') for r in sorted(list(constants.RESOLUTIONS))}
    resolution = EnumerationSetting(
        'Resolution', 'Camera Resolution [px]', _res_opts)

    hflip = BooleanSetting('Horizontal Flip', 'Flip Image Horizontally')
    vflip = BooleanSetting('Vertical Flip', 'Flip Image Vertically')
    vflip = BooleanSetting('Vertical Flip', 'Flip Image Vertically')

    def __init__(self, child):
        super().__init__(child)
        self.resolution = '800x600'


class VirtualSettings(SimpleSettings, Sibling):

    awb_mode = EnumerationSetting(
        'AWB Mode',
        'Auto-White Balance',
        ['Off', 'Auto', 'Incandescant', 'Tungsten', 'Flourescent',
            'Indoor', 'Daylight', 'Cloudy', 'Custom'],
        action="if (typeof syncGains === 'function') syncGains(this)",
        name='awb-mode')
    redgain = FloatSetting(
        'Red Gain', 'Red component of awb gain', '', 0.0, 32.0, 1.0, 'red-gain')
    bluegain = FloatSetting(
        'Blue Gain', 'Blue component of awb gain', '', 0.0, 32.0, 1.0, 'blue-gain')

    def __init__(self):
        super().__init__(self)


class UsbSettings(SimpleSettings):

    pass


class PiSettings(SimpleSettings, Sibling):

    awb_mode = EnumerationSetting(
        'AWB Mode',
        'Auto-White Balance',
        ['Off', 'Auto', 'Incandescant', 'Tungsten', 'Flourescent',
            'Indoor', 'Daylight', 'Cloudy', 'Custom'],
        action="if (typeof syncGains === 'function') syncGains(this)",
        name='awb-mode')
    redgain = FloatSetting(
        'Red Gain', 'Red component of awb gain', '', 0.0, 8.0, 0.1, 'red-gain')
    bluegain = FloatSetting(
        'Blue Gain', 'Blue component of awb gain', '', 0.0, 8.0, 0.1, 'blue-gain')

    def __init__(self):
        super().__init__(self)
        self.awb_mode = 'auto'
        self.redgain = 4.0
        self.bluegain = 4.0


class LusbSettings(UsbSettings, Sibling):

    def __init__(self):
        super().__init__(self)


class WusbSettings(UsbSettings, Sibling):

    def __init__(self):
        super().__init__(self)


class MeasureSettings(CoreSettings):

    css_style = 'width: 100%;height: 24px;text-align: right;font-weight: bold;margin-top: 10px'

    ls1 = LabelSetting('')
    ls2 = LabelSetting('Lower Range', {'style': css_style})
    ls3 = LabelSetting('')
    ls4 = LabelSetting('')
    ls5 = LabelSetting('Scale', {'style': css_style})
    ls6 = LabelSetting('')
    ls7 = LabelSetting('Upper Range', {'style': css_style})
    ls8 = LabelSetting('')
    ls9 = LabelSetting('')
    ls10 = LabelSetting('Max Score', {'style': css_style})
    ls11 = LabelSetting('')

    span_lower = FloatSetting(
        'Span', 'The lower span range', None, rmin=1.0, rmax=0.0, step=0.01)
    span_scale = FloatSetting('', 'The target span scale',
                              None, rmin=0, rmax=2.0, step=0.01, incl_slider=False)
    span_upper = FloatSetting(
        '', 'The upper span range', None, rmin=0, rmax=1.0, step=0.01)
    span_maxscore = IntSetting('', 'The maximum span score', None)

    area_lower = FloatSetting(
        'Area', 'The lower area range', None, rmin=1.0, rmax=0.0, step=0.01)
    area_scale = FloatSetting('', 'The target area scale',
                              None, rmin=0, rmax=2.0, step=0.0001, incl_slider=False)
    area_upper = FloatSetting(
        '', 'The upper area range', None, rmin=0, rmax=1.0, step=0.01)
    area_maxscore = IntSetting('', 'The maximum area score', None)

    ls21 = LabelSetting('')
    ls22 = LabelSetting('Lower Range', {'style': css_style})
    ls23 = LabelSetting('')
    ls24 = LabelSetting('')
    ls25 = LabelSetting('Setpoint', {'style': css_style})
    ls26 = LabelSetting('')
    ls27 = LabelSetting('Upper Range', {'style': css_style})
    ls28 = LabelSetting('')
    ls29 = LabelSetting('')
    ls210 = LabelSetting('Max Score', {'style': css_style})
    ls211 = LabelSetting('')

    isoscelicity_lower = FloatSetting(
        'Isoscelicity', 'The lower isoscelicity range', None, rmin=1.0, rmax=0.0, step=0.01)
    isoscelicity_setpoint = FloatSetting(
        '', 'The target isoscelicity value', None, rmin=0, rmax=1.0, step=0.01, incl_slider=False)
    isoscelicity_upper = FloatSetting(
        '', 'The upper isoscelicity range', None, rmin=0, rmax=1.0, step=0.01)
    isoscelicity_maxscore = FloatSetting(
        '', 'The maximum isoscelicity score', None)

    solidity_lower = FloatSetting(
        'Solidity', 'The lower solidity range', None, rmin=1.0, rmax=0.0, step=0.01)
    solidity_setpoint = FloatSetting(
        '', 'The target solidity value', None, rmin=0, rmax=1.0, step=0.01, incl_slider=False)
    solidity_upper = FloatSetting(
        '', 'The upper solidity range', None, rmin=0, rmax=1.0, step=0.01)
    solidity_maxscore = FloatSetting('', 'The maximum solidity score', None)

    fitness_lower = IntSetting(
        'Fitness', 'The lower fitness range', None, rmin=1.0, rmax=0.0, step=0.01)
    fitness_setpoint = IntSetting(
        '', 'The target fitness value', None, rmin=0, rmax=1.0, step=0.01, incl_slider=False)
    fitness_upper = IntSetting(
        '', 'The upper fitness range', None, rmin=0, rmax=1.0, step=0.01)
    fitness_maxscore = IntSetting('', 'The maximum fitness score', None)

    def __init__(self, config):

        self.span_scale = config['span.scale']
        self.span_lower = config['span.lower']
        self.span_upper = config['span.upper']
        self.span_maxscore = config['span.maxscore']

        self.area_scale = config['area.scale']
        self.area_lower = config['area.lower']
        self.area_upper = config['area.upper']
        self.area_maxscore = config['area.maxscore']

        self.isoscelicity_setpoint = config['isoscelicity.setpoint']
        self.isoscelicity_lower = config['isoscelicity.lower']
        self.isoscelicity_upper = config['isoscelicity.upper']
        self.isoscelicity_maxscore = config['isoscelicity.maxscore']

        self.solidity_setpoint = config['solidity.setpoint']
        self.solidity_lower = config['solidity.lower']
        self.solidity_upper = config['solidity.upper']
        self.solidity_maxscore = config['solidity.maxscore']

        self.fitness_setpoint = config['fitness.setpoint']
        self.fitness_lower = config['fitness.lower']
        self.fitness_upper = config['fitness.upper']
        self.fitness_maxscore = config['fitness.maxscore']

        # re-label with configured dimensions for display purposes
        target_length_m = config['mower.target_length_m']
        span_calc_expression = '{:.3f} *'.format(target_length_m)
        type(self).span_scale.label = span_calc_expression
        target_area_m2 = config['mower.target_area_m2']
        area_calc_expression = '{:.3f} *'.format(target_area_m2)
        type(self).area_scale.label = area_calc_expression
