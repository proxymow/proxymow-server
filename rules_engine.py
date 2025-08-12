import sys
from math import degrees, radians, pi
import time
import logging
import numpy
from collections import deque

from utilities import trace_rules, get_safe_functions
from geom_lib import get_circle_from_world_points, get_angle_between_cartesian_points, get_distance_between_points
from odometry import MovementCode
from forms.rule import RuleScope
import geom_lib
from destination import Attitude
import constants

class RulesEngine():
    '''
    Rules Engine to execute navigation strategies
    '''

    def __init__(self, name, rules, terms, udp_socket, data_mapper):
        '''
        Constructor
        '''
        self.name = name
        self.set_rules(rules)
        self.set_terms(terms)
        self.context = {}
        self.safe_functions = get_safe_functions()

        self.last_n_commands = deque([], 10)
        self.last_n_comp_commands = deque([], 10)
        self.last_command = (-1, -1, -1)
        self.last_command_code = MovementCode.NIL.name
        self.in_flight = False
        self.robot_attitude = Attitude.DEFAULT.name

        self.stage_started_time = -1
        self.route_started_time = -1
        self.udp_socket = udp_socket
        self.data_mapper = data_mapper
        self.logger = logging.getLogger('navigation')
        self.lclogger = logging.getLogger('last-cmds')

    def __key(self):
        return (self.rules_key(), self.terms_key())

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, RulesEngine):
            return self.__key() == other.__key()
        return NotImplemented

    def rules_key(self):
        return (tuple(self.rules))

    def terms_key(self):
        return (tuple(self.terms))

    def set_terms(self, terms):
        # sets the terms and sorts
        self.terms = terms
        sort_order = 'Term|Hybrid|Systerm'
        self.terms.sort(key=lambda term: sort_order.index(
            term.__class__.__name__), reverse=False)
        
        # assemble dictionary of units for rule tooltips
        self.terms_units = {d.name: d.units for d in self.terms if d.units != ''}

    def set_rules(self, rules):
        # sets the rules and sorts
        self.rules = rules
        self.rules.sort(key=lambda rule: rule.priority)

    def build_context(
        self,
        snapshot,
        itinerary,
        config,
        telem,
        trace=False
    ):

        # collect together all the useful terms for our conditions and expressions
        try:
            # might need some numpy math, or geometry functions...
            self.context['np'] = numpy
            self.context['gl'] = geom_lib

            # some are parameters passed in
            if snapshot is not None:
                if trace:
                    self.logger.debug(
                        'build_context using incoming snapshot for current pose')
                self.context['ssid'] = snapshot.ssid
                pose = snapshot._pose
                t_zero = snapshot._t_zero
            else:
                if trace:
                    self.logger.debug(
                        'build_context NO incoming snapshot for current pose')
                self.context['ssid'] = -1
                pose = None
                t_zero = 0

            self.context['lt'] = time.strftime(
                '%H:%M:%S', time.localtime(t_zero))

            # some are historic and/or my own instance variables
            self.context['m'] = self.last_command
            self.context['p'] = self.last_command_code
            self.context['z'] = self.in_flight

            # robot attitude - has to be captured when the robot is approaching, not adjacent or beyond
            if self.last_command_code == 'FWD':
                self.robot_attitude = Attitude.FWD_DRIVE.name
            elif self.last_command_code == 'REV':
                self.robot_attitude = Attitude.REV_DRIVE.name
            self.context['rat'] = self.robot_attitude

            # some will come from itinerary
            if itinerary is not None:
                if trace:
                    self.logger.debug(
                        'build_context using incoming itinerary for current/previous destinations')
                self.context['i'] = itinerary.dest_ptr + 1  # destination index
                prev_dest, tgt_dest = itinerary.get_path_ends()
            else:
                if trace:
                    self.logger.debug(
                        'build_context NO incoming itinerary current/previous destinations are None')
                self.context['i'] = -1
                prev_dest = None
                tgt_dest = None

            # some will come from the configuration
            velocity_full_speed_mps = config['mower.velocity_full_speed_mps']
            self.context['v'] = velocity_full_speed_mps
            axle_track_m = config['mower.axle_track_m']
            self.context['w'] = axle_track_m
            n = config['mower.motion.set_rotation_speed_percent']
            self.context['n'] = n
            s = config['mower.motion.set_drive_speed_percent']
            self.context['s'] = s
            
            # some will come from telemetry - if available...
            try:
                num_sensors = len(config['mower.sens_factor_list'].split(','))
            except:
                num_sensors = 0
            if telem is not None and telem != {}:
                try:
                    cutter1_state = telem['cutter1']
                    cutter2_state = telem['cutter2']
                except Exception:
                    cutter1_state = cutter2_state = False
                self.context['cut1'] = int(cutter1_state)
                self.context['cut2'] = int(cutter2_state)
                try:
                    scaled_sensors = list(telem['sensors'].values())
                except Exception:
                    scaled_sensors = [-1] * num_sensors
                self.context['sens'] = scaled_sensors
            else:
                self.context['cut1'] = -1
                self.context['cut2'] = -1
                self.context['sens'] = [-1] * num_sensors
            
            # some will come from the current pose and might be undesirable numpy float types!
            if pose is not None:
                if trace:
                    self.logger.debug(
                        'build_context using incoming snapshot pose for current location')
                x = float(pose.arena.c_x_m)  # m
                y = float(pose.arena.c_y_m)  # m
                c = float(pose.arena.t_rad)
                rc = (c + pi) % (2 * pi)
            else:
                if trace:
                    self.logger.debug(
                        'build_context NO incoming snapshot pose for current location')
                x = y = c = rc = None
                tgt_dest = None  # force null navigation

            self.context['x'] = x
            self.context['y'] = y
            self.context['c'] = c
            self.context['rc'] = rc

            # some will come from the previous destination
            if prev_dest is not None:
                if trace:
                    self.logger.debug(
                        'build_context using previous destination for start location')
                x1 = prev_dest.target_x
                self.context['x1'] = x1
                y1 = prev_dest.target_y
                self.context['y1'] = y1

                # distance from source
                if x is not None and y is not None and x1 is not None and y1 is not None:
                    k = float(get_distance_between_points(x1, y1, x, y))
                else:
                    k = -1
                self.context['k'] = k

            else:
                if trace:
                    self.logger.debug(
                        'build_context NO previous destination for start location')
                self.context['x1'] = None
                self.context['y1'] = None
                self.context['k'] = -1

            # some will come from the destination
            if tgt_dest is not None:
                if trace:
                    self.logger.debug(
                        'build_context using target destination for end location')
                x2 = tgt_dest.target_x  # .x_m
                self.context['x2'] = x2
                y2 = tgt_dest.target_y  # .y_m
                self.context['y2'] = y2
                if tgt_dest.attitude is not None:
                    a2 = tgt_dest.attitude.name
                else:
                    a2 = Attitude.DEFAULT
                self.context['att2'] = a2

                # some will be calculations on base data
                # distance to target [d]
                if x is not None and y is not None and x2 is not None and y2 is not None:
                    if trace:
                        self.logger.debug(
                            'build_context using x, y..x2, y2 for path distance')
                    d = float(get_distance_between_points(x, y, x2, y2))
                else:
                    self.logger.debug('build_context NO path distance')
                    d = -1  # None
                self.context['d'] = d

                if trace:
                    trace_rules(
                        'build_context tgt_dest {0} d {1} c1 {2}'.format(tgt_dest, d, c))

                try:
                    lad = None
                    lax = lay = -1
                    lap = (lax, lay)
                    if 'lad' in self.context and self.context['lad'] is not None and self.context['lad'] > 0:
                        lad = self.context['lad']
                        # find look-ahead point using look-ahead distance
                        lap = geom_lib.line_circle_intersection(
                            x, y, x1, y1, x2, y2, min(d, lad))
                        lax, lay = lap[0], lap[1]
                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.warn('build_context look-ahead: ' +
                                     str(e) + ' on line ' + str(err_line))
                    if trace:
                        self.logger.debug(
                            'build_context no look ahead distance specified, defaulting to x2, y2 end of the path')
                self.context['lap'] = lap
                tgt_x = x2
                tgt_y = y2
                if lad is not None:
                    if trace:
                        self.logger.debug(
                            'build_context using angle between x,y and look ahead lax,lay for target heading')
                    c2 = get_angle_between_cartesian_points(x, y, lax, lay)
                    tgt_x, tgt_y = lax, lay
                elif d is not None and d > constants.CLOSE_TO_HOME_RADIUS_M:
                    if trace:
                        self.logger.debug(
                            'build_context using angle between x,y and x2,y2 for target heading')
                    c2 = get_angle_between_cartesian_points(x, y, x2, y2)
                else:
                    self.logger.debug(
                        'build_context too close to home - using current heading for target heading')
                    c2 = c
                self.context['c2'] = c2

                # delta heading[t], target - current
                t = c2 - c if c is not None and c2 is not None else 0
                self.context['t'] = t
                rt = c2 - rc if rc is not None and c2 is not None else 0
                self.context['rt'] = rt

                # shortest route angle [u]
                u = ((t + pi) % (2 * pi)) - pi
                self.context['u'] = u
                ru = ((rt + pi) % (2 * pi)) - pi
                self.context['ru'] = ru

                # absolute shortest route angle [u]
                a = abs(u)
                self.context['a'] = a
                ra = abs(ru)
                self.context['ra'] = ra

                # turn circle from current to destination
                # library function calculates the angle of arrival from the start and path angles
                if trace:
                    trace_rules('get_circle_from_world_points x: {:.3f} y: {:.3f} c: {:.0f} tgt_x: {:.3f} tgt_y: {:.3f}'.format(x, y, degrees(c), tgt_x, tgt_y))
                centre_x, centre_y, turn_circle_radius, arrival_angle, sector_angle, sector_portion = get_circle_from_world_points(
                    x, y, c, tgt_x, tgt_y)
                self.context['tcx'] = centre_x
                self.context['tcy'] = centre_y
                if trace:
                    trace_rules('get_circle_from_world_points: centre_x {0}, centre_y {1}, turn_circle_radius {2}, arrival_angle {3}, sector_angle {4}, sector_portion {5}'.format(
                        centre_x, centre_y, turn_circle_radius, arrival_angle, sector_angle, sector_portion))
                if centre_x is not None:
                    if trace:
                        self.logger.debug(
                            'build_context using calculated turn circle')
                    msg_tmplt = '\n  turn circle centre_x: {0:.2f}'
                    msg_tmplt += '\n  turn circle centre_y: {1:.2f}'
                    msg_tmplt += '\n  turn circle radius: {2:.2f}'
                    msg_tmplt += '\n  turn circle circumference: {3:.2f}'
                    msg_tmplt += '\n  arrival_angle: {4:.0f}'
                    msg_tmplt += '\n  sector_angle: {5:.0f}'
                    msg_tmplt += '\n  sector_portion: {6:.2f}'
                    msg_tmplt += '\n  angular distance: {7:.2f}\n'
                    msg = msg_tmplt.format(
                        centre_x,
                        centre_y,
                        turn_circle_radius,
                        2 * pi * turn_circle_radius if turn_circle_radius is not None else 0,
                        arrival_angle,
                        sector_angle,
                        sector_portion,
                        sector_portion * 2 * pi * turn_circle_radius if turn_circle_radius is not None else 0,
                    )
                    if trace:
                        trace_rules(msg)
                    f = sector_angle
                    self.context['f'] = f
                    g = sector_portion
                    self.context['g'] = g
                    velocity_ratio, arc_length = geom_lib.get_velocity_ratio(
                        axle_track_m,
                        turn_circle_radius,
                        sector_portion,
                        pragmatic=False,
                        debug=trace,
                        logger=self.logger
                    )

                    self.context['b'] = turn_circle_radius
                    self.context['j'] = velocity_ratio
                    self.context['l'] = arc_length  # arc length
                else:
                    if trace:
                        self.logger.debug(
                            'build_context NO calculated turn circle')
                    self.context['f'] = 0
                    self.context['g'] = 0
                    self.context['b'] = 0
                    self.context['j'] = 1  # velocity ratio is 1
                    self.context['l'] = d
            else:
                if trace:
                    self.logger.debug(
                        'build_context NO target destination for end location')
                self.context['x2'] = None
                self.context['y2'] = None
                self.context['c2'] = None
                self.context['tcx'] = None
                self.context['tcy'] = None
                self.context['att2'] = ''
                self.context['d'] = -1
                self.context['k'] = -1
                self.context['t'] = 0
                self.context['u'] = 0
                self.context['a'] = 0
                self.context['rt'] = 0
                self.context['ru'] = 0
                self.context['ra'] = 0
                self.context['b'] = -1
                self.context['f'] = 0
                self.context['g'] = 0
                self.context['j'] = 1.0
                self.context['l'] = -1
                self.context['lap'] = (-1, -1)

            # context needs to include user-defined expressions
            hyb_terms = [
                term for term in self.terms if term.__class__.__name__ == 'Hybrid']
            ud_terms = [
                term for term in self.terms if term.__class__.__name__ == 'Term']
            # ensure hybrids precede user-defined, so annotations based on hybrids work!
            for ud_term in hyb_terms + ud_terms:
                if ud_term.expression is not None and ud_term.expression != '':
                    try:
                        ud_result = eval(str(ud_term.expression),
                                         self.context, self.safe_functions)
                    except Exception as e:
                        err_line = sys.exc_info()[-1].tb_lineno
                        if 'NoneType' not in str(e):
                            self.logger.error(
                                'Error parsing user-defined term: ' + 
                                str(ud_term.expression) + 
                                ' on line ' + str(err_line) + 
                                ' => ' + str(e)
                            )
                        ud_result = -1  # None
                    try:
                        # convert to native Python types
                        ud_result = ud_result.item()
                    except Exception:
                        pass
                    self.context[ud_term.name] = ud_result
                else:
                    self.context[ud_term.name] = None

            # finally update values for terms
            for term in self.terms:
                term_val = self.context[term.name] if term.name in self.context else None
                if term_val is not None:
                    try:
                        # round display values - not context values
                        term.result = round(term_val, 2)
                    except Exception:
                        term.result = term_val  # may not be numeric
                    try:
                        # convert to native Python types
                        term.result = term.result.item()
                    except Exception:
                        pass
                else:
                    # de-None display values AND context values
                    term.result = -1  # ''

                alt_val = None
                if term.alt_units is not None:
                    if term_val is not None:
                        if term.alt_units == 'degrees':
                            alt_val = degrees(term_val)
                        elif term.alt_units == 'radians':
                            alt_val = radians(term_val)
                        else:
                            alt_val = None
                        if alt_val is not None:
                            # round display values - not context values
                            term.alt_result = round(alt_val, 2)
                        else:
                            term.alt_result = -1  # ''
                        try:
                            # convert to native Python types
                            term.alt_result = term.alt_result.item()
                        except Exception:
                            pass
                    else:
                        # de-None display values - not context values
                        term.alt_result = -1
                else:
                    term.alt_units = ''

                if trace:
                    if type(term.result) is tuple:
                        term_typestring = list(map(type, term.result))
                    else:
                        term_typestring = type(term.result)
                    msg = '{0} [{1}] = {2} {3} {4}'.format(
                        term.name, term.description, term.result, term.units, term_typestring)
                    if alt_val is not None:
                        msg += ' ' + str(alt_val) + ' ' + term.alt_units
                    trace_rules(msg)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error(
                'Error in RulesEngine build_context: ' + str(e) + ' on line ' + str(err_line))

    def select(self, scope=RuleScope.ANY, trace=False):
        '''
            select the first executable rule in priority order (as pre-sorted)
            default scope is ANY - so all enabled rules
        '''
        selected_rule = None
        try:
            r = 0
            while r < len(self.rules):
                rule = self.rules[r]
                if rule.in_scope(scope):
                    msg = 'Select checking rule: {0} {1} priority: {2} scope: {3}...'.format(
                        r, rule.name, rule.priority, rule.scope)
                    if trace:
                        trace_rules(msg)
                    if selected_rule is None:
                        rule.check(self.context, self.safe_functions,
                                   self.terms_units, trace=trace)  # trace
                        if rule.condition_state:
                            selected_rule = rule
                            rule.parse(self.context, self.safe_functions, 
                                       self.terms_units, trace=trace)
                            if trace:
                                trace_rules(
                                    'Select selected rule: ' + rule.name)
                            break
                r += 1

            # clear down other rules
            for rule in self.rules:
                if selected_rule is not None and rule is not selected_rule:
                    rule.cleardown()
                    msg = 'Select cleared down rule: {}'.format(rule.name)
                    if trace:
                        trace_rules(msg)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error('Error in RulesEngine.select: ' +
                              str(e) + ' on line ' + str(err_line))

        return selected_rule

    def parse(self, rule, trace=False):
        '''
            just parse the supplied rule using our context and safe functions
        '''
        rule.parse(self.context, self.safe_functions, self.terms_units, trace=trace)
