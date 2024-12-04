from forms.term import Term


class Hybrid(Term):
    '''
        represents a variable term available to the rules
        the expression can be edited, but no other fields
        the term cannot be deleted

        name: str
        description: str
        expression: str
        result: str
        units: str
        alt_expression: str
        alt_result: str
        alt_units: str
        user_defined: bool
        colour: str

    '''
    pk_att_name = 'name'

    _hidden = ['result', 'alt_result']
    _readonlys = [pk_att_name, 'description', 'units',
                  'alt_expression', 'alt_units', 'scope', 'user_defined']
