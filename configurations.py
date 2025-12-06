import yaml
import json
import os
import sys
from pathlib import Path
import time
import importlib.util
import lxml.etree as ET
from math import pi, acos
import copy
from threading import Thread, Timer
import numpy as np
import logging

import constants
from vis_lib import matrices_from_quad_points
from utilities import route_pc_to_metres
from pxm_exceptions import *  # @UnusedWildImport
from forms.morphable import Morphable
from forms.rule import Rule
from forms.term import Term
from forms.hybrid import Hybrid
from forms.systerm import Systerm
from forms.point import Point


class Config():
    '''
        class representing the system configuration
    '''
    SAVE_INIT_DELAY_SECS = 3
    SAVE_PERIOD_SECS = 10
    PROFILED_MEASURES = True

    def __init__(self, settings_file_path, config_file_path, dump=True, readonly=False, debug=False, callback=None):
        '''
            Constructor
        '''
        self.logger = logging.getLogger('pxm')
        self.database = {}
        self.settings_file_path = settings_file_path
        self.cfg_file_path = config_file_path
        self.readonly = readonly
        self.debug = debug
        self.callback = callback
        self.prev_profile = None
        self.prev_mower = None
        self.load()
        self.parse()

        # print it to confirm
        if dump and debug:
            print(self)

        self.execute_save = False
        if self.SAVE_PERIOD_SECS > 0:
            self.save_thread = Thread(target=self.do_save)
            self.save_thread.setDaemon(True)
            self.save_thread.start()

    def do_save(self):

        # save loop
        while True:
            if self.execute_save and not self.readonly:
                self.logger.debug('Saving config...')
                self.save_config()
                with open(self.settings_file_path, 'w') as outfile:
                    yaml.dump(self.settings, outfile, default_flow_style=False)
                self.execute_save = False
                self.logger.info('Config completed save')
            time.sleep(self.SAVE_PERIOD_SECS)

    def schedule_save(self):
        self.execute_save = True

    def load(self):

        parser = ET.XMLParser(strip_cdata=False)
        if self.settings_file_path is not None:
            self.settings = yaml.safe_load(open(self.settings_file_path))

        if self.cfg_file_path is not None:
            cfg_tree = ET.parse(self.cfg_file_path, parser)
            self.cfg_tree = cfg_tree
            self.cfg_root = cfg_tree.getroot()

    def parse(self):
        '''
        Parse xml into dictionary database
        '''
        try:
            profiles_xpath = "profiles/profile"
            profile_nodes = self.cfg_root.findall(profiles_xpath)
            profiles = [node.attrib['name'] for node in profile_nodes]
            self.database['profiles'] = profiles

            req_profile = self.settings['profile']
            if req_profile in profiles:
                cur_profile = req_profile
            elif len(profiles) > 0:
                cur_profile = profiles[0]
                self.logger.debug('Config parse - requested profile unavailable, using first: {}'.format(cur_profile))
            else:
                self.logger.debug('Config parse - no profiles available')
                cur_profile = None
            self.logger.debug('Config parse - current profile: ' + cur_profile)
            self.database['current.profile'] = cur_profile
            profile_xpath = "./profiles/profile[@name='{0}']".format(
                cur_profile)
            profile_node = self.cfg_root.find(profile_xpath)
            self.cur_profile_node = profile_node

            try:
                db_conn_node = profile_node.find('connection')
                self.database['dbconn.host'] = db_conn_node.attrib['host']
                self.database['dbconn.port'] = int(db_conn_node.attrib['port'])
                self.database['dbconn.db'] = db_conn_node.attrib['database']
                self.database['dbconn.user'] = db_conn_node.attrib['user']
                self.database['dbconn.password'] = db_conn_node.attrib['password']
            except Exception:
                pass  # optional

            mowers_xpath = "mowers/mower"
            mower_nodes = self.cfg_root.findall(mowers_xpath)
            mowers = [node.attrib['name'] for node in mower_nodes]
            self.database['mowers'] = mowers

            cur_mower = self.settings['mower']
            self.database['current.mower'] = cur_mower

            strategies_xpath = "navigation_strategies/strategy"
            strategy_nodes = self.cfg_root.findall(strategies_xpath)
            strategies = [node.attrib['name'] for node in strategy_nodes]
            self.database['strategies'] = strategies

            pairings_xpath = "pairings/pairing"
            pairings_nodes = self.cfg_root.findall(pairings_xpath)
            pairings = [node.attrib['profile'] + '+' +
                               node.attrib['mower'] for node in pairings_nodes]
            self.database['pairings'] = pairings

            # Mowing Patterns from Plug-ins
            cur_script_fldr = Path(__file__).parent
            rel_patt_path = 'patterns'
            abs_patt_path = (cur_script_fldr / rel_patt_path).resolve()
            self.logger.info(
                'absolute patterns path: {0}'.format(abs_patt_path))
            patt_names_0 = [os.path.basename(x)[0:-3]
                            for x in abs_patt_path.glob('*.py')]
            patt_names = [' '.join(word.title() for word in patt_name.split(
                '_')) for patt_name in patt_names_0]
            patt_names.remove('Template')
            self.database['patterns'] = patt_names

            # determine navigation strategy and mowing pattern from pairing?
            if cur_profile != self.prev_profile or cur_mower != self.prev_mower:
                self.logger.info(
                    'profile/mower changed - use pairings') 
                pairing_xpath_tmplt = "pairings/pairing[@mower='{0}' and @profile='{1}']"
                pairing_nodes = self.cfg_root.xpath(
                    pairing_xpath_tmplt.format(cur_mower, cur_profile))
                if len(pairing_nodes) > 0:
                    pairing_name = pairing_nodes[0].attrib['name']
                    cur_strategy = pairing_nodes[0].attrib['strategy']
                    self.logger.info('{} pairing - requested strategy for {} and {}: {}'.format(
                        pairing_name, cur_mower, cur_profile, cur_strategy))
                    cur_pattern = pairing_nodes[0].attrib['pattern']
                    self.logger.info('{} pairing - requested pattern for {} and {}: {}'.format(
                        pairing_name, cur_mower, cur_profile, cur_pattern))
                else:
                    # determine navigation strategy from profile with any mower
                    pairing_xpath = pairing_xpath_tmplt.format(
                        '*', cur_profile)
                    pairing_nodes = self.cfg_root.xpath(pairing_xpath)
                    if len(pairing_nodes) > 0:
                        pairing_name = pairing_nodes[0].attrib['name']
                        cur_strategy = pairing_nodes[0].attrib['strategy']
                        self.logger.info('{} pairing - strategy for any mower on profile {}: {}'.format(
                            pairing_name, cur_profile, cur_strategy))
                        cur_pattern = pairing_nodes[0].attrib['pattern']
                        self.logger.info('{} pairing - pattern for any mower on profile {}: {}'.format(
                            pairing_name, cur_mower, cur_pattern))
                    else:
                        # determine navigation strategy from mower with any profile
                        pairing_xpath = pairing_xpath_tmplt.format(
                            cur_mower, '*')
                        pairing_nodes = self.cfg_root.xpath(
                            pairing_xpath)
                        if len(pairing_nodes) > 0:
                            pairing_name = pairing_nodes[0].attrib['name']
                            cur_strategy = pairing_nodes[0].attrib['strategy']
                            self.logger.info('{} pairing - strategy for mower {} on any profile: {}'.format(
                                pairing_name, cur_mower, cur_strategy))
                            cur_pattern = pairing_nodes[0].attrib['pattern']
                            self.logger.info('{} pairing - pattern for mower {} on any profile: {}'.format(
                                pairing_name, cur_mower, cur_pattern))
                        else:
                            # no pairing defined for this mower/profile combination
                            # favour 'Rotate and Veer' strategy, if available
                            strategy_xpath = "./navigation_strategies/strategy[contains(@name, 'Rotate and Veer')]"
                            strategy_nodes = self.cfg_root.xpath(strategy_xpath)
                            if len(strategy_nodes) > 0:
                                first_strategy_node = strategy_nodes[0]
                            else:
                                # select first strategy
                                strategy_xpath = "./navigation_strategies/strategy"
                                strategy_nodes = self.cfg_root.xpath(strategy_xpath)
                                if len(strategy_nodes) > 0:
                                    first_strategy_node = strategy_nodes[0]
                            if first_strategy_node is not None:
                                cur_strategy = first_strategy_node.attrib['name']
                                self.logger.info(
                                    'strategy defaulting to first: {0}'.format(cur_strategy))
                            else:
                                cur_strategy = None
                                raise BaseException(
                                    'No Navigation Strategies Defined')
                            # move 'Fence' pattern to top of list, if available
                            try:
                                patt_names.insert(0, patt_names.pop(patt_names.index('Fence')))
                            except:
                                pass
                            # select first pattern
                            if len(patt_names) > 0:
                                first_pattern = patt_names[0]
                                cur_pattern = first_pattern
                                self.logger.info(
                                    'pattern defaulting to first: {0}'.format(cur_pattern))
                            else:
                                cur_pattern = None
                                raise BaseException('No Mowing Patterns Defined')

                # validate requested strategy and pattern
                if cur_strategy not in strategies:
                    force_strat = None
                    self.logger.warning(
                        'Invalid strategy referenced in \'{}\' pairing: [{}] - defaulting to first: [{}]'.format(
                            pairing_name, cur_strategy, force_strat
                        )
                    )                
                    cur_strategy = force_strat
                if cur_pattern not in patt_names:
                    force_pattern = None
                    self.logger.warning(
                        'Invalid pattern referenced in \'{}\' pairing: [{}] - defaulting to first: [{}]'.format(
                            pairing_name, cur_pattern, force_pattern
                        )
                    )                
                    cur_pattern = force_pattern

                self.settings['strategy'] = cur_strategy 
                self.settings['pattern'] = cur_pattern 
                self.prev_profile = cur_profile
                self.prev_mower = cur_mower
            else:
                self.logger.info(
                    'profile/mower unchanged - skip pairings')
                cur_strategy = self.settings['strategy']
                cur_pattern = self.settings['pattern']
            self.database['current.strategy'] = cur_strategy
            self.database['current.pattern'] = cur_pattern
            if 'excursion' in self.settings and self.settings['excursion'] is not None:
                self.database['current.excursion'] = int(
                    self.settings['excursion'])
            else:
                self.database['current.excursion'] = 1
            strategy_xpath = "./navigation_strategies/strategy[@name='{0}']".format(
                cur_strategy)
            strategy_node = self.cfg_root.find(strategy_xpath)
            self.cur_strategy_node = strategy_node

            last_visited_route_node = self.settings['last_visited_route_node']
            self.database['current.last_visited_route_node'] = last_visited_route_node

            mower_xpath = "./mowers/mower[@name='{0}']".format(cur_mower)
            mower_node = self.cfg_root.find(mower_xpath)
            self.cur_mower_node = mower_node
            if mower_node is not None:
                identity_node = mower_node.find('identity')
                dimensions_node = mower_node.find('dimensions')
                motion_node = mower_node.find('motion')
                sensors_node = mower_node.find('sensors')
                self.database['mower.ip'] = identity_node.attrib['ip']
                self.database['mower.port'] = int(identity_node.attrib['port'])
                self.database['mower.type'] = identity_node.attrib['type']

                axle_track_m = float(motion_node.attrib['axle_track_m'])
                # m - the distance between wheels (from centre-to-centre along the length of the axle)
                self.database['mower.axle_track_m'] = axle_track_m
                # length metres - the diameter of wheel
                wheel_dia_m = float(motion_node.attrib['wheel_dia_m'])
                self.database['mower.wheel_dia_m'] = wheel_dia_m
                # [unit * length] = length circumference = pi * diameter
                wheel_circum_m = pi * wheel_dia_m
                self.database['mower.wheel_circum_m'] = wheel_circum_m
                motor_full_speed_rpm = float(
                    motion_node.attrib['motor_full_speed_rpm'])  # [unit / time]
                self.database['mower.motor_full_speed_rpm'] = motor_full_speed_rpm
                # [unit / time] / [unit] = [unit / time] revolutions per second from rpm
                motor_full_speed_rps = motor_full_speed_rpm / 60
                self.database['mower.motor_full_speed_rps'] = motor_full_speed_rps
                # metres[m] * revolutions[units] / second[s] => metres per second [m/s]
                velocity_full_speed_mps = wheel_circum_m * motor_full_speed_rps
                self.database['mower.velocity_full_speed_mps'] = velocity_full_speed_mps
                cutter1_dia_m = float(dimensions_node.attrib['cutter1_dia_m'])
                cutter2_dia_m = float(dimensions_node.attrib['cutter2_dia_m'])
                self.database['mower.dimensions.cutter1_dia_m'] = cutter1_dia_m
                self.database['mower.dimensions.cutter2_dia_m'] = cutter2_dia_m
                if cutter2_dia_m > 0:
                    cutter_dia_m = np.mean([cutter1_dia_m, cutter2_dia_m])
                else:
                    cutter_dia_m = cutter1_dia_m
                self.database['mower.dimensions.cutter_dia_m'] = cutter_dia_m
                self.database['mower.motion.set_rotation_speed_percent'] = int(
                    motion_node.attrib['set_rotation_speed_percent'])
                self.database['mower.motion.set_drive_speed_percent'] = int(
                    motion_node.attrib['set_drive_speed_percent'])
                # sensors
                self.database['mower.sens_name_list'] = sensors_node.attrib['name_list']
                self.database['mower.sens_factor_list'] = sensors_node.attrib['factor_list']

                # body dimensions
                body_width_m = float(dimensions_node.attrib['body_width_m'])
                self.database['mower.body_width_m'] = body_width_m
                body_length_m = float(dimensions_node.attrib['body_length_m'])
                self.database['mower.body_length_m'] = body_length_m

                # triangular target dimensions
                target_width_m = float(
                    dimensions_node.attrib['target_width_m'])
                self.database['mower.target_width_m'] = target_width_m
                target_length_m = float(
                    dimensions_node.attrib['target_length_m'])
                self.database['mower.target_length_m'] = target_length_m
                target_radius_m = float(
                    dimensions_node.attrib['target_radius_m'])
                self.database['mower.target_radius_m'] = target_radius_m
                target_offset_pc = int(
                    dimensions_node.attrib['target_offset_pc'])
                self.database['mower.target_offset_pc'] = target_offset_pc

                # calculate length of equal sides
                leg_length_m = float(
                    np.hypot((target_width_m / 2), target_length_m))  # isosceles
                self.database['mower.leg_length_m'] = leg_length_m

                # calculate target area m2
                target_area_m2 = 0.5 * target_width_m * target_length_m
                self.database['mower.target_area_m2'] = target_area_m2

                # target angles
                base_angle = acos(
                    1 - (target_width_m**2 / (2 * leg_length_m**2)))
                vertex_angle = (pi - base_angle) / 2
                self.database['mower.base_angle_rad'] = base_angle
                self.database['mower.vertex_angle_rad'] = vertex_angle

                # target ratio
                target_isos_ratio = target_width_m / leg_length_m
                self.database['mower.isos_ratio'] = target_isos_ratio

            else:
                self.database['mower.dimensions.cutter1_dia_m'] = 0
                self.database['mower.dimensions.cutter2_dia_m'] = 0
                self.database['mower.dimensions.cutter_dia_m'] = cutter_dia_m = 0
                self.database['mower.ip'] = None
                self.database['mower.port'] = None
                self.database['mower.type'] = None
                self.database['mower.body_width_m'] = body_width_m = 0
                self.database['mower.body_length_m'] = body_length_m = 0
                self.database['mower.leg_length_m'] = leg_length_m = 0
                self.database['mower.target_area_m2'] = 0
                self.database['mower.target_width_m'] = target_width_m = 0
                self.database['mower.target_length_m'] = target_length_m = 0
                self.database['mower.target_radius_m'] = target_radius_m = 0
                self.database['mower.motion.set_rotation_speed_percent'] = 0
                self.database['mower.motion.set_drive_speed_percent'] = 0
                self.database['mower.velocity_full_speed_mps'] = 0
                self.database['mower.axle_track_m'] = 0

            # lawn dimensions
            lawn_node = profile_node.find('lawn')
            self.cur_lawn_node = lawn_node
            lawn_width_m = float(lawn_node.attrib["width_m"])
            self.database['lawn.width_m'] = lawn_width_m
            lawn_length_m = float(lawn_node.attrib["length_m"])
            self.database['lawn.length_m'] = lawn_length_m
            lawn_border_m = float(lawn_node.attrib["border_m"])
            self.database['lawn.border_m'] = lawn_border_m

            dev_node = profile_node.find("device")
            self.cur_dev_node = dev_node
            dev_chan_attr = dev_node.attrib["channel"]
            self.database['device.channel'] = dev_chan_attr if dev_chan_attr is not None and dev_chan_attr != 'None' else None
            dev_index_attr = dev_node.attrib["index"]
            self.database['device.index'] = dev_index_attr if dev_index_attr is not None and dev_index_attr != 'None' else None
            dev_endpoint_attr = dev_node.attrib["endpoint"] if 'endpoint' in dev_node.attrib else None
            self.database['device.endpoint'] = dev_endpoint_attr if dev_endpoint_attr is not None and dev_endpoint_attr != 'None' else None

            # camera optical properties

            # polymorphic camera optical properties
            opt_node = dev_node[0]  # first and only child
            self.cur_opt_node = opt_node
            disp_col_attr = opt_node.attrib["display_colour"]
            self.database['optical.display_colour'] = disp_col_attr is not None and disp_col_attr == 'True'
            res_attr = opt_node.attrib["resolution"]
            res = res_attr if res_attr is not None and res_attr != 'None' else 'x'.join(
                map(str, self.RESOLUTIONS[-1]))
            device_width = int(res.split('x')[0])
            device_height = int(res.split('x')[1])
            display_width = min(
                constants.CAPPED_IMAGE_RESOLUTION[0], device_width)
            display_height = min(
                constants.CAPPED_IMAGE_RESOLUTION[1], device_height)

            self.database['optical.resolution'] = res  # res_mode
            self.database['optical.width'] = device_width
            self.database['optical.height'] = device_height
            self.database['optical.display_width'] = display_width
            self.database['optical.display_height'] = display_height
            self.database['optical.analysis_display_ratio'] = device_width / display_width

            awb_attr = opt_node.attrib["awb_mode"] if 'awb_mode' in opt_node.attrib else None
            self.database['optical.awb_mode'] = awb_attr
            redgain_attr = opt_node.attrib["redgain"] if 'redgain' in opt_node.attrib else None
            self.database['optical.redgain'] = float(
                redgain_attr) if redgain_attr is not None and redgain_attr != 'None' else None
            bluegain_attr = opt_node.attrib["bluegain"] if 'bluegain' in opt_node.attrib else None
            self.database['optical.bluegain'] = float(
                bluegain_attr) if bluegain_attr is not None and bluegain_attr != 'None' else None
            h_flip_attr = opt_node.attrib["hflip"] if 'hflip' in opt_node.attrib else None
            self.database['optical.hflip'] = h_flip_attr is not None and h_flip_attr == 'True'
            v_flip_attr = opt_node.attrib["vflip"] if 'vflip' in opt_node.attrib else None
            self.database['optical.vflip'] = v_flip_attr is not None and v_flip_attr == 'True'
            ann_attr = opt_node.attrib["annotate"]
            self.database['optical.annotate'] = ann_attr is not None and ann_attr == 'True'

            undistort_strength_attr = opt_node.attrib[
                "undistort_strength"] if 'undistort_strength' in opt_node.attrib else None
            self.database['optical.undistort_strength'] = float(
                undistort_strength_attr) if undistort_strength_attr is not None and undistort_strength_attr != 'None' else 0.0

            undistort_zoom_attr = opt_node.attrib["undistort_zoom"] if 'undistort_zoom' in opt_node.attrib else None
            self.database['optical.undistort_zoom'] = float(
                undistort_zoom_attr) if undistort_zoom_attr is not None and undistort_zoom_attr != 'None' else 0.0

            hotspot_xpath = "./hotspot"
            hotspot_node = profile_node.find(hotspot_xpath)
            self.cur_hotspot_node = hotspot_node
            hotspot_name_attr = hotspot_node.attrib["name"]
            hotspot_name = hotspot_name_attr if hotspot_name_attr is not None and hotspot_name_attr != 'None' else None
            self.database['hotspot.name'] = hotspot_name

            try:
                if self.PROFILED_MEASURES:
                    scaled_measures_node = profile_node.find("measures/scaled_measures")
                    setpoint_measures_node = profile_node.find("measures/setpoint_measures")
                else:
                    scaled_measures_node = self.cfg_root.find("measures/scaled_measures")
                    setpoint_measures_node = self.cfg_root.find("measures/setpoint_measures")
                span_node = scaled_measures_node.xpath(
                    "scaled[@name='span']")[0]
                span_lower_attr = span_node.attrib["lower"]
                span_lower = float(
                    span_lower_attr) if span_lower_attr is not None and span_lower_attr != 'None' else None
                span_scale_attr = span_node.attrib["scale"]
                span_scale = float(
                    span_scale_attr) if span_scale_attr is not None and span_scale_attr != 'None' else None
                span_upper_attr = span_node.attrib["upper"]
                span_upper = float(
                    span_upper_attr) if span_upper_attr is not None and span_upper_attr != 'None' else None
                span_maxscore_attr = span_node.attrib["maxscore"]
                span_maxscore = int(
                    span_maxscore_attr) if span_maxscore_attr is not None and span_maxscore_attr != 'None' else None
                area_node = scaled_measures_node.xpath(
                    "scaled[@name='area']")[0]
                area_lower_attr = area_node.attrib["lower"]
                area_lower = float(
                    area_lower_attr) if area_lower_attr is not None and area_lower_attr != 'None' else None
                area_scale_attr = area_node.attrib["scale"]
                area_scale = float(
                    area_scale_attr) if area_scale_attr is not None and area_scale_attr != 'None' else None
                area_upper_attr = area_node.attrib["upper"]
                area_upper = float(
                    area_upper_attr) if area_upper_attr is not None and area_upper_attr != 'None' else None
                area_maxscore_attr = area_node.attrib["maxscore"]
                area_maxscore = int(
                    area_maxscore_attr) if area_maxscore_attr is not None and area_maxscore_attr != 'None' else None
                isos_node = setpoint_measures_node.xpath(
                    "setpoint[@name='isoscelicity']")[0]
                isos_lower_attr = isos_node.attrib["lower"]
                isos_lower = float(
                    isos_lower_attr) if isos_lower_attr is not None and isos_lower_attr != 'None' else None
                isos_setpoint_attr = isos_node.attrib["setpoint"]
                isos_setpoint = float(
                    isos_setpoint_attr) if isos_setpoint_attr is not None and isos_setpoint_attr != 'None' else None
                isos_upper_attr = isos_node.attrib["upper"]
                isos_upper = float(
                    isos_upper_attr) if isos_upper_attr is not None and isos_upper_attr != 'None' else None
                isos_maxscore_attr = isos_node.attrib["maxscore"]
                isos_maxscore = int(
                    isos_maxscore_attr) if isos_maxscore_attr is not None and isos_maxscore_attr != 'None' else None
                solid_node = setpoint_measures_node.xpath(
                    "setpoint[@name='solidity']")[0]
                solid_lower_attr = solid_node.attrib["lower"]
                solid_lower = float(
                    solid_lower_attr) if solid_lower_attr is not None and solid_lower_attr != 'None' else None
                solid_setpoint_attr = solid_node.attrib["setpoint"]
                solid_setpoint = float(
                    solid_setpoint_attr) if solid_setpoint_attr is not None and solid_setpoint_attr != 'None' else None
                solid_upper_attr = solid_node.attrib["upper"]
                solid_upper = float(
                    solid_upper_attr) if solid_upper_attr is not None and solid_upper_attr != 'None' else None
                solid_maxscore_attr = solid_node.attrib["maxscore"]
                solid_maxscore = int(
                    solid_maxscore_attr) if solid_maxscore_attr is not None and solid_maxscore_attr != 'None' else None
                fitness_node = setpoint_measures_node.xpath(
                    "setpoint[@name='fitness']")[0]
                fitness_lower_attr = fitness_node.attrib["lower"]
                fitness_lower = float(
                    fitness_lower_attr) if fitness_lower_attr is not None and fitness_lower_attr != 'None' else None
                fitness_setpoint_attr = fitness_node.attrib["setpoint"]
                fitness_setpoint = float(
                    fitness_setpoint_attr) if fitness_setpoint_attr is not None and fitness_setpoint_attr != 'None' else None
                fitness_upper_attr = fitness_node.attrib["upper"]
                fitness_upper = float(
                    fitness_upper_attr) if fitness_upper_attr is not None and fitness_upper_attr != 'None' else None
                fitness_maxscore_attr = fitness_node.attrib["maxscore"]
                fitness_maxscore = int(
                    fitness_maxscore_attr) if fitness_maxscore_attr is not None and fitness_maxscore_attr != 'None' else None

                self.database['span.lower'] = span_lower
                self.database['span.scale'] = span_scale
                self.database['span.upper'] = span_upper
                self.database['span.maxscore'] = span_maxscore

                self.database['area.lower'] = area_lower
                self.database['area.scale'] = area_scale
                self.database['area.upper'] = area_upper
                self.database['area.maxscore'] = area_maxscore

                self.database['isoscelicity.lower'] = isos_lower
                self.database['isoscelicity.setpoint'] = isos_setpoint
                self.database['isoscelicity.upper'] = isos_upper
                self.database['isoscelicity.maxscore'] = isos_maxscore

                self.database['solidity.lower'] = solid_lower
                self.database['solidity.setpoint'] = solid_setpoint
                self.database['solidity.upper'] = solid_upper
                self.database['solidity.maxscore'] = solid_maxscore

                self.database['fitness.lower'] = fitness_lower
                self.database['fitness.setpoint'] = fitness_setpoint
                self.database['fitness.upper'] = fitness_upper
                self.database['fitness.maxscore'] = fitness_maxscore

            except Exception:
                pass
            '''
                system is cartesian y ascending up
                orientation is Clockwise from Bottom-Left:
                1      2
                0      3
            '''
            self.cur_calib_node = lawn_node.find('calib')
            # calibration width and length
            # default to lawn dimensions if no calibration dimensions
            calib_width_att = self.cur_calib_node.attrib[
                'width_m'] if 'width_m' in self.cur_calib_node.attrib else None
            if calib_width_att is not None:
                calib_width_m = float(calib_width_att)
            else:
                calib_width_m = lawn_width_m
            self.database['calib.width_m'] = calib_width_m

            calib_length_att = self.cur_calib_node.attrib[
                'length_m'] if 'length_m' in self.cur_calib_node.attrib else None
            if calib_length_att is not None:
                calib_length_m = float(calib_length_att)
            else:
                calib_length_m = lawn_length_m
            self.database['calib.length_m'] = calib_length_m

            calib_offx_att = self.cur_calib_node.attrib[
                'offset_x_m'] if 'offset_x_m' in self.cur_calib_node.attrib else None
            if calib_offx_att is not None:
                calib_offset_x_m = float(calib_offx_att)
            else:
                calib_offset_x_m = 0.0
            self.database['calib.offset_x_m'] = calib_offset_x_m

            calib_offy_att = self.cur_calib_node.attrib[
                'offset_y_m'] if 'offset_y_m' in self.cur_calib_node.attrib else None
            if calib_offy_att is not None:
                calib_offset_y_m = float(calib_offy_att)
            else:
                calib_offset_y_m = 0.0
            self.database['calib.offset_y_m'] = calib_offset_y_m

            calib_xpath = "./calib/point"
            calib_pts = lawn_node.findall(calib_xpath)
            calib_percent_points = []
            src_pts_pc = []
            for pt in calib_pts:
                i = int(pt.attrib["index"])
                ptX_percent = float(pt.attrib["x"])
                ptY_percent = float(pt.attrib["y"])
                calib_percent_points.append(Point(i, ptX_percent, ptY_percent))
                src_pts_pc.append([ptX_percent, ptY_percent])
            self.database['lawn.calib'] = calib_percent_points

            self.cur_fence_node = lawn_node.find('fence')
            fence_xpath = "./fence/point"
            fence_pts = lawn_node.findall(fence_xpath)
            fence_points = []

            # de-duplicate fence points
            pt_keys = []
            for pt in fence_pts:
                i = int(pt.attrib["index"])
                ptX_percent = float(pt.attrib["x"])
                ptY_percent = float(pt.attrib["y"])
                pt_key = str(ptX_percent) + '|' + str(ptY_percent)
                if pt_key not in pt_keys:
                    pt_keys.append(pt_key)
                    fence_points.append(Point(i, ptX_percent, ptY_percent))

            # sort points in-place by _index
            fence_points.sort(key=lambda p: p.index)

            self.database['lawn.fence'] = fence_points

            arena_width_m = lawn_width_m + (2 * lawn_border_m)
            arena_length_m = lawn_length_m + (2 * lawn_border_m)
            self.database['arena.width_m'] = arena_width_m
            self.database['arena.length_m'] = arena_length_m
            arena_x_scale = device_width / (arena_width_m * 1000)
            arena_y_scale = device_height / (arena_length_m * 1000)
            self.database['arena.x_scale_px_per_mm'] = arena_x_scale
            self.database['arena.y_scale_px_per_mm'] = arena_y_scale

            # scale factor for cutter, etc.
            min_scale_factor = min(arena_x_scale, arena_y_scale)

            # M maps raw image to the top-down arena image (lawn + border)
            # N the inverse of M
            # L maps raw image pixel coordinates to world arena metres (cartesian)
            # K the inverse of L
            calib_pc_points = [[p.x, p.y] for p in calib_percent_points]
            self.logger.debug('matrices from quad points for location')
            M, _N, L, _K = matrices_from_quad_points(
                calib_pc_points,
                calib_width_m,
                calib_length_m,
                calib_offset_x_m,
                calib_offset_y_m,
                lawn_width_m,
                lawn_length_m,
                lawn_border_m,
                device_height,
                device_width,
                logger=self.logger,
                debug=self.debug
            )
            self.logger.debug('matrices from quad points for display')
            _DM, DN, _DL, DK = matrices_from_quad_points(
                calib_pc_points,
                calib_width_m,
                calib_length_m,
                calib_offset_x_m,
                calib_offset_y_m,
                lawn_width_m,
                lawn_length_m,
                lawn_border_m,
                display_height,
                display_width,
                logger=self.logger,
                debug=self.debug
            )
            arena_matrix_javascript = [[float(j) for j in i] for i in L]
            self.database['calib.img_matrix_inv'] = M
            self.database['calib.img_matrix'] = DN
            self.database['calib.arena_matrix'] = L
            self.database['calib.arena_matrix_inv'] = DK
            self.database['calib.arena_matrix_js'] = arena_matrix_javascript

            # calculate fence
            fence_m = []
            for pt in fence_points:
                x_m = round((pt.x * arena_width_m / 100), 3)
                y_m = round((pt.y * arena_length_m / 100), 3)
                fence_m.append((x_m, y_m, None))
            self.database['lawn.fence.metres'] = fence_m

            # calculate route?
            if (cutter_dia_m is not None and 
                cur_pattern is not None and 
                cur_pattern != 'None'):

                # from Current Pattern Name - obtain module_name
                rel_pat_mod_name = cur_pattern.replace(' ', '_').lower()
                try:
                    file_path = os.path.join(
                        abs_patt_path, rel_pat_mod_name) + '.py'
                    module_name = rel_pat_mod_name
                    spec = importlib.util.spec_from_file_location(
                        module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                except Exception as e1:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.error(
                        'Config Parse Error loading pattern plug-in: ' + str(e1) + ' on line ' + str(err_line))

                pattern_logger = logging.getLogger('mow-patterns')

                route_pc = module.calculate_route(
                    fence_points, arena_width_m, arena_length_m, cutter_dia_m, pattern_logger)
                route_m = route_pc_to_metres(
                    arena_width_m, arena_length_m, route_pc, min_internode_dist_m=constants.MINIMUM_INTER_NODE_DISTANCE_M)
            else:
                route_m = []
                route_pc = []
            self.database['lawn.route'] = route_m
            self.database['lawn.route_pc'] = route_pc

            # calculate cutter width in pixels
            self.database['mower.dimensions.cutter_dia_px'] = int(
                cutter_dia_m * min_scale_factor * 1000)

            # calculate arena body area in pixels squared
            arena_centre_x_m = arena_width_m / 2
            arena_centre_y_m = arena_length_m / 2
            # v1 is bottom-left, v2 is bottom-right, v3 is tip
            arena_vertices_m = [(arena_centre_x_m, arena_centre_y_m),
                                (arena_centre_x_m + (body_width_m), arena_centre_y_m),
                                (arena_centre_x_m + (body_width_m / 2), arena_centre_y_m + body_length_m)]
            self.logger.debug('arena_vertices_m: {0}'.format(arena_vertices_m))

            sys_terms_container_xpath = './navigation_strategies/system_terms'
            sys_terms_cont = self.cfg_root.find(sys_terms_container_xpath)
            terms_xpath = 'term'
            sys_terms = sys_terms_cont.findall(terms_xpath)

            usr_terms_container_xpath = 'user_terms'
            usr_terms = []
            if strategy_node is not None:
                usr_terms_cont = strategy_node.find(usr_terms_container_xpath)
                if usr_terms_cont is not None:
                    usr_terms = usr_terms_cont.findall(terms_xpath)

            hyb_terms_container_xpath = 'hybrid_terms'
            hyb_terms = []
            if strategy_node is not None:
                hyb_terms_cont = strategy_node.find(hyb_terms_container_xpath)
                if hyb_terms_cont is not None:
                    terms_xpath = 'hybrid'
                    hyb_terms = hyb_terms_cont.findall(terms_xpath)

            strategy_terms = [usr_terms, hyb_terms, sys_terms]
            terms = []
            for s in [0, 1, 2]:
                for var_node in strategy_terms[s]:
                    name = var_node.attrib['name']
                    description = var_node.attrib['description']
                    units = var_node.attrib['units']
                    if 'alt_units' in var_node.attrib:
                        alt_units = var_node.attrib['alt_units']
                    else:
                        alt_units = None
                    scope = s
                    if s < 2:  # user_defined/hybrid:
                        expression = var_node.attrib['expression']
                        alt_expression = var_node.attrib['alt_expression'] if 'alt_expression' in var_node.attrib else None
                    else:
                        expression = None
                        alt_expression = None
                    term_colour = var_node.attrib['colour'] if 'colour' in var_node.attrib and var_node.attrib['colour'] != 'None' else None
                    if s == 0:
                        term = Term(
                            None,
                            name,
                            description,
                            expression,
                            units,
                            alt_expression,
                            alt_units,
                            term_colour,
                            cur_strategy
                        )
                    elif s == 1:
                        term = Hybrid(
                            None,
                            name,
                            description,
                            expression,
                            units,
                            alt_expression,
                            alt_units,
                            term_colour,
                            cur_strategy
                        )
                    else:
                        term = Systerm(
                            None,
                            name,
                            description,
                            expression,
                            units,
                            alt_expression,
                            alt_units,
                            term_colour,
                            cur_strategy
                        )

                    terms.append(term)

            self.database['strategy.terms'] = terms

            rules_xpath = './rules/rule'
            strategy_rules = []
            if strategy_node is not None:
                strategy_rules = strategy_node.findall(rules_xpath)
            rules = []
            for rule_node in strategy_rules:

                name = rule_node.attrib['name']
                description = rule_node.attrib['description']
                priority = int(rule_node.attrib['priority'])
                condition = rule_node.find('condition').text
                left_speed = rule_node.find('left_speed').text
                right_speed = rule_node.find('right_speed').text
                duration = rule_node.find('duration').text
                stage_complete_attrib = rule_node.attrib['stage_complete']
                stage_complete = stage_complete_attrib is not None and stage_complete_attrib == 'True'
                scope = int(rule_node.attrib['scope'])

                strat_rule = Rule(None,
                                  '0',
                                  name,
                                  description,
                                  priority,
                                  condition,
                                  left_speed,
                                  right_speed,
                                  duration,
                                  stage_complete,
                                  scope,
                                  cur_strategy
                                  )
                rules.append(strat_rule)  # strat_rule_dict

            self.database['strategy.rules'] = rules

        except Exception as e2:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error('Error parsing Config: ' +
                              str(e2) + ' on line ' + str(err_line))

    # def keys(self):
    #     return list(self.database.keys())
    #
    # def items(self):
    #     return list(self.database.items())

    def save_config(self):
        self.cfg_tree.write(self.cfg_file_path)

    def resetFence(self):
        self.logger.debug('Resetting Fence...')
        fence_node = self.cur_lawn_node.find('fence')
        for pt in list(fence_node):
            fence_node.remove(pt)

        inset_pc = 25  # % border
        low_point = str(round(inset_pc, 1))
        high_point = str(round(100 - inset_pc, 1))
        '''
            system is cartesian y ascending up
            orientation is Clockwise from Bottom-Left:
            1      2
            0      3
        '''
        ET.SubElement(fence_node, 'point', index='0', x=low_point, y=low_point)
        ET.SubElement(fence_node, 'point', index='2',
                      x=low_point, y=high_point)
        ET.SubElement(fence_node, 'point', index='4',
                      x=high_point, y=high_point)
        ET.SubElement(fence_node, 'point', index='6',
                      x=high_point, y=low_point)
        self.parse()
        self.schedule_save()

    def resetCalib(self):

        self.logger.debug('Resetting Calibration...')
        calib_node = self.cur_lawn_node.find('calib')
        for pt in calib_node.findall('point'):
            calib_node.remove(pt)
        '''
            system is cartesian y ascending up
            orientation is Clockwise from Bottom-Left:
            1      2
            0      3
        '''
        ET.SubElement(calib_node, 'point', index='0', x='30', y='30')
        ET.SubElement(calib_node, 'point', index='1', x='30', y='60')
        ET.SubElement(calib_node, 'point', index='2', x='60', y='60')
        ET.SubElement(calib_node, 'point', index='3', x='60', y='30')
        self.parse()
        self.schedule_save()

    def __contains__(self, key):
        return key in self.database

    def __getitem__(self, key):
        result = None
        if key in self.database:
            result = self.database[key]
        else:
            print('Config.__getitem__() Could not find:', key, 'in database')
            raise NameError('Config key {0} not found'.format(key))

        return result

    def __setitem__(self, key, value):
        commit = False
        partial_commit = False  # default
        # check key for partial_commit prefix
        if key is not None and key.startswith('_'):
            key = key[1:]
            partial_commit = True
            self.logger.debug('Config Update Partial Commit key: ' + key)
        key_parts = key.split('.')
        tgt_node = self.get_target_node(key_parts)
        self.logger.debug('Config Update tgt node: ' + str(tgt_node))
        if key not in self.database:
            pk_val = self.get_pk_value(key_parts)
            coll_xpath = '/'.join(key_parts)
            # locate collection node
            coll_node = tgt_node.find(coll_xpath)
            self.logger.debug('collection node' + str(coll_node))
            if coll_node is not None:
                # check container for permission to update nodes
                module_name = coll_node.attrib['module']
                klass = Morphable.get_klass(module_name)
                updatable_att = coll_node.attrib.get('updatable')
                updatable = updatable_att is not None and updatable_att == "true"
                # create a class object
                if klass is None:
                    self.logger.debug(
                        'Class non-existent - ' + module_name.title())
                    # raise missing entity class exception
                    raise MissingClassException(module_name.title())
                else:
                    instance = klass.from_json_str(value)
                    pk_name = klass.pk_att_name
                    item_filter = '{0}[@{1}="{2}"]'.format(
                        module_name, pk_name, pk_val)
                    pre_existing_item_nodes = coll_node.xpath(item_filter)
                    if pre_existing_item_nodes is not None and len(pre_existing_item_nodes) == 1:
                        if updatable:
                            # emit an xml node
                            new_item_node = instance.as_xml_node(pk_val)
                            self.logger.debug(ET.tostring(new_item_node))
                            # replace current node
                            coll_node.replace(
                                pre_existing_item_nodes[0], new_item_node)
                            commit = True
                            self.logger.debug(
                                'Node identified - collection updated')
                        else:
                            self.logger.debug(
                                'Node identified - but collection not updatable!')
                            # raise collection not updatable exception
                            raise CollectionNotUpdatableException()
                    else:
                        # raise record not found exception
                        raise RecordNotFoundException(pk_val)

        elif self.database[key] != value:
            self.logger.debug('Config Update key: ' + key + ' from: ' +
                              str(self.database[key]) + ' to value: ' + str(value) + ' ?')
            # and has changed
            if key.startswith('current.'):
                self.settings[key.split('.')[1]] = value
                commit = True
            else:
                try:
                    att_name = key_parts[-1]
                    # first assume the key is path to node
                    node_xpath = key.replace('.', '/')
                    node = tgt_node.find(node_xpath)
                    self.logger.debug('node xpath: ' + node_xpath)
                    self.logger.debug('node: ' + str(node))
                    if node is not None:
                        # key is a node path - update node text
                        node_text = node.text
                        self.logger.debug('current node text: ' + node_text)

                        if node_text != value:
                            self.logger.debug(
                                'Updating: ' + key + ' to value: ' + str(value))
                            node.text = str(value)
                            commit = True
                    else:
                        # key may be an attribute name?
                        if len(key_parts) == 1:
                            att_node = tgt_node
                        else:
                            att_node_xpath = '/'.join(map(str,
                                                      (key_parts[:-1])))
                            self.logger.debug(
                                'att node xpath: ' + att_node_xpath)
                            att_node = tgt_node.find(att_node_xpath)
                        self.logger.debug('att node: ' + str(att_node))
                        if att_node is not None:
                            self.logger.debug(
                                'Updating: ' + key + ' to attribute value: ' + str(value))
                            att_node.attrib[att_name] = str(value)
                            commit = True
                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.error(
                        'Error in api __setitem__: ' + str(e) + ' on line ' + str(err_line))
                    raise RecordNotFoundException(key)

        if partial_commit:
            self.logger.debug('Partial Commit Saving Config...')
            self.database[key] = value  # short circuit
            self.schedule_save()  # xml => file
        elif commit:
            self.logger.debug('Full Commit Saving Config...')
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            # issue callback - but not repeatedly
            if self.callback is not None:
                if 'timer' in vars(self):
                    self.timer.cancel()
                self.timer = Timer(5, self.callback)
                self.timer.start()

    def __str__(self):
        result = ''
        max_list = 10000  # use 10000 to see all items
        obfuscations = ['password']
        for key, value in self.database.items():
            do_obfuscate = any(obfuscate in key for obfuscate in obfuscations)
            if isinstance(value, list):
                list_values = '\n\t'.join(map(str, value))
                result += key + ' = [\n\t' + list_values[:max_list] + '\n]\n'
                if len(list_values) > max_list:
                    result += '...\n\n'
            else:
                result += key + ' = ' + \
                    ('*' * len(str(value)) if do_obfuscate else str(value)) + '\n'
        return result

    def patch(self, key, value):
        commit = False
        partial_commit = False  # default
        # check key for partial_commit prefix
        if key is not None and key.startswith('_'):
            key = key[1:]
            partial_commit = True
            self.logger.debug('Config Update Partial Commit key: ' + key)
        key_parts = key.split('.')

        pk_val = self.get_pk_value(key_parts)
        tgt_node = self.get_target_node(key_parts)
        coll_xpath = '/'.join(key_parts)
        # locate collection node
        coll_node = tgt_node.find(coll_xpath)
        self.logger.debug('collection node:' + str(coll_node))
        if coll_node is not None:
            # check container for permission to update nodes
            module_name = coll_node.attrib['module']
            klass = Morphable.get_klass(module_name)
            updatable_att = coll_node.attrib.get('updatable')
            updatable = updatable_att is not None and updatable_att == "true"
            # create a class object
            if klass is None:
                self.logger.debug('Class non-existent - ' +
                                  module_name.title())
                # raise missing entity class exception
                raise MissingClassException(module_name.title())
            else:
                pk_name = klass.pk_att_name
                item_filter = '{0}[@{1}="{2}"]'.format(
                    module_name, pk_name, pk_val)
                pre_existing_item_nodes = coll_node.xpath(item_filter)
                if pre_existing_item_nodes is not None and len(pre_existing_item_nodes) == 1:
                    if updatable:
                        # emit an xml node
                        item_node = pre_existing_item_nodes[0]
                        data_dict = json.loads(value)
                        exist_keys = item_node.attrib.keys()
                        if not set(data_dict).issubset(exist_keys):
                            raise AttributeNotFoundException()
                        else:
                            item_node.attrib.update(
                                {(k, str(v)) for k, v in data_dict.items()})

                        commit = True
                        self.logger.debug(
                            'Node identified - collection updated')
                    else:
                        self.logger.debug(
                            'Node identified - but collection not updatable!')
                        raise CollectionNotUpdatableException()
                else:
                    raise RecordNotFoundException(pk_val)

        if partial_commit:
            self.logger.debug('Partial Commit Saving Config...')
            self.database[key] = value  # short circuit
            self.schedule_save()  # xml => file
        elif commit:
            self.logger.debug('Full Commit Saving Config...')
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()

    def add(self, key, value):
        # add item to collection, if not a duplicate
        self.logger.info('Config adding {0} to {1}'.format(value, key))

        commit = False
        partial_commit = False  # default
        # check key for partial_commit prefix
        if key is not None and key.startswith('_'):
            key = key[1:]
            partial_commit = True
            self.logger.debug('Config Update Partial Commit key: ' + key)
        key_parts = key.split('.')

        tgt_node = self.get_target_node(key_parts)
        coll_xpath = '/'.join(key_parts)
        # locate collection node
        coll_node = tgt_node.find(coll_xpath)
        self.logger.debug('collection node' + str(coll_node))
        # check container for permission to add nodes, delete nodes, reorder nodes
        module_name = coll_node.attrib['module']
        klass = Morphable.get_klass(module_name)
        extensible_att = coll_node.attrib.get('extensible')
        expandable_att = coll_node.attrib.get('expandable')
        extensible = extensible_att is not None and extensible_att == "true"
        expandable = expandable_att is not None and expandable_att == "true"
        # create a class object
        if klass is None:
            self.logger.debug('Class non-existent - ' + module_name.title())
            # raise missing entity class exception
            raise MissingClassException(module_name.title())
        else:
            instance = klass.from_json_str(value)
            pk_name = klass.pk_att_name
            dupe_filter = instance.as_xpath_filter()
            pre_existing_item_nodes = coll_node.xpath(dupe_filter)
            self.logger.debug('pre_existing_item_nodes' +
                              str(pre_existing_item_nodes))

            if pre_existing_item_nodes is not None and len(pre_existing_item_nodes) > 0:
                # raise attempt to create duplicate exception
                raise DuplicateRecordException('Item Already Exists')
            elif extensible:
                # insert new node
                if expandable:
                    # find all nodes beyond (only works for numeric primary keys)
                    nodes_beyond_xpath = dupe_filter.replace('=', '>')
                    self.logger.debug(
                        'nodes beyond xpath: ' + str(nodes_beyond_xpath))
                    nodes_beyond = coll_node.xpath(nodes_beyond_xpath)
                    self.logger.debug('nodes beyond: ' + str(nodes_beyond))
                    # make space by moving nodes up two
                    for node_beyond in nodes_beyond:
                        node_beyond.attrib[pk_name] = str(
                            int(node_beyond.attrib[pk_name]) + 2)
                    # emit an incremented xml node
                    new_item_node = instance.inc_index().as_xml_node()
                    self.logger.debug(
                        'Node inserting - collection expanded to accommodate')
                else:
                    # emit an xml node
                    new_item_node = instance.as_xml_node()
                    self.logger.debug('Node inserting - no expansion required')

                # append to end
                coll_node.append(new_item_node)
                commit = True
                self.logger.debug('Node inserted')
            else:
                self.logger.debug(
                    'Node non-existent, attempting to add - but collection not extensible!')
                # raise collection not extensible exception
                raise CollectionNotExtensibleException()

        if partial_commit:
            self.logger.debug('Partial Commit Saving Config...')
            self.database[key] = value  # short circuit
            self.schedule_save()  # xml => file
        elif commit:
            self.logger.debug('Full Commit Saving Config...')
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()

    def delete(self, key):
        commit = False
        key_parts = key.split('.')
        # identify pk value
        pk_val = self.get_pk_value(key_parts)
        tgt_node = self.get_target_node(key_parts)
        self.logger.debug('targetting: ' + str(tgt_node))
        coll_xpath = '/'.join(key_parts)
        # locate collection node
        coll_node = tgt_node.find(coll_xpath)
        self.logger.debug('collection node' + str(coll_node))
        if coll_node is not None:
            # check container for permission to delete nodes, contract nodes
            module_name = coll_node.attrib['module']
            klass = Morphable.get_klass(module_name)
            deletable = coll_node.attrib.get('deletable') == "true"
            # create a class object
            if klass is None:
                self.logger.debug('Class non-existent - ' +
                                  module_name.title())
                # raise missing entity class exception
                raise MissingClassException(module_name.title())
            else:
                pk_name = klass.pk_att_name
                item_filter = '{0}[@{1}="{2}"]'.format(
                    module_name, pk_name, pk_val)

            # construct xpath to locate existing node
            item_xpath = coll_xpath + "/" + item_filter
            self.logger.debug('collection item xpath: ' + item_xpath)
            cur_item_node = tgt_node.find(item_xpath)
            self.logger.debug('itm node: ' + str(cur_item_node))
            if cur_item_node is not None:
                if deletable:
                    # remove current node
                    coll_node.remove(cur_item_node)
                    commit = True
                else:
                    self.logger.debug(
                        'Node not deleted - collection items not deletable')
                    # raise collection not deletable exception
                    raise CollectionNotDeletableException()
            else:
                self.logger.debug('Node not identified for deletion')
                # raise record not found exception
                raise RecordNotFoundException(pk_val)
        else:
            self.logger.debug('Config Delete key: ' + key)
            if key.startswith('current.'):
                self.settings[key.split('.')[2]] = None
                commit = True
            else:
                att_name = key_parts[-1]
                # first assume the key is path to node
                node_xpath = key.replace('.', '/')
                node = tgt_node.find(node_xpath)
                self.logger.debug('node xpath: ' + node_xpath)
                self.logger.debug('node: ' + str(node))
                if node is not None:
                    # key is a node path - clear node text
                    node.text = ""
                    commit = True
                else:
                    # key may be an attribute name?
                    if len(key_parts) == 1:
                        att_node = tgt_node
                    else:
                        att_node_xpath = '/'.join(map(str, (key_parts[:-1])))
                        self.logger.debug('att node xpath: ' + att_node_xpath)
                        att_node = tgt_node.find(att_node_xpath)
                    self.logger.debug('att node: ' + str(att_node))
                    if att_node is not None:
                        self.logger.debug(
                            'Updating: ' + key + ' to attribute value: None')
                        att_node.attrib[att_name] = "None"
                        commit = True

        if commit:
            self.logger.debug('Full Commit Saving Config...')
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()

    def sort_children(self, parent, attr):

        parent[:] = sorted(parent, key=lambda child: int(child.get(attr)))

    def reprioritiseRule(self, rule, rules):

        rule.attrib['priority'] = str(rules.index(rule))

        return rule

    def renumberPriorities(self):
        # renumber priorities
        rules = self.cur_strategy_node.xpath('rules/rule')
        self.logger.debug('initial rules')
        for rule in rules:
            self.logger.debug(
                rule.attrib['name'] + ' ' + rule.attrib['priority'])

        self.sort_children(rules, 'priority')
        self.logger.debug('sorted rules')
        for rule in rules:
            self.logger.debug(
                rule.attrib['name'] + ' ' + rule.attrib['priority'])

        m = [self.reprioritiseRule(rule, rules) for rule in rules]
        self.cur_strategy_node.find('rules')[:] = list(m)
        self.logger.debug('renumbered rules')
        for rule in rules:
            self.logger.debug(
                rule.attrib['name'] + ' ' + rule.attrib['priority'])

    def promote_rule(self, index):

        # locate node
        rule_xpath = "rules/rule[@index='{0}']".format(index)
        rule_node = self.cur_strategy_node.find(rule_xpath)
        if rule_node is not None:
            # locate priority
            rule_priority = rule_node.attrib['priority']
            # locate rule above
            rule_priorities_xpath = 'rules/rule/@priority'
            strategy_rule_priorities = self.cur_strategy_node.xpath(
                rule_priorities_xpath)
            strategy_rule_priorities.sort(key=lambda r: int(r))
            above_rule_priority = strategy_rule_priorities[strategy_rule_priorities.index(
                rule_priority) - 1]
            above_rule_xpath = "rules/rule[@priority='{0}']".format(
                above_rule_priority)
            above_rule_node = self.cur_strategy_node.find(above_rule_xpath)
            self.logger.debug('Promote Rule ' +
                              rule_priority + '><' + above_rule_priority)
            rule_node.attrib['priority'] = above_rule_priority
            above_rule_node.attrib['priority'] = rule_priority

            # self.renumberPriorities() # temp for fixing data!

            self.logger.debug('Full Commit Saving Config...')
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()

            self.logger.debug('Config Committed and reloaded')
        else:
            self.logger.error('Config Failed to promote rule')
            raise RecordNotFoundException(index)

    def demote_rule(self, index):

        # locate node
        rule_xpath = "rule[@index='{0}']".format(index)
        rule_node = self.cur_strategy_node.find(rule_xpath)
        # locate priority
        rule_priority = rule_node.attrib['priority']
        # locate rule below
        rule_priorities_xpath = './rule/@priority'
        strategy_rule_priorities = self.cur_strategy_node.xpath(
            rule_priorities_xpath)
        strategy_rule_priorities.sort(key=lambda r: int(r))
        below_rule_priority = strategy_rule_priorities[strategy_rule_priorities.index(
            rule_priority) + 1]
        below_rule_xpath = "rule[@priority='{0}']".format(below_rule_priority)
        below_rule_node = self.cur_strategy_node.find(below_rule_xpath)
        self.logger.debug('Demote Rule ' + rule_priority +
                          '><' + below_rule_priority)
        rule_node.attrib['priority'] = below_rule_priority
        below_rule_node.attrib['priority'] = rule_priority

        self.renumberPriorities()  # temp for fixing data!

        self.save_config()  # write back
        time.sleep(self.SAVE_INIT_DELAY_SECS)
        self.initialise()  # reload
        self.logger.debug('Config Committed and reloaded')

    def delete_rule(self, name):
        # locate node
        rules_node = self.cur_strategy_node.find('rules')
        rule_xpath = "rule[@name='{0}']".format(name)
        rule_node = rules_node.find(rule_xpath)
        # remove node?
        if rule_node is not None:
            rules_node.remove(rule_node)
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()
            self.logger.debug('Config Committed and reloaded')

    def delete_term(self, name):
        # locate node
        terms_node = self.cur_strategy_node.find('user_terms')
        term_xpath = "term[@name='{0}']".format(name)
        term_node = terms_node.find(term_xpath)
        # remove node?
        if term_node is not None:
            terms_node.remove(term_node)
            self.schedule_save()  # xml => file
            self.parse()  # reload xml => database
            if self.callback is not None:
                self.callback()
            self.logger.debug('Config Committed and reloaded')

    def get_next_in_seq(self, root_node, elem_name, att_name):
        if root_node is None:
            root_node = self.cfg_root
        xpath = '//{0}/@{1}'.format(elem_name, att_name)
        indices = list(map(int, root_node.xpath(xpath)))
        new_index = max(indices) + 1
        return new_index

    def duplicate_rule(self, name):
        # locate node
        rule_xpath = "rules/rule[@name='{0}']".format(name)
        rule_node = self.cur_strategy_node.find(rule_xpath)
        # clone node
        dupe_rule_node = copy.deepcopy(rule_node)

        # append -copy to name
        dupe_rule_node.attrib['name'] += '-copy'

        self.cur_strategy_node.find('rules').append(dupe_rule_node)
        self.renumberPriorities()
        self.logger.debug('Full Commit Saving Config...')
        self.schedule_save()  # xml => file
        self.parse()  # reload xml => database
        if self.callback is not None:
            self.callback()
        self.logger.debug('Config Committed and reloaded')

    def get_target_node(self, key_parts):

        # lawn, mower, etc.
        tgt_node_name = key_parts[0]
        self.logger.info('targetting: ' + tgt_node_name)
        if tgt_node_name == 'profile':
            tgt_node = self.cur_profile_node
            key_parts.pop(0)
        elif tgt_node_name == 'lawn':
            tgt_node = self.cur_lawn_node
            key_parts.pop(0)
        elif tgt_node_name == 'calib':
            tgt_node = self.cur_calib_node
            key_parts.pop(0)
        elif tgt_node_name == 'fence':
            tgt_node = self.cur_fence_node
            key_parts.pop(0)
        elif tgt_node_name == 'device':
            tgt_node = self.cur_dev_node
            key_parts.pop(0)
        elif tgt_node_name == 'optical':
            tgt_node = self.cur_opt_node
            key_parts.pop(0)
        elif tgt_node_name == 'hotspot':
            tgt_node = self.cur_hotspot_node
            key_parts.pop(0)
        elif tgt_node_name == 'mower':
            tgt_node = self.cur_mower_node
            key_parts.pop(0)
        elif tgt_node_name == 'strategy':
            tgt_node = self.cur_strategy_node
            key_parts.pop(0)
        elif tgt_node_name in ['span', 'area']:
            if self.PROFILED_MEASURES:
                tgt_node = self.cur_profile_node.find(
                    "measures/scaled_measures/scaled[@name='{}']".format(tgt_node_name))
            else:
                tgt_node = self.cfg_root.find(
                    "measures/scaled_measures/scaled[@name='{}']".format(tgt_node_name))
            if tgt_node is not None:
                key_parts.pop(0)
        elif tgt_node_name in ['solidity', 'isoscelicity', 'fitness']:
            if self.PROFILED_MEASURES:
                tgt_node = self.cur_profile_node.find(
                    "measures/setpoint_measures/setpoint[@name='{}']".format(tgt_node_name))
            else:
                tgt_node = self.cfg_root.find(
                    "measures/setpoint_measures/setpoint[@name='{}']".format(tgt_node_name))
            if tgt_node is not None:
                key_parts.pop(0)
        elif tgt_node_name == '':
            pass
        else:
            tgt_node = self.cfg_root

        return tgt_node

    def get_pk_value(self, key_parts):
        pk_val = key_parts.pop()
        return pk_val

    def query_xpath(self, xpath_query):
        element = None
        elements = self.cfg_root.xpath(xpath_query)
        if len(elements) > 0:
            element = elements[0]
        return element
