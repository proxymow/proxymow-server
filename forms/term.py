from forms.morphable import Morphable
from dupe_key_dict import DupeKeyDict
from setting import TextSetting, ExpressionSetting, EnumerationSetting


class Term(Morphable):
    '''
        represents a variable term available to the rules
    '''
    pk_att_name = 'name'

    _hidden = ['result', 'alt_result']

    name = TextSetting('Term Name', 'Name of the term', None,
                       '^.{1,}$', 'must have at least 1 character')
    description = TextSetting('Term Description', 'Term description')
    expression = ExpressionSetting(
        'Term Expression', 'Term expression', char_width=30)
    units = TextSetting('Units', 'Term units')
    alt_expression = ExpressionSetting(
        'Alt Expression', 'Alternative term expression', char_width=30)
    alt_units = TextSetting('Alt Units', 'Alternative term units')
    colour = EnumerationSetting('Colour', 'Group colour for annotations', [
                                'None', 'white', 'silver', 'gray', 'black', 'red', 'maroon', 'yellow', 'olive', 'lime', 'green', 'aqua', 'teal', 'blue', 'navy', 'fuchsia', 'purple'])

    def __init__(
            self,
            dictionary=None,
            name=None,
            description=None,
            expression=None,
            units=None,
            alt_expression=None,
            alt_units=None,
            colour=None,
            cur_strategy=None
    ):
        '''
        Constructor
        '''
        if dictionary is not None:
            for k, v in dictionary.items():
                setattr(self, k, v)
        else:
            self.name = name
            self.description = description
            self.expression = expression
            self.result = None
            self.units = units
            self.alt_expression = alt_expression
            self.alt_result = None
            self.alt_units = alt_units
            self.colour = colour
            self._cur_strategy = cur_strategy

    def __str__(self):
        return self.description + '<' + self.name + '>' + ('=' + self.expression if self.expression is not None else '')

    def __key(self):
        return (self.name, self.description, self.expression, self.result, self.units, self.alt_expression, self.alt_result, self.alt_units, self.colour)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__key() == other.__key()
        return NotImplemented

    def render_dict(self, _row_index=0, _max_row_index=0):

        debug = False
        # set empty to show all columns for debugging
        hidden_col_prefix = '' if debug else '_'
        variant = self.__class__.__name__

        # conditional inclusion not permitted - a column must be populated
        row_attributes = {}
        row_attributes[hidden_col_prefix +
                       '@row_class'] = 'row-{}'.format(variant.lower())

        if variant == 'Term':
            xpath = "navigation_strategies/strategy[@name='{0}']/user_terms/term[@name='{1}']".format(
                self._cur_strategy, self.name)
            action = 'document.getElementsByClassName("settings-form")[0].style.display="block";renderForm(null, "{0}");'.format(
                xpath)
            row_attributes[hidden_col_prefix + '@row_ondblclick'] = action
        elif variant == 'Hybrid':
            xpath = "navigation_strategies/strategy[@name='{0}']/hybrid_terms/hybrid[@name='{1}']".format(
                self._cur_strategy, self.name)
            action = 'document.getElementsByClassName("settings-form")[0].style.display="block";renderForm(null, "{0}");'.format(
                xpath)
            row_attributes[hidden_col_prefix + '@row_ondblclick'] = action
        else:
            row_attributes[hidden_col_prefix + '@row_ondblclick'] = ''

        # merge extra items and row attributes into new dict
        dkdict = DupeKeyDict(row_attributes)
        dkdict['Name'] = self.name
        dkdict['Description'] = self.description
        dkdict['Expression'] = self.expression
        dkdict['Result'] = '{0} {1}'.format(
            self.result if self.result is not None else '',
            self.units if self.result is not None else ''
        )
        dkdict['Alt Expression'] = self.alt_expression
        dkdict['Alt Result'] = '{0} {1}'.format(
            self.alt_result if self.alt_result is not None and self.alt_result != -1 else '',
            self.alt_units if self.alt_result is not None and self.alt_result != -1 else ''
        )
        dkdict['Colour'] = self.colour

        extra_items = {
            'Action': '<button onclick="strategyTermDelete(\'{}\')">Delete</button>'.format(self.name) if variant == 'Term' else ''
        }
        dkdict.update(extra_items)

        return dkdict


class User_Term(Term):
    pk_att_name = 'name'
