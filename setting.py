import tool_pane_tool  # @UnusedImport


class BaseSetting():
    def __init__(self):
        self.default = None


class SimpleSetting(BaseSetting):
    def __init__(self, label, doc, units, name):
        super().__init__()
        self.label = label
        self.doc = doc
        self.units = units
        self.name = name

    def get_tool(self):
        return None

    def __repr__(self):
        return str(self.__dict__)


class HiddenSetting(BaseSetting):
    def __init__(self):
        super().__init__()
        self.label = None

    def get_tool(self, key, value, _enab=True):
        return tool_pane_tool.ToolPaneHidden(key, None, value)


class LabelSetting(BaseSetting):
    def __init__(self, label, html_options={}):
        super().__init__()
        self.label = label
        self.html_options = html_options

    def get_tool(self, _key, _value, _enab=True):
        return tool_pane_tool.ToolPaneLabel(self.label, self.html_options)


class EnumerationSetting(SimpleSetting):
    def __init__(self, label, doc, options, def_options={}, action=None, name=None):
        super().__init__(label, doc, '', name)
        self.options = options
        self.def_options = def_options
        self.action = action

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneDropdown(key, self.name, self.label, self.doc, self.action, enab, {}, self.options, value, self.def_options)


class NumberSetting(SimpleSetting):
    def __init__(self, label, doc, units, rmin, rmax, step, name):
        super().__init__(label, doc, units, name)
        self.min = rmin
        self.max = rmax
        self.step = step
        self.default = 0


class IntSetting(NumberSetting):
    def __init__(self, label, doc, units, rmin=0, rmax=100, step=1, name=None, incl_slider=True):
        super().__init__(label, doc, units, rmin, rmax, step, name)
        self.slide_action = '' if incl_slider else None

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneNumber(
            key, self.name, self.label, self.units, self.doc, None, self.slide_action, enab, {
            }, self.min, self.max, self.step, value
        )


class FloatSetting(NumberSetting):
    def __init__(self, label, doc, units, rmin=0, rmax=100, step=1, name=None, incl_slider=True):
        super().__init__(label, doc, units, rmin, rmax, step, name)
        self.default = 0.0
        self.slide_action = '' if incl_slider else None

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneNumber(
            key, self.name, self.label, self.units, self.doc, None, self.slide_action, enab, {
            }, self.min, self.max, self.step, value
        )


class BooleanSetting(SimpleSetting):
    def __init__(self, label, doc, name=None):
        super().__init__(label, doc, '', name)
        self.default = False

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneCheck(key, self.name, self.label, self.doc, None, enab, {}, value)


class TextSetting(SimpleSetting):
    def __init__(self, label, doc, units=None, regex=None, msg=None, char_width=20, name=None):
        super().__init__(label, doc, units, name)
        self.regex = regex
        self.msg = msg
        self.char_width = char_width

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneString(key, self.name, self.label, self.units, self.doc, None, enab, {}, value, self.regex, self.msg, self.char_width)


class ExpressionSetting(TextSetting):
    def __init__(self, label, doc, units=None, regex=None, msg=None, char_width=20, name=None):
        super().__init__(label, doc, units, regex, msg, char_width, name)

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneExpression(key, self.name, self.label, self.units, self.doc, None, enab, {}, value, self.regex, self.msg, self.char_width)


class ColorSetting(TextSetting):
    def __init__(self, label, doc, units=None, regex=None, msg=None, char_width=20, name=None):
        super().__init__(label, doc, units, regex, msg, char_width, name)

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneString(key, self.name, self.label, self.units, self.doc, None, enab, {'type': "color"}, value, self.regex, self.msg, self.char_width)
    
class PasswordSetting(TextSetting):
    def __init__(self, label, doc, units=None, regex=None, msg=None, char_width=20, name=None):
        super().__init__(label, doc, units, regex, msg, char_width, name)

    def get_tool(self, key, value, enab):
        return tool_pane_tool.ToolPaneString(key, self.name, self.label, self.units, self.doc, None, enab, {'type': "password"}, value, self.regex, self.msg, self.char_width)
