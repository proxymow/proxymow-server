

class HtmlToolPane(object):
    '''
        Represents a toolpane in a webpage
    '''

    def __init__(self, tp_id, tp_class, tp_config, tp_vertical=False, tp_labels=True):
        '''
        Constructor
        '''
        self.id = tp_id
        self.class_name = tp_class
        self.config = tp_config
        self.is_vertical = tp_vertical
        self.has_labels = tp_labels

    def render(self):
        '''
            render toolpane to html string
        '''
        html = '<div class="{0}">\n'.format(self.class_name)
        for tool in self.config:
            html += self.render_tool(tool)
        html += '</div>\n'

        return html

    def render_tool(self, tool):
        '''
            render tool to html string
        '''
        tid, label, tooltip, icon_def, _action, _disabled = tool
        icon_svg = icon_def
        html = '\t<button id="{0}" type="button" title="{1}">{2}</button>\n'.format(
            tid,
            tooltip,
            icon_svg + '<span>' + label + '</span>' if self.has_labels and self.is_vertical else icon_svg +
            label if self.has_labels else icon_svg
        )
        return html
