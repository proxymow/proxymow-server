import sys
import logging
import numpy as np
from math import copysign
from enum import Enum

import constants
from utilities import trace_rules, trace_command, despatch_to_mower_udp
from dupe_key_dict import DupeKeyDict
from forms.morphable import Morphable
from setting import TextSetting, ExpressionSetting, BooleanSetting, EnumerationSetting


class RuleScope(Enum):
    STATIONARY = 0
    IN_FLIGHT = 1
    ANY = 2
    DISABLED = 3


class Rule(Morphable):
    '''
        a navigation strategy rule

    '''

    pk_att_name = 'name'

    name = TextSetting('Rule Name', 'Name of the rule', None,
                       '^.{6,}$', 'must have at least 6 characters', char_width=32)
    description = TextSetting(
        'Rule Description', 'Rule description', char_width=48)
    condition = ExpressionSetting(
        'Condition', 'Condition that selects rule', char_width=30)
    left_speed = ExpressionSetting(
        'Left Speed', 'Rule\'s left speed expression', char_width=30)
    right_speed = ExpressionSetting(
        'Right Speed', 'Rule\'s right speed expression', char_width=30)
    duration = ExpressionSetting(
        'Duration', 'Rule\'s duration expression', char_width=30)
    scope = EnumerationSetting('Scope', 'Rule\'s scope applicability', {
                               0: 'Stationary', 1: 'In-Flight', 2: 'Any', 3: 'Disabled'})
    stage_complete = BooleanSetting(
        'Stage Complete', 'Condition to complete the stage')

    def __init__(
            self,
            dictionary=None,
            index=-1,
            name='',
            description='',
            priority=-1,
            condition='',
            left_speed='',
            right_speed='',
            duration='',
            stage_complete=False,
            scope=0,
            cur_strategy=None
    ):
        '''
        Constructor
        '''
        if dictionary is not None:
            for k, v in dictionary.items():
                setattr(self, k, v)
        else:
            self.index = index
            self.name = name
            self.description = description
            self.priority = priority
            self.condition = condition
            self.condition_state = False
            self.condition_info = 'not available'
            self.condition_error = ''
            self.left_speed = left_speed
            self._left_speed_result = None
            self.left_speed_info = 'not available'
            self.left_speed_error = ''
            self.right_speed = right_speed
            self._right_speed_result = None
            self.right_speed_info = 'not available'
            self.right_speed_error = ''
            self.duration = duration
            self._duration_result = None
            self.duration_info = ''
            self.duration_error = ''
            self.stage_complete = stage_complete
            self.scope = scope
            self.trace_on = True
            self.cur_strategy = cur_strategy

            # initialise the escalation ladder matrix
            self._escalation_matrix = None
            self._rung_index = -1

        self._logger = logging.getLogger('navigation')

    @property
    def auxiliary(self):
        '''
            The auxiliary property
        '''
        return (
            (self.left_speed is None or self.left_speed.strip() == '') and
            (self.right_speed is None or self.right_speed.strip() == '') and
            self.duration is not None and
            self.duration.strip() != ''
        )

    @property
    def left_speed_result(self):
        '''The left_speed_result property.'''
        if not self.condition_state:
            result = None
        # current rung of the escalation matrix
        elif (constants.ESCALATION_ENABLED and
              self.scope == RuleScope.STATIONARY.value and
              self._rung_index >= 0 and
              self._escalation_matrix is not None):
            result = self._escalation_matrix[self._rung_index][0]
        else:
            result = self._left_speed_result
        return result

    @left_speed_result.setter
    def left_speed_result(self, value):
        self._left_speed_result = value

    @property
    def right_speed_result(self):
        '''The right_speed_result property.'''
        if not self.condition_state:
            result = None
        # current rung of the escalation matrix
        elif (constants.ESCALATION_ENABLED and
              self.scope == RuleScope.STATIONARY.value and
              self._rung_index >= 0 and
              self._escalation_matrix is not None):

            result = self._escalation_matrix[self._rung_index][1]
        else:
            result = self._right_speed_result
        return result

    @right_speed_result.setter
    def right_speed_result(self, value):
        self._right_speed_result = value

    @property
    def duration_result(self):
        '''The duration_result property.'''
        if not self.condition_state:
            result = None
        # current rung of the escalation matrix
        elif (constants.ESCALATION_ENABLED and
              self.scope == RuleScope.STATIONARY.value and
              self._rung_index >= 0 and
              self._escalation_matrix is not None):
            result = self._escalation_matrix[self._rung_index][2]
        else:
            result = self._duration_result
        return result

    @duration_result.setter
    def duration_result(self, value):
        self._duration_result = value

    @property
    def num_rungs(self):
        # first rung is the un-escalated command
        if self._escalation_matrix is not None:
            result = len(self._escalation_matrix) - 1
        else:
            result = 0
        return result

    @property
    def is_executable(self):
        # does the command have left/right/duration?
        is_navigation = not [v for v in (
            self.left_speed, self.right_speed, self.duration) if v is None or v.strip() == '']
        return is_navigation or self.auxiliary

    def in_scope(self, scope):
        '''
            determines if rule is in scope:
                enabled, or
                any of Stationary | In-Flight
        '''
        return (
            self.scope != RuleScope.DISABLED.value and
            (
                (self.scope == scope.value or
                    (scope == RuleScope.ANY and self.scope in [RuleScope.STATIONARY.value, RuleScope.IN_FLIGHT.value]) or
                    (self.scope == RuleScope.ANY.value and scope in [
                     RuleScope.STATIONARY, RuleScope.IN_FLIGHT])
                 )
            )
        )

    def __key(self):
        return (
            self.index,
            self.name,
            self.description,
            self.priority,
            self.condition,
            self.condition_state,
            self.left_speed,
            self.left_speed_result,
            self.right_speed,
            self.right_speed_result,
            self.duration,
            self.duration_result,
            self.stage_complete,
            self.scope
        )

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Rule):
            return self.__key() == other.__key()
        return NotImplemented

    def __repr__(self):
        return '{} {} {} {} {} {} {} {} {} {}'.format(
            self.index,
            self.name,
            self.description,
            self.priority,
            self.condition if self.condition is not None else '',
            self.condition_state,
            self.left_speed if self.left_speed is not None else '',
            self.right_speed if self.right_speed is not None else '',
            self.duration if self.duration is not None else '',
            self.stage_complete
        )

    @property
    def cmd(self):
        """The cmd property."""
        units = ('%', 'ms')
        if self.left_speed_result is None and self.right_speed_result is None and self.duration_result is None:
            result = self.name
        elif self.auxiliary:
            result = self.name + ' [' + self.duration_result + ']'
        else:
            result = '{} ({}{}, {}{}, {}{}){}'.format(
                self.name,
                '' if self.left_speed_result is None else self.left_speed_result,
                '' if self.left_speed_result is None else units[0],
                '' if self.right_speed_result is None else self.right_speed_result,
                '' if self.left_speed_result is None else units[0],
                '' if self.duration_result is None else self.duration_result,
                '' if self.duration_result is None else units[1],
                self._rung_index * '+'
            )
        return result

    def check(self, context, safe_functions, terms_units, trace=False):
        # update internal condition state
        if self.condition is not None and self.condition.strip() != '':
            try:
                self.condition_state = eval(
                    self.condition, context, safe_functions)
                comp = compile(self.condition, "<string>", "eval")
                ref_terms = {key: round(context[key], 5) if isinstance(
                    context[key], float) else context[key] for key in comp.co_names if key in context}
                terms_list = [f'{k}={v} {terms_units[k] if k in terms_units else ""}' for k, v in ref_terms.items()]
                self.condition_info = (', '.join(terms_list)).strip()
                self.condition_error = ''
            except Exception as e:
                self.condition_error = str(e)
            if self.trace_on and trace:
                trace_rules('Checking Rule {} Condition: {{{}}} Info: {} result is {} "{}"'.format(
                    self.priority,
                    self.condition,
                    self.condition_info,
                    self.condition_state,
                    self.condition_error)
                )

        # return state for convenience
        return self.condition_state

    def parse(self, context, safe_functions, terms_units, trace=False):
        try:
            if self.left_speed is not None and self.left_speed.strip() != '':
                try:
                    self.left_speed_result = round(
                        eval(self.left_speed, context, safe_functions))
                    comp = compile(self.left_speed, "<string>", "eval")
                    ref_terms = {key: round(context[key], 5) if isinstance(
                        context[key], float) else context[key] for key in comp.co_names if key in context}
                    terms_list = [f'{k}={v} {terms_units[k] if k in terms_units else ""}' for k, v in ref_terms.items()]
                    self.left_speed_info = (', '.join(terms_list)).strip()
                    self.left_speed_error = ''
                except Exception as e:
                    self.left_speed_error = str(e)
            if self.right_speed is not None and self.right_speed.strip() != '':
                try:
                    self.right_speed_result = round(
                        eval(self.right_speed, context, safe_functions))
                    comp = compile(self.right_speed, "<string>", "eval")
                    ref_terms = {key: round(context[key], 5) if isinstance(
                        context[key], float) else context[key] for key in comp.co_names if key in context}
                    terms_list = [f'{k}={v} {terms_units[k] if k in terms_units else ""}' for k, v in ref_terms.items()]
                    self.right_speed_info = (', '.join(terms_list)).strip()
                    self.right_speed_error = ''
                except Exception as e:
                    self.right_speed_error = str(e)
            if self.duration is not None and self.duration.strip() != '':
                try:
                    if self.auxiliary:
                        self.duration_result = eval(
                            self.duration, context, safe_functions)
                    else:
                        self.duration_result = round(
                            eval(self.duration, context, safe_functions))
                    comp = compile(self.duration, "<string>", "eval")
                    ref_terms = {key: round(context[key], 5) if isinstance(
                        context[key], float) else context[key] for key in comp.co_names if key in context}
                    terms_list = [f'{k}={v} {terms_units[k] if k in terms_units else ""}' for k, v in ref_terms.items()]
                    self.duration_info = (', '.join(terms_list)).strip()
                    self.duration_error = ''
                except Exception as e:
                    self.duration_error = str(e)

            if self.trace_on and trace:
                trace_rules('Parsing Rule ' + str(self.priority) + ': {' +
                            self.left_speed + '} => ' + str(self.left_speed_result) + ' ' + str(self.left_speed_info) + ', {' + ((' exception: ' + self.left_speed_error) if self.left_speed_error != '' else '') +
                            self.right_speed + '} => ' + str(self.right_speed_result) + ' ' + str(self.right_speed_info) + ', {' + ((' exception: ' + self.right_speed_error) if self.right_speed_error != '' else '') +
                            self.duration + '} => ' + str(self.duration_result) + ' ' + str(self.duration_info) + ((' exception: ' + self.duration_error) if self.duration_error != '' else ''))

            # update the escalation matrix

            # find the steps between initial and maximum
            num_steps = 1 + constants.NUM_ESCALATION_RUNGS
            endpts = True
            if (constants.ESCALATION_ENABLED and
                not self.stage_complete and
                not self.auxiliary):
                if (self._left_speed_result is not None and
                    self._right_speed_result is not None and
                        self._duration_result is not None and self._duration_result > 0):
                    dur_factor = constants.ESCALATION_DURATION_FACTOR
                    if self._left_speed_result * self._right_speed_result >= 0:
                        # driving
                        if self.trace_on and trace:
                            trace_rules(
                                'Parsing Rule {} calculating driving escalation'.format(self.priority))
                        if self._left_speed_result == 0:
                            # 1WR
                            left_speed_steps = np.zeros(num_steps, dtype=int)
                            dur_factor = 1.0  # no duration reduction
                        else:
                            left_speed_steps = np.linspace(self._left_speed_result, copysign(
                                100, self._left_speed_result), num=num_steps, endpoint=endpts, dtype=int)
                        if self._right_speed_result == 0:
                            # 1WR
                            right_speed_steps = np.zeros(num_steps, dtype=int)
                            dur_factor = 1.0  # no duration reduction
                        else:
                            right_speed_steps = np.linspace(self._right_speed_result, copysign(
                                100, self._right_speed_result), num=num_steps, endpoint=endpts, dtype=int)
                        if self._duration_result < 100:
                            duration_steps = np.linspace(
                                100, 1000, num=num_steps, dtype=int)
                        else:
                            start_dur = self._duration_result * \
                                abs(max(self._left_speed_result,
                                    self._right_speed_result) / 100)
                            scaled_dur = (
                                (self._duration_result - start_dur) * dur_factor) + start_dur
                            duration_steps = np.linspace(
                                self._duration_result, scaled_dur, num=num_steps, endpoint=endpts, dtype=int)
                    else:
                        # rotation
                        if self.trace_on and trace:
                            trace_rules(
                                'Parsing Rule {} calculating rotating escalation'.format(self.priority))
                        left_speed_steps = np.linspace(self._left_speed_result, copysign(
                            100, self._left_speed_result), num=num_steps, endpoint=endpts, dtype=int)
                        # 2WR => 2WR
                        right_speed_steps = np.linspace(self._right_speed_result, copysign(
                            100, self._right_speed_result), num=num_steps, endpoint=endpts, dtype=int)
                        # 2WR => 1WR - aimed at increasing rotational torque
                        # this tactic is suspected to cause instability near target!
                        # if we need it we are going to have to append it as a last resort
                        # right_speed_steps = np.linspace(self._right_speed_result, 0, num=num_steps, endpoint=endpts, dtype=int)

                        max_speed_ratio = abs(
                            max(self._left_speed_result, self._right_speed_result) / 100)
                        start_dur = self._duration_result * max_speed_ratio
                        scaled_dur = (
                            (self._duration_result - start_dur) * dur_factor) + start_dur
                        duration_steps = np.linspace(
                            self._duration_result, scaled_dur, num=num_steps, endpoint=endpts, dtype=int)

                    self._escalation_matrix = np.dstack(
                        [left_speed_steps, right_speed_steps, duration_steps])[0].tolist()
                    self._rung_index = 0

                    if self.trace_on and trace:
                        trace_rules(
                            'Parsing Rule {} escalation matrix updated'.format(self.priority))
                else:
                    self._escalation_matrix = [[None, None, None]]
                    self._rung_index = 0
                    if self.trace_on and trace:
                        trace_rules(
                            'Parsing Rule {} escalation matrix disabled'.format(self.priority))

            else:
                if self.trace_on and trace:
                    trace_rules(
                        'Parsing Rule {} escalation matrix NOT updated'.format(self.priority))

            if self.trace_on and trace:
                trace_rules('Rule {} [{}] Escalation {}'.format(
                    self.priority, self.name, self._escalation_matrix))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self._logger.error('Error in Rule parse: ' +
                               str(e) + ' on line ' + str(err_line))

    def compile_cmd(self):
        # compile the rule command
        cmd = None
        try:
            if self.auxiliary:
                cmd = self.duration_result
            else:
                cmd = 'sweep({}, {}, {})'.format(
                    self.left_speed_result,
                    self.right_speed_result,
                    self.duration_result
                )
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self._logger.error('Error in Rule compile: ' +
                               str(e) + ' on line ' + str(err_line))

        return cmd

    def execute(self, config, udp_socket, trace=False):
        # execute the rule
        resp = None
        try:
            # execute the rule
            cmd = self.compile_cmd()
            msg = 'Strategy Rule ' + self.name + ' transmitting Command: [' + cmd + ']'
            if self.trace_on and trace:
                trace_rules(msg)
                trace_command(msg)

            resp = self.despatch(cmd, config, udp_socket)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self._logger.error('Error in Rule execute: ' +
                               str(e) + ' on line ' + str(err_line))

        return self.stage_complete, resp

    def despatch(self, cmd, config, udp_socket):

        host = config['mower.ip']
        port = config['mower.port']
        resp = despatch_to_mower_udp(
            cmd, udp_socket, host, port, await_response=True, max_attempts=1)
        return resp

    def cleardown(self):
        # clear rule
        self.condition_state = False
        self.condition_info = ''
        self.condition_error = ''
        self.left_speed_result = None
        self.left_speed_info = ''
        self.left_speed_error = ''
        self.right_speed_result = None
        self.right_speed_info = ''
        self.right_speed_error = ''
        self.duration_result = None
        self.duration_info = ''
        self.duration_error = ''
        self._rung_index = 0

    def render_dict(self, pre_obj=None, succ_obj=None):

        debug = False
        # set empty to show all columns for debugging
        hidden_col_prefix = '' if debug else '_'

        self.enabled = int(self.scope) != RuleScope.DISABLED.value

        # conditional inclusion not permitted - a column must be populated
        row_attributes = {}
        row_attributes[hidden_col_prefix +
                       '@row_class'] = 'row-disabled' if not self.enabled else 'row-auxiliary' if self.auxiliary else ''
        row_attributes[hidden_col_prefix +
                       '@row_title'] = '{0}'.format(self.description)

        xpath = "navigation_strategies/strategy[@name='{0}']/rules/rule[@name='{1}']".format(
            self.cur_strategy, self.name)
        klassparam = ', "AuxRule"' if self.auxiliary else ''
        action = 'document.getElementsByClassName("settings-form")[0].style.display="block";renderForm(null, "{}", "edit"{});'.format(
            xpath, klassparam)
        row_attributes[hidden_col_prefix + '@row_ondblclick'] = action

        # merge extra items and row attributes into new dict
        dkdict = DupeKeyDict(row_attributes)
        dkdict[hidden_col_prefix + 'index'] = self.index
        dkdict['name'] = self.name
        dkdict['description'] = self.description

        dkdict['priority'] = self.priority
        dkdict[hidden_col_prefix + '@cell_style'] = 'text-align: right'
        dkdict[hidden_col_prefix +
               '@cell_class'] = 'down-arrow' if pre_obj is None else 'up-arrow' if succ_obj is None else 'up-down-arrow'
        dkdict[hidden_col_prefix + '@cell_onclick'] = 'reposition(event, "{0}",{1},"{2}",{3},"{4}",{5})'.format(
            pre_obj.name if pre_obj is not None else -1,
            pre_obj.priority if pre_obj is not None else -1,
            self.name,
            self.priority,
            succ_obj.name if succ_obj is not None else -1,
            succ_obj.priority if succ_obj is not None else -1
        )  # promote or demote

        dkdict['condition'] = self.condition
        dkdict[hidden_col_prefix + '@cell_class'] = self.cond_cell_class()
        dkdict[hidden_col_prefix +
               '@cell_title'] = self.tooltip(self.condition_info)
        dkdict[hidden_col_prefix + 'condition_state'] = self.condition_state
        dkdict[hidden_col_prefix + 'condition_error'] = self.condition_error

        dkdict['left_speed'] = self.left_speed
        dkdict[hidden_col_prefix + '@cell_class'] = self.aux_cell_class()
        dkdict[hidden_col_prefix +
               '@cell_title'] = self.tooltip(self.left_speed_info)

        dkdict['left_speed_result'] = self.left_speed_result
        dkdict[hidden_col_prefix + '@cell_class'] = self.aux_cell_class()

        dkdict[hidden_col_prefix + 'left_speed_error'] = self.left_speed_error

        dkdict['right_speed'] = self.right_speed
        dkdict[hidden_col_prefix + '@cell_class'] = self.aux_cell_class()
        dkdict[hidden_col_prefix +
               '@cell_title'] = self.tooltip(self.right_speed_info)

        dkdict['right_speed_result'] = self.right_speed_result
        dkdict[hidden_col_prefix + '@cell_class'] = self.aux_cell_class()

        dkdict[hidden_col_prefix + 'right_speed_error'] = self.right_speed_error

        dkdict['duration/cmd'] = self.duration
        dkdict[hidden_col_prefix +
               '@cell_title'] = self.tooltip(self.duration_info)

        dkdict['duration/cmd_result'] = self.duration_result
        dkdict[hidden_col_prefix + 'duration_error'] = self.duration_error
        dkdict['stage_complete'] = self.stage_complete
        dkdict['scope'] = self.__class__.scope.options[int(self.scope)]

        extra_items = {
            'Action': '<button onclick="strategyRuleDelete(\'{}\')">Delete</button>'.format(self.name),
            'Duplicate': '<button onclick="strategyRuleDuplicate(\'{}\', \'{}\')">Duplicate</button>'.format(self.cur_strategy, self.name)
        }

        dkdict.update(extra_items)

        return dkdict

    def cond_cell_class(self):
        result = 'cell-normal'
        if self.condition_error:
            result = 'cell-error'
        elif self.condition_state:
            result = 'cell-matched'
        return result

    def aux_cell_class(self):
        result = 'cell-normal'
        if self.auxiliary:
            result = 'cell-aux'
        return result

    def tooltip(self, info):
        result = 'Unmatched: ' + info
        if not self.enabled:
            result = 'disabled'
        elif self.condition_error != '':
            result = self.condition_error
        elif self.condition_state:
            result = 'Matched: ' + info
        return result


class AuxRule(Rule):

    pk_att_name = 'name'
    left_speed = None
    right_speed = None
    duration = ExpressionSetting(
        'Direct Command', 'Rule\'s direct command expression', char_width=30)
