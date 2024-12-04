

class ToolPaneTool():
    '''
    Represents a tool in a ToolPane
    '''

    def __init__(self, tool_key, tool_name, label, unit_str, tooltip, action, enabled, html_options):
        '''
        Constructor
        '''
        self.key = tool_key
        self.name = tool_name
        self.label = label
        self.unit_str = unit_str if unit_str is not None else ''
        self.tooltip = tooltip
        self.action = action
        self.enabled = enabled
        # add widget class to all widgets
        if 'class' in html_options:
            html_options['class'] += ' widget'
        else:
            html_options['class'] = 'widget'

        self.html_options = html_options

    @property
    def classname(self):
        return type(self).__name__

    def __repr__(self):
        return str(self.__dict__)


class ToolPaneButton(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options, icon):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.icon = icon
        self.cur_val = None


class ToolPaneDropdown(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options, data_options, cur_val, default_options):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.data_options = data_options
        # convert current value to integer key if possible
        try:
            self.cur_val = int(cur_val)
        except Exception:
            self.cur_val = cur_val

        self.default_options = default_options


class ToolPaneNumber(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, unit_str, tooltip, action, slide_action, enabled, html_options, min_val, max_val, step, cur_val):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, unit_str,
                         tooltip, action, enabled, html_options)
        self.cur_val = cur_val

        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.slide_action = slide_action
        self.has_slider = (slide_action is not None)
        # add tpt-number class to all widgets
        if 'class' in html_options:
            html_options['class'] += ' tpt-number'
        else:
            html_options['class'] = 'tpt-number'

        self.html_options = html_options


class ToolPaneCheck(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options, cur_val):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.cur_val = cur_val


class ToolPaneSlide(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options, cur_val):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.cur_val = cur_val


class ToolPaneString(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, unit_str, tooltip, action, enabled, html_options, cur_val, val_regex=None, val_msg=None, char_width=20):
        '''
        Constructor
        '''
        html_options['size'] = char_width
        if 'class' in html_options:
            html_options['class'] += ' tpt-string'
        else:
            html_options['class'] = 'tpt-string'

        super().__init__(tool_key, tool_name, label, unit_str,
                         tooltip, action, enabled, html_options)
        self.cur_val = cur_val
        self.val_regex = val_regex
        self.val_msg = val_msg


class ToolPaneExpression(ToolPaneString):
    def __init__(self, tool_key, tool_name, label, unit_str, tooltip, action, enabled, html_options, cur_val, val_regex=None, val_msg=None, char_width=20):
        '''
        Constructor
        '''
        if 'class' in html_options:
            html_options['class'] += ' tpt-expression'
        else:
            html_options['class'] = 'tpt-expression'

        super().__init__(tool_key, tool_name, label, unit_str, tooltip, action,
                         enabled, html_options, cur_val, val_regex, val_msg, char_width)


class ToolPaneIndicator(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.cur_val = None


class ToolPaneBatteryIndicator(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, action, enabled, html_options):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label, None,
                         tooltip, action, enabled, html_options)
        self.cur_val = None


class ToolPaneReadout(ToolPaneTool):
    def __init__(self, tool_key, tool_name, label, tooltip, enabled, html_options, cur_val):
        '''
        Constructor
        '''
        super().__init__(tool_key, tool_name, label,
                         None, tooltip, None, enabled, html_options)
        self.cur_val = cur_val


class ToolPaneLabel(ToolPaneTool):
    def __init__(self, label, html_options={}):
        '''
        Constructor
        '''
        self.key = None
        self.name = None
        self.cur_val = label
        self.html_options = html_options


class ToolPaneGap(ToolPaneTool):
    def __init__(self, html_options={}):
        '''
        Constructor
        '''
        self.key = None
        self.name = None
        self.cur_val = None
        self.html_options = html_options


class ToolPaneNewline(ToolPaneTool):
    def __init__(self, height_px):
        '''
        Constructor
        '''
        self.key = None
        self.name = None
        self.cur_val = None
        self.html_options = {'style': 'height: {0}px'.format(height_px)}


class ToolPaneHidden(ToolPaneTool):
    def __init__(self, tool_key, tool_name, cur_val):
        '''
        Constructor
        '''
        self.key = tool_key
        self.name = tool_name
        self.cur_val = cur_val
