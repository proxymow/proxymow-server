#!/usr/bin/env python3

from argparse import ArgumentParser
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import glob
import json
import cherrypy
from jinja2 import Environment, FileSystemLoader
import random
import io
import os
import tempfile
import platform
import gc
import datetime
from datetime import timezone
import time
from time import sleep
from math import radians, degrees, sin, cos
import numpy as np
from copy import deepcopy
from matplotlib.font_manager import findfont, FontProperties
try:
    from picamera2 import Picamera2  # @UnresolvedImport
except ModuleNotFoundError:
    pass
from PIL import Image, ImageFile, ImageDraw, ImageFont
from scipy.ndimage import zoom
import copy
import socket
import sys
import queue
from queue import Empty
from threading import Thread
import urllib.parse
from collections import deque, namedtuple
import more_itertools
import lxml.etree as ET
import traceback
import mariadb
import markdown

import utilities
import constants
from cameras import RemoteOpticalPi
from odometry import Movement
from dashed_image_draw import DashedImageDraw
import configurations
from vis_lib import get_fence_mask_surface, \
    grid_intersections_camera, get_polygons_from_pc, matrices_from_quad_points, \
    get_prospect_list, probe_prospect_list, render_contour_row, lores_contours
from geom_lib import annot_arrow, annot_axle, distance_to_line, diff_angles
from utilities import trace_rules, trace_command, trace_location, \
    despatch_to_mower_udp, \
    fetch_telemetry, \
    LOCATION_CSV_HEADER, \
    get_mem_stats
from diagram_lib import plot_excursion, plot_contour_entry_as_projection, \
    plot_projection_img
from rules_engine import RulesEngine
import poses
import tmplt_utils
from snapshot import Snapshot, SnapshotGrowth
from virtual import vmower
from mapper import ImageMapper, DataMapper
from timesheet import Timesheet
from pxm_exceptions import *  # @UnusedWildImport
from itinerary import Itinerary
from fixed_length_dict import SnapshotBuffer
from cameras import OpticalVirtual
from viewport import Viewport
from forms.morphable import Morphable
from forms.rule import RuleScope


class MowerProxy():

    def __init__(self, config, socket):
        self.config = config
        self.udp_socket = socket

    def get(self):
        pose = utilities.fetch_pose(self.config, self.udp_socket)
        return pose

    def set(self, x_m, y_m, theta_deg, axle_track_m, velocity_full_speed_mps):
        utilities.despatch_to_mower_udp(
            'set_pose({}, {}, {}, {}, {:.5f})'.format(
                x_m,
                y_m,
                theta_deg,
                axle_track_m,
                velocity_full_speed_mps),
            self.udp_socket,
            self.config['mower.ip'],
            self.config['mower.port'],
            await_response=True,
            max_attempts=3
        )


class ProxymowServer(object):

    VERSION_STRING = "1.0.10"

    linux = (platform.system() == 'Linux')

    tmp_folder_path = tempfile.gettempdir() + os.path.sep
    font_path = findfont(FontProperties(family=['sans-serif']))

    LOG_MAX_BYTES = constants.LOG_MAX_BYTES
    LOG_BACKUP_COUNT = constants.LOG_BACKUP_COUNT

    def __init__(self, args):
        self.debug = args.debug
        self.log_level = logging.DEBUG if self.debug else logging.WARNING
        # create formatters
        log_formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        data_log_formatter = logging.Formatter()

        if args.work_folder is None:
            work_folder_path = Path.home()
        else:
            work_folder_path = Path(args.work_folder).resolve()

        print('Proxymow Working Directory Path:', work_folder_path.__str__())
        app_root_path = Path(__file__).parent
        print('Proxymow Application Root Path:', app_root_path.__str__())
        self.settings_file_path_name = (
            app_root_path / 'configs' / 'settings.yml').resolve().__str__()
        self.config_file_path_name = (
            app_root_path / 'configs' / 'config.xml').resolve().__str__()

        self.image_folder_path_name = (
            work_folder_path / 'images').resolve().__str__()
        # ensure folder exists
        if not os.path.exists(self.image_folder_path_name):
            os.makedirs(self.image_folder_path_name)
        self.calib_folder_path_name = (
            work_folder_path / 'calib').resolve().__str__()
        # ensure folder exists
        if not os.path.exists(self.calib_folder_path_name):
            os.makedirs(self.calib_folder_path_name)
        self.calib_img_name = (
            work_folder_path / 'calib' / 'calib-{}.jpg').resolve().__str__()
        self.tmplt_path_name = (
            app_root_path / 'templates').resolve().__str__()
        self.env = Environment(loader=FileSystemLoader(self.tmplt_path_name))

        log_folder_path = (work_folder_path / 'logs').resolve()

        pxm_log_file_name = ((log_folder_path / 'pxm.log').resolve()).__str__()
        comms_log_file_name = (
            (log_folder_path / 'comms.log').resolve()).__str__()
        vision_log_file_name = (
            (log_folder_path / 'vision.log').resolve()).__str__()
        settings_log_file_name = (
            (log_folder_path / 'settings.log').resolve()).__str__()
        locator_log_file_name = (
            (log_folder_path / 'locator.log').resolve()).__str__()
        navigation_log_file_name = (
            (log_folder_path / 'navigation.log').resolve()).__str__()
        last_cmds_log_file_name = (
            (log_folder_path / 'last-cmds.log').resolve()).__str__()
        patterns_log_file_name = (
            (log_folder_path / 'patterns.log').resolve()).__str__()
        excursion_log_file_name = (
            (log_folder_path / 'excursion.csv').resolve()).__str__()
        contours_log_file_name = (
            (log_folder_path / 'contours.dat').resolve()).__str__()

        # main log
        self.pxm_logger = logging.getLogger('pxm')
        # create handler
        log_handler = RotatingFileHandler(
            pxm_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        log_handler.setFormatter(log_formatter)
        self.pxm_logger.addHandler(log_handler)
        self.pxm_logger.setLevel(self.log_level)

        # settings log
        self.settings_log = logging.getLogger('settings')
        # create handler
        settings_log_handler = RotatingFileHandler(
            settings_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        settings_log_handler.setFormatter(log_formatter)
        self.settings_log.addHandler(settings_log_handler)
        self.settings_log.setLevel(self.log_level)

        # comms log
        comms_logger = logging.getLogger('comms')
        # create handler
        comms_log_handler = RotatingFileHandler(
            comms_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        comms_log_handler.setFormatter(log_formatter)
        comms_logger.addHandler(comms_log_handler)
        comms_logger.setLevel(self.log_level)

        # vision log
        self.vision_logger = logging.getLogger('vision')
        # create handler
        vision_log_handler = RotatingFileHandler(
            vision_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        vision_log_handler.setFormatter(log_formatter)
        self.vision_logger.addHandler(vision_log_handler)
        self.vision_logger.setLevel(self.log_level)

        # locator log
        locator_logger = logging.getLogger('locator')
        # create handler
        locator_log_handler = RotatingFileHandler(
            locator_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        locator_log_handler.setFormatter(log_formatter)
        locator_logger.addHandler(locator_log_handler)
        locator_logger.setLevel(self.log_level)

        # navigation log
        navigation_logger = logging.getLogger('navigation')
        # create handler
        navigation_log_handler = RotatingFileHandler(
            navigation_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        navigation_log_handler.setFormatter(log_formatter)
        navigation_logger.addHandler(navigation_log_handler)
        navigation_logger.setLevel(self.log_level)

        # last commands log
        last_cmds_logger = logging.getLogger('last-cmds')
        # create handler
        last_cmds_log_handler = RotatingFileHandler(
            last_cmds_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        last_cmds_log_handler.setFormatter(log_formatter)
        last_cmds_logger.addHandler(last_cmds_log_handler)
        last_cmds_logger.setLevel(self.log_level)

        # mow patterns log
        pattern_logger = logging.getLogger('mow-patterns')
        # create handler
        pattern_log_handler = RotatingFileHandler(
            patterns_log_file_name, maxBytes=self.LOG_MAX_BYTES, backupCount=self.LOG_BACKUP_COUNT)
        # add formatter to handler
        pattern_log_handler.setFormatter(log_formatter)
        pattern_logger.addHandler(pattern_log_handler)
        pattern_logger.setLevel(self.log_level)

        # excursion log
        excursion_logger = logging.getLogger('excursion')
        # create handler
        excursion_log_handler = RotatingFileHandler(
            excursion_log_file_name,
            maxBytes=self.LOG_MAX_BYTES,
            backupCount=self.LOG_BACKUP_COUNT
        )
        # add formatter to handler
        excursion_log_handler.setFormatter(data_log_formatter)
        excursion_logger.addHandler(excursion_log_handler)
        excursion_logger.setLevel(logging.ERROR)  # initially logs nothing

        # contours log
        contour_logger = logging.getLogger('contours')
        # create handler
        contour_log_handler = RotatingFileHandler(
            contours_log_file_name,
            maxBytes=self.LOG_MAX_BYTES * 2,
            backupCount=self.LOG_BACKUP_COUNT
        )
        # add formatter to handler
        contour_log_handler.setFormatter(data_log_formatter)
        contour_logger.addHandler(contour_log_handler)
        contour_logger.setLevel(logging.ERROR)  # initially logs nothing

        self.contours_buffer = deque([], 100)
        arch_file_lst = os.listdir(self.image_folder_path_name)
        num_files = len(arch_file_lst)
        self.archive_image_count = (
            num_files + 1) % constants.ARCHIVE_IMAGE_MAX_COUNT

        self.pxm_logger.info('server initialisation started...')
        self.initialise()

    def initialise(self):

        try:

            self.log('initialise started...')
            self.config = configurations.Config(
                self.settings_file_path_name, self.config_file_path_name, debug=self.debug, callback=self.re_init)
            self.log(str(self.config))
            self.db_connection = None
            self.envir = {}
            self.drive = {'state': ''}
            self.drive_pause = False
            self.drive_step = False
            self.drive_cancel = False
            self.drive['path'] = None
            self.reset_index = 0
            self.itinerary = None
            self.total_destinations = 0
            self.pose = None
            self.cmds = []
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(4)
            self.udp_socket2 = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)  # Mower Proxy
            self.udp_socket2.settimeout(4)
            self.telemetry_updated = 0  # force immediate update
            self.when_checked = 0  # force
            self.telem = {}
            self.cutter1_state = False
            self.cutter2_state = False
            self.calib_image_array_cache = {}

            # create instances of picam2, one per camera
            try:
                if not self.debug:
                    os.environ["LIBCAMERA_LOG_LEVELS"] = "2"
                inventory = Picamera2.global_camera_info()
                self.log('Camera Inventory: ' + str(inventory))
                for i, attached_camera in enumerate(inventory):
                    if 'i2c' in attached_camera['Id']:
                        # its a pi camera
                        self.log('Creating a Picamera Object for attached pi Camera: {} Index: {}...'.format(
                            attached_camera['Model'], i))
                        self.pipicam2 = Picamera2(i)
                    elif 'usb' in attached_camera['Id']:
                        # its a usb camera
                        self.log('Creating a Picamera Object for attached usb Camera: {} Index: {}...'.format(
                            attached_camera['Model'], i))
                        self.usbpicam2 = Picamera2(i)
            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                err_msg = 'Unable to init OpticalPi: ' + \
                    str(e) + ' on line ' + str(err_line)
                err_msg += ' Picamera2 not available on Windows?'
                self.log_warning(err_msg)

            # initialise location properties
            self.location_props = {
                'not_found_count': 0
            }
            self.extrapolation_incidents = 0

            # create unpopulated mappers
            self.log('init about to create mappers...', True)  # log memory
            self.distort_mapper = ImageMapper(
                logger=self.pxm_logger, populate=False)
            self.undistort_unwarp_mapper = ImageMapper(
                logger=self.pxm_logger, populate=False)
            self.undistort_mapper = ImageMapper(
                logger=self.pxm_logger, populate=False)
            self.unwarp_mapper = ImageMapper(
                logger=self.pxm_logger, populate=False)
            self.data_mapper = DataMapper(
                logger=self.pxm_logger, populate=False)
            self.grid_data_mapper = DataMapper(
                logger=self.pxm_logger, populate=False)
            self.rules_engine = None
            self.cached_scoring_snapshot = None
            self.cached_scoring_props = {}
            self.re_init(True)  # re-initialise artefacts

            self.snapshot_buffer = SnapshotBuffer(4)
            self.motivate_pose_buffer = deque([], 4)

            self.consecutive_extrapolations = 0

            # PIL load truncated image files
            ImageFile.LOAD_TRUNCATED_IMAGES = True

            # establish the input queue
            self.camera_request_queue = queue.Queue(maxsize=-1)
            # establish the output queues
            self.camera_locate_queue = queue.Queue(maxsize=-1)
            self.camera_vision_queue = queue.Queue(maxsize=-1)
            self.camera_snap_queue = queue.Queue(maxsize=-1)
            self.camera_raw_queue = queue.Queue(maxsize=-1)

            # create and start virtual mower thread
            self.vm_thread = Thread(target=self.virtual_mower)
            self.vm_thread.daemon = True
            self.vm_thread.start()

            sleep(2.0)  # allow time for virtual mower to start

            # create mower proxy
            self.shared = MowerProxy(self.config, self.udp_socket2)

            # create and start camera worker thread
            self.camera_worker = Thread(target=self.process_image)
            self.camera_worker.daemon = True
            self.camera_worker.start()

            # create and start governor thread
            self.run_governor = True
            self.governor_thread = Thread(target=self.governor)
            self.governor_thread.daemon = True
            self.governor_thread.start()

            self.log('init - complete, governor thread running: ' +
                     str(self.governor_thread.is_alive()))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in pxm initialisation: ' +
                           str(e) + ' on line ' + str(err_line))

    def re_init(self, first_time=False):
        '''
            initialise artefacts that might need re-initialising after a configuration change
        '''
        try:
            self.log('re_init started...')
            arena_width_m = self.config['arena.width_m']
            arena_length_m = self.config['arena.length_m']
            img_arr_cols = self.config['optical.width']
            img_arr_rows = self.config['optical.height']
            display_cols = self.config['optical.display_width']
            display_rows = self.config['optical.display_height']
            arena_matrix = self.config['calib.arena_matrix']
            img_matrix = self.config['calib.img_matrix']
            strength = self.config['optical.undistort_strength']
            zoom = self.config['optical.undistort_zoom']

            # temporary pause for governor
            self.log('re_init pausing governor...')
            self.run_governor = False
            sleep(2)

            self.log('re_init about to clear mappers...', True)  # log memory
            self.distort_mapper.clear()
            self.undistort_unwarp_mapper.clear()
            self.undistort_mapper.clear()
            self.unwarp_mapper.clear()
            self.data_mapper.clear()
            self.log('re_init about to garbage collect...', True)  # log memory
            gc.collect()
            self.log('re_init about to populate mappers...', True)  # log memory

            self.undistort_unwarp_mapper.populate(
                ["transform", "unbarrel"],
                display_cols,
                display_rows,
                matrix=img_matrix,
                strength=strength,
                zoom=zoom
            )
            self.log('re_init populated undistort unwarp mapper')
            self.data_mapper.populate(
                ["unbarrel_inv", "transform"],
                img_arr_cols,
                img_arr_rows,
                matrix=arena_matrix,
                strength=strength,
                zoom=zoom
            )

            self.log('re_init mappers populated', True)  # log memory

            if self.config['current.mower'] in self.config['mowers']:

                robot_span_m = self.config['mower.target_length_m']
                target_width_m = self.config['mower.target_width_m']
                target_radius_m = self.config['mower.target_radius_m']
                target_offset_pc = self.config['mower.target_offset_pc']
                body_width_m = self.config['mower.body_width_m']
                body_length_m = self.config['mower.body_length_m']
                axle_track_m = self.config['mower.axle_track_m']
                velocity_full_speed_mps = self.config['mower.velocity_full_speed_mps']

                poses.Pose.init(
                    self.config,
                    target_width_m,
                    robot_span_m,
                    target_radius_m,
                    target_offset_pc,
                    axle_track_m,
                    body_width_m,
                    body_length_m,
                    arena_width_m,
                    arena_length_m,
                    img_arr_cols,
                    img_arr_rows,
                    self.data_mapper,
                    logging.getLogger('locator')
                )

                Movement.init(axle_track_m, velocity_full_speed_mps)

            else:
                # default
                robot_span_m = 0.2  # dummy values to keep things rolling
                axle_track_m = 0.15
                poses.Pose.init(
                    self.config,
                    0,
                    robot_span_m,
                    0,
                    50,
                    axle_track_m,
                    0,
                    0,
                    arena_width_m,
                    arena_length_m,
                    img_arr_cols,
                    img_arr_rows,
                    self.data_mapper,
                    logging.getLogger('locator')
                )

            vlawn_bottom_left_ref_pc = (20, 20)
            vlawn_bottom_width_pc = 60
            vlawn_top_width_pc = 50
            vlawn_top_inset_pc = (
                vlawn_bottom_width_pc - vlawn_top_width_pc) / 2
            vlawn_height_pc = 60
            vlawn_top_right_pc = (vlawn_bottom_left_ref_pc[0] + vlawn_top_width_pc + vlawn_top_inset_pc, 100 - (
                vlawn_bottom_left_ref_pc[1] + vlawn_height_pc))
            vlawn_top_left_pc = (vlawn_bottom_left_ref_pc[0] + vlawn_top_inset_pc, 100 - (
                vlawn_bottom_left_ref_pc[1] + vlawn_height_pc))
            vlawn_bottom_right_pc = (
                vlawn_bottom_left_ref_pc[0] + vlawn_bottom_width_pc, 100 - (vlawn_bottom_left_ref_pc[1]))
            vlawn_bottom_left_pc = (
                vlawn_bottom_left_ref_pc[0], 100 - (vlawn_bottom_left_ref_pc[1]))
            vlawn_bollards_pc = []
            if constants.DISPLAY_VIRTUAL_LAWN_BOLLARDS:
                vlawn_bollards_pc = [(20, 20), (90, 90), (90, 70), (70, 90),
                                     (70, 70), (70, 20), (20, 70), (90, 20), (20, 90)]

            lawn_bounds_pc = [vlawn_bottom_left_pc, vlawn_top_left_pc,
                              vlawn_top_right_pc, vlawn_bottom_right_pc]
            distortion = 2.0
            if self.linux:
                try:
                    from lincameras import OpticalLusb
                except Exception as ce1:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.log_warning(
                        'No Linux USB camera Available in pxm re_init: ' + str(ce1) + ' on line ' + str(err_line))
                try:
                    from lincameras import OpticalPi
                except Exception as ce2:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.log_warning(
                        'No Linux RPI camera Available in pxm re_init: ' + str(ce2) + ' on line ' + str(err_line))
            else:
                from wincameras import OpticalWusb
            if self.config['device.channel'] == 'VirtualSettings':
                self.camera = OpticalVirtual(
                    lawn_bounds_pc,
                    vlawn_bollards_pc,
                    distortion,
                    self.distort_mapper,
                    debug=self.debug
                )
            elif self.config['device.channel'] == 'LusbSettings':
                if self.linux:
                    # linux webcam
                    self.log('Attempting to associate USB Camera...')
                    self.camera = OpticalLusb(
                        self.usbpicam2, debug=self.debug, logger=self.vision_logger)
            elif self.config['device.channel'] == 'WusbSettings':
                if not self.linux:
                    # windows webcam
                    self.camera = OpticalWusb(
                        int(self.config['device.index']), debug=self.debug, logger=self.vision_logger)
            elif self.config['device.channel'].startswith('PiSettings'):
                # only create once
                if self.linux:
                    try:
                        self.log('Attempting to associate RPI Camera...')
                        self.camera = OpticalPi(
                            self.pipicam2, 0, debug=self.debug, logger=self.vision_logger)
                        self.log('Linux RPI Camera associated')
                        self.camera.local_config_string = None
                    except Exception as e:
                        err_line = sys.exc_info()[-1].tb_lineno
                        self.log_error(
                            'FATAL Unable to associate Linux RPI Camera: ' + str(e) + ' on line ' + str(err_line))
                else:
                    # No pi camera 2 in windows - supply virtual camera instead!
                    self.camera = OpticalVirtual(
                        lawn_bounds_pc,
                        vlawn_bollards_pc,
                        distortion,
                        self.distort_mapper,
                        debug=self.debug
                    )
            elif self.config['device.channel'] == 'RemotePiSettings':
                self.camera = RemoteOpticalPi(self.config['device.endpoint'])
                self.log('RemoteOpticalPi Camera created')
            else:
                print('No Camera Selected')
                raise Exception('No Camera Selected')

            # strategy now based on mower/lawn combination which may change
            # however, we want to preserve the last n cmds & start time...
            if 'rules_engine' in vars(self) and self.rules_engine is not None:
                prev_last_n_cmds = self.rules_engine.last_n_commands
                prev_last_n_comp_cmds = self.rules_engine.last_n_comp_commands
                prev_route_started_time = self.rules_engine.route_started_time
            else:
                prev_last_n_cmds = None
                prev_last_n_comp_cmds = None
                prev_route_started_time = -1

            self.rules_engine = RulesEngine(
                self.config['current.strategy'],
                self.config['strategy.rules'],
                self.config['strategy.terms'],
                self.udp_socket,
                self.data_mapper
            )

            if prev_last_n_cmds is not None:
                self.rules_engine.last_n_commands = prev_last_n_cmds
                self.rules_engine.last_n_comp_commands = prev_last_n_comp_cmds
                self.rules_engine.route_started_time = prev_route_started_time

            # update location props
            self.location_props['not_found_count'] = 0

            # scoring properties
            self.score_props = {}
            scaled_names = ['span', 'area']
            scaled_property_names = ['lower', 'scale', 'upper', 'maxscore']
            measure_names = ['isoscelicity', 'solidity', 'fitness']
            meas_property_names = ['lower', 'setpoint', 'upper', 'maxscore']
            for name in scaled_names:
                prop_list = []
                for propname in scaled_property_names:
                    if propname == 'scale':
                        # scale appropriate real-world measurement from config
                        scale_factor = self.config['{}.{}'.format(
                            name, propname)]
                        if name == 'span':
                            configured_val = self.config['mower.target_length_m']
                        elif name == 'area':
                            configured_val = self.config['mower.target_area_m2']
                        prop_list.append(configured_val * scale_factor)
                    else:
                        prop_list.append(
                            self.config['{}.{}'.format(name, propname)])
                self.score_props[name] = tuple(prop_list)
            for name in measure_names:
                prop_list = []
                for propname in meas_property_names:
                    prop_list.append(
                        self.config['{}.{}'.format(name, propname)])
                self.score_props[name] = tuple(prop_list)

            # fence polygons
            fence_polygon_percent = self.config['lawn.fence']
            self.log('re_init about to construct fence polygons, data mapper {}'.format(
                self.data_mapper), True)  # log memory
            _outer_darkzone_polygon_m, self.outer_darkzone_polygon_px = get_polygons_from_pc(
                fence_polygon_percent,
                arena_width_m,
                arena_length_m,
                constants.DARK_ZONE_FENCE_BUFFER_PERCENT,  # percentage growth factor
                constants.DARK_ZONE_MIN_SEGMENT_PERCENT,
                data_mapper=self.data_mapper,
                logger=self.pxm_logger,
                debug=False
            )
            self.log('outer dark zone constructed')

            # fence mask full-res
            self.fence_mask_img = get_fence_mask_surface(
                img_arr_cols,
                img_arr_rows,
                self.outer_darkzone_polygon_px,
                ImageFont.truetype(self.font_path, 20),
                like_arr=None,
                debug=False,
                logger=self.pxm_logger
            )
            # fence mask display-res
            adr = self.config['optical.analysis_display_ratio']
            self.fence_mask_display_img = get_fence_mask_surface(
                display_cols,
                display_rows,
                [p // adr for p in self.outer_darkzone_polygon_px],
                ImageFont.truetype(self.font_path, 20),
                like_arr=None,
                debug=False,
                logger=self.pxm_logger
            )
            self.log('fence masks constructed')

            self.fence_mask_array = np.asarray(self.fence_mask_img, bool)
            self.fence_mask_display_array = np.asarray(
                self.fence_mask_display_img, bool)
            if constants.DEBUG_SAVE_IMAGE_LEVEL > 0:
                self.fence_mask_img.save(
                    self.tmp_folder_path + 'fence-mask.jpg')
                self.fence_mask_display_img.save(
                    self.tmp_folder_path + 'fence-mask-display.jpg')

            # create viewport for windowing
            self.viewport = Viewport()

            # reset last visited node?
            if constants.RESET_LAST_VISITED_NODE_ON_PROFILE_CHANGE:
                self.config['_current.last_visited_route_node'] = None

            # restart governor
            self.log('re_init un-pausing governor...')
            self.run_governor = True

            self.log('re_init complete')
            if first_time:
                print('Proxymow Server successfully started! Use CTRL-C to terminate.')
                print('Point your browser at http://{}:{}'.format(socket.gethostname(), cherrypy.server.socket_port))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in pxm re_init: ' +
                           str(e) + ' on line ' + str(err_line))

    def handle_GET(self, *_args, key):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        if key == '*':
            return str(self.config)
        elif key == 'keys':
            return str(self.config.keys())
        elif key in vars(self):
            self.log('GET Dict: ' + str(key))
            inst_var = vars(self)[key]
            json_str = json.dumps(inst_var)
            return json_str
        elif key.split('.')[-1].isnumeric():
            raise cherrypy.HTTPError(404)
        elif key in self.config:
            value = self.config[key]
            if value is not None:
                if isinstance(value, list):
                    json_str = json.dumps(value, default=lambda o: {
                                          k: v for k, v in o.__dict__.items() if not k.startswith('_')})
                    return json_str
                else:
                    return str(value)
            else:
                raise cherrypy.HTTPError(404)
        elif '.'.join(key.split('.')[:-1]) in self.config:
            key_parts = key.split('.')
            coll_key = '.'.join(key_parts[:-1])
            rid = key_parts[-1]
            value = [o for o in self.config[coll_key]
                     if o.__dict__[o.__class__.pk_att_name] == rid]
            if value is not None:
                if isinstance(value, list):
                    json_str = json.dumps(value, default=lambda o: {
                                          k: v for k, v in o.__dict__.items() if not k.startswith('_')})
                    return json_str
                else:
                    return str(value)
            else:
                raise cherrypy.HTTPError(404)
        else:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def handle_POST(self, *_args, key, value):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.log('POST: ' + str(key) + '=' + str(value))
        if key in self.config:
            try:
                self.config.add(key, value)
            except MissingClassException:
                self.log_error('POST CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' missing class')
                raise cherrypy.HTTPError(500)
            except DuplicateRecordException:
                self.log_error('POST CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' duplicate record')
                raise cherrypy.HTTPError(404)
            except CollectionNotExtensibleException:
                self.log_error('POST CMD: ' + str(key) + ' Value: ' +
                               str(value) + ' collection not extensible')
                raise cherrypy.HTTPError(500)

            return key + ' => ' + value
        else:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def handle_PATCH(self, *_args, key, value):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.log('PATCH: ' + str(key) + '=' + str(value))
        resp = '-1'  # assume failure
        try:
            key_parts = key.split('.')
            coll_path = '.'.join(key_parts[0:-1])  # strip id
            is_valid_key = key in self.config or coll_path in self.config
        except Exception:
            pass

        if is_valid_key:
            self.log('PATCH CMD: ' + str(key) + ' updating...')
            try:
                self.config.patch(key, value)
            except MissingClassException:
                self.log_error('PATCH CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' missing class')
                raise cherrypy.HTTPError(500)
            except RecordNotFoundException:
                self.log_error('PATCH CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' record not found')
                raise cherrypy.HTTPError(404)
            except AttributeNotFoundException:
                self.log_error('PATCH CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' attribute not found')
                raise cherrypy.HTTPError(500)
            except CollectionNotUpdatableException:
                self.log_error('PATCH CMD: ' + str(key) + ' Value: ' +
                               str(value) + ' collection not updatable')
                raise cherrypy.HTTPError(500)
            except ProxymowException:
                self.log_error('PATCH CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' update failed')
                raise cherrypy.HTTPError(500)
            except Exception:
                self.log_error('PATCH CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' update error')
                raise cherrypy.HTTPError(500)
            self.log('PATCH CMD: ' + str(key) + ' Value Written: ' +
                     str(value) + ' updated successfully')
            resp = key + ' => ' + value
        return resp

    def populate_nested_element(self, element, jdict):

        # need to identify element's class
        klass = Morphable.get_klass(element.tag)

        for k, v in jdict.items():

            if type(v) is dict:

                child_elem = element.find(k)
                if child_elem is not None:
                    self.populate_nested_element(child_elem, v)
                else:
                    self.settings_log.debug(
                        'populate_nested_element: no child element ' + k)
                    # need to identify child element's class and siblings
                    child_klass = Morphable.get_klass(k)
                    siblings = child_klass.siblings()
                    self.settings_log.info(
                        'populate_nested_element: siblings: ' + str(siblings))
                    # is missing child element sibling?
                    for sib_class in siblings:
                        sib_class_name = sib_class.__name__
                        self.settings_log.info(
                            'populate_nested_element searching for class:' + sib_class_name)
                        sib_var_name = sib_class.variable_name()
                        sib_child_elem = element.find(sib_var_name)
                        if sib_child_elem is not None:
                            self.settings_log.info(
                                'populate_nested_element removing redundant sibling {0}'.format(sib_child_elem.tag))
                            element.remove(sib_child_elem)
                    repl_elem = ET.Element(k)
                    element.append(repl_elem)
                    self.populate_nested_element(repl_elem, v)

            elif k in element.attrib:
                element.set(k, str(v))
                self.settings_log.info(
                    'populate_nested_element replacement: att={0} = {1}'.format(k, element.attrib[k]))
            elif element.find(k) is not None:
                # writing item that is not an attribute - must be child cdata
                element.find(k).text = ET.CDATA(str(v))
                self.settings_log.info(
                    'populate_nested_element: cdata element={0}'.format(k))
            elif klass is not None and k in vars(klass()):
                element.set(k, str(v))
                self.settings_log.info(
                    'populate_nested_element creation: att={0} = {1}'.format(k, element.attrib[k]))
            else:
                self.settings_log.warning(
                    'Error in populate_nested_element: {0} is neither attribute nor child element'.format(k))

    @cherrypy.expose
    def handle_x_PATCH(self, *args, **kwargs):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.settings_log.info('handle_x_PATCH: ' +
                               str(args) + '=' + str(kwargs))
        resp = '-1'  # assume failure
        key = '/'.join(args[1:])
        value = kwargs['value']
        try:
            element = self.config.query_xpath(key)
            data_dict = json.loads(value)
            self.populate_nested_element(element, data_dict)
            self.settings_log.debug(ET.tostring(element, pretty_print=True))
            self.settings_log.info('handle_x_PATCH xpath update complete')
            resp = '1'
            self.settings_log.info(
                'handle_x_PATCH Full Commit Saving Config...')
            self.config.schedule_save()  # xml => file
            self.config.parse()  # reload xml => database
            if self.config.callback is not None:
                self.config.callback()
        except MissingClassException:
            self.settings_log.error(
                'X PATCH CMD: ' + str(key) + ' Value: ' + str(value) + ' missing class')
            raise cherrypy.HTTPError(500)
        except RecordNotFoundException:
            self.settings_log.error(
                'X PATCH CMD: ' + str(key) + ' Value: ' + str(value) + ' record not found')
            raise cherrypy.HTTPError(404)
        except AttributeNotFoundException:
            self.settings_log.error(
                'X PATCH CMD: ' + str(key) + ' Value: ' + str(value) + ' attribute not found')
            raise cherrypy.HTTPError(500)
        except CollectionNotUpdatableException:
            self.settings_log.error(
                'X PATCH CMD: ' + str(key) + ' Value: ' + str(value) + ' collection not updatable')
            raise cherrypy.HTTPError(500)
        except ProxymowException:
            self.settings_log.error(
                'X PATCH CMD: ' + str(key) + ' Value: ' + str(value) + ' update failed')
            raise cherrypy.HTTPError(500)

        self.settings_log.info('X PATCH CMD: ' + str(key) +
                               ' Value Written: ' + str(value) + ' updated successfully')
        return resp

    @cherrypy.expose
    def handle_x_POST(self, *args, **kwargs):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.settings_log.info('handle_x_POST: ' +
                               str(args) + '=' + str(kwargs))
        resp = '-1'  # assume failure
        key = '/'.join(args[1:])
        value = kwargs['value']
        mode = kwargs['mode']
        try:
            if mode == 'create':
                coll_node = self.config.query_xpath(key)
                module_name = coll_node.attrib.get('module')
                # look for a blueprint
                skeleton_node = self.config.cfg_root.find(
                    'blueprints/{0}'.format(module_name))
            elif mode == 'duplicate':
                skeleton_node = self.config.query_xpath(key)
                coll_node = skeleton_node.getparent()
                module_name = skeleton_node.tag
            class_name = module_name.title()
            klass = Morphable.get_klass(module_name)
            extensible_att = coll_node.attrib.get('extensible')
            expandable_att = coll_node.attrib.get('expandable')
            orderable_att = coll_node.attrib.get('orderable')
            extensible = extensible_att is not None and extensible_att == "true"
            expandable = expandable_att is not None and expandable_att == "true"
            orderable = orderable_att is not None and orderable_att == "true"
            # create a class object
            if klass is None:
                self.settings_log.debug(
                    'handle_x_POST Class non-existent - ' + class_name)
                # raise missing entity class exception
                raise MissingClassException(class_name)
            else:
                instance = klass.from_json_str(value)
                pk_name = klass.pk_att_name
                pk_val = getattr(instance, pk_name)
                dupe_filter = instance.as_xpath_filter()
                pre_existing_item_nodes = coll_node.xpath(dupe_filter)
                self.settings_log.debug(
                    'handle_x_POST pre_existing_item_nodes: ' + str(pre_existing_item_nodes))

                if pre_existing_item_nodes is not None and len(pre_existing_item_nodes) > 0:
                    # raise attempt to create duplicate exception
                    raise DuplicateRecordException(
                        '\'{0}\' Already Exists'.format(pk_val))
                elif extensible:
                    # insert new node
                    if skeleton_node is not None:
                        new_item_node = copy.deepcopy(skeleton_node)
                        data_dict = json.loads(value)
                        self.populate_nested_element(new_item_node, data_dict)
                        if isinstance(pk_val, int):
                            # then we need the next highest
                            next_index = self.config.get_next_in_seq(
                                None, module_name, pk_name)
                            new_item_node.set(pk_name, str(next_index))
                        self.settings_log.debug(
                            'handle_x_POST' + str(ET.tostring(new_item_node, pretty_print=True)))
                    else:
                        if expandable:
                            # find all nodes beyond (only works for numeric primary keys)
                            nodes_beyond_xpath = dupe_filter.replace('=', '>')
                            self.settings_log.debug(
                                'handle_x_POST nodes beyond xpath: ' + nodes_beyond_xpath)
                            nodes_beyond = coll_node.xpath(nodes_beyond_xpath)
                            self.settings_log.debug(
                                'handle_x_POST nodes beyond: ' + str(nodes_beyond))
                            # make space by moving nodes up two
                            for node_beyond in nodes_beyond:
                                node_beyond.attrib[pk_name] = str(
                                    int(node_beyond.attrib[pk_name]) + 2)
                            # emit an incremented xml node
                            new_item_node = instance.inc_index().as_xml_node()
                            self.settings_log.debug(
                                'handle_x_POST Node inserting - collection expanded to accommodate')
                        else:
                            # emit an xml node
                            new_item_node = instance.as_xml_node()
                            self.settings_log.debug(
                                'handle_x_POST Node inserting - no expansion required')

                    if orderable:
                        # then we need the next highest priority
                        pri_att_name = 'priority'
                        new_priority = self.config.get_next_in_seq(
                            coll_node, module_name, pri_att_name)
                        new_item_node.set(pri_att_name, str(new_priority))

                    # append to end
                    coll_node.append(new_item_node)
                    self.settings_log.debug('handle_x_POST Node inserted')
                else:
                    self.settings_log.debug(
                        'handle_x_POST Node non-existent, attempting to add - but collection not extensible!')
                    # raise collection not extensible exception
                    raise CollectionNotExtensibleException(key)

            self.settings_log.info('handle_x_POST xpath insert complete')
            resp = '1'
            self.settings_log.info(
                'handle_x_POST Full Commit Saving Config...')
            self.config.schedule_save()  # xml => file
            self.config.parse()  # reload xml => database
            if self.config.callback is not None:
                self.config.callback()
        except MissingClassException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: ' + str(key) +
                           ' Value: ' + str(value) + ' missing class')
            raise cherrypy.HTTPError(500, str(e))
        except DuplicateRecordException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: error' + str(key) +
                           ' Value: ' + str(value) + ' missing class')
            raise cherrypy.HTTPError(500, str(e))
        except RecordNotFoundException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: ' + str(key) +
                           ' Value: ' + str(value) + ' record not found')
            raise cherrypy.HTTPError(404, str(e))
        except AttributeNotFoundException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: ' + str(key) +
                           ' Value: ' + str(value) + ' attribute not found')
            raise cherrypy.HTTPError(500, str(e))
        except CollectionNotUpdatableException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: ' + str(key) +
                           ' Value: ' + str(value) + ' collection not updatable')
            raise cherrypy.HTTPError(500, str(e))
        except ProxymowException as e:
            self.log_error('handle_x_POST CMD: error ' + str(e))
            self.log_error('handle_x_POST CMD: ' + str(key) +
                           ' Value: ' + str(value) + ' update failed')
            raise cherrypy.HTTPError(500, str(e))

        self.log('handle_x_POST CMD: ' + str(key) +
                 ' Value Written: ' + str(value) + ' updated successfully')
        return resp

    @cherrypy.expose
    def handle_PUT(self, *_args, key, value):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.log('PUT: ' + str(key) + '=' + str(value))
        try:
            key_parts = key.split('.')
            coll_path = '.'.join(key_parts[0:-1])  # strip id
            is_valid_key = key in self.config or coll_path in self.config
        except Exception:
            pass
        if is_valid_key:
            self.log('PUT CMD: ' + str(key) + ' updating...')
            try:
                self.config[key] = value
            except MissingClassException:
                self.log_error('PUT CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' missing class')
                raise cherrypy.HTTPError(500)
            except RecordNotFoundException:
                self.log_error('PUT CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' record not found')
                raise cherrypy.HTTPError(404)
            except CollectionNotUpdatableException:
                self.log_error('PUT CMD: ' + str(key) + ' Value: ' +
                               str(value) + ' collection not updatable')
                raise cherrypy.HTTPError(500)
            except ProxymowException:
                self.log_error('PUT CMD: ' + str(key) +
                               ' Value: ' + str(value) + ' update failed')
                raise cherrypy.HTTPError(500)

            self.log('PUT CMD: ' + str(key) + ' Value Written: ' +
                     str(value) + ' updated successfully')
        else:
            self.cmds.append(key + '=' + value)
            self.log('PUT CMD: ' + str(key) + ' CMDS:' + str(self.cmds))
            try:
                value = self.process_instructions()
            except MissingClassException:
                self.log_error('PUT CMD: ' + str(key) + ' missing class')
                raise cherrypy.HTTPError(500)
            except RecordNotFoundException:
                self.log_error('PUT CMD: ' + str(key) + ' record not found')
                raise cherrypy.HTTPError(404)
            except CollectionNotUpdatableException:
                self.log_error('PUT CMD: ' + str(key) +
                               ' collection not deletable')
                raise cherrypy.HTTPError(500)

        return value

    @cherrypy.expose
    def handle_DELETE(self, *_args, key):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        try:
            self.config.delete(key)
        except MissingClassException:
            self.log_error('PUT DELETE: ' + str(key) + ' missing class')
            raise cherrypy.HTTPError(500)
        except RecordNotFoundException:
            self.log_error('PUT DELETE: ' + str(key) + ' record not found')
            raise cherrypy.HTTPError(404)
        except CollectionNotUpdatableException:
            self.log_error('PUT DELETE: ' + str(key) + ' collection not deleteable')
            raise cherrypy.HTTPError(500)
        return key + ' => ""'

    @cherrypy.expose
    def handle_x_DELETE(self, *args, **kwargs):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        self.log('handle_x_DELETE: ' + str(args) + '=' + str(kwargs))
        resp = '-1'  # assume failure
        key = '/'.join(args[1:])
        try:
            item_node = self.config.query_xpath(key)
            coll_node = item_node.getparent()
            module_name = coll_node.attrib['module']
            klass = Morphable.get_klass(module_name)
            deletable = coll_node.attrib.get('deletable') == "true"
            # create a class object
            if klass is None:
                self.settings_log.error(
                    'handle_x_DELETE Class non-existent - ' + module_name.title())
                # raise missing entity class exception
                raise MissingClassException(module_name.title())
            else:
                pk_name = klass.pk_att_name
                pk_val = item_node.attrib[pk_name]
            self.settings_log.debug(
                'handle_x_DELETE itm node: ' + str(item_node))
            if item_node is not None:
                if deletable:
                    # remove current node
                    coll_node.remove(item_node)
                    resp = "1"
                else:
                    self.settings_log.error(
                        'handle_x_DELETE Node not deleted - collection items not deletable')
                    # raise collection not deletable exception
                    raise CollectionNotDeletableException()
            else:
                self.settings_log.error(
                    'handle_x_DELETE Node not identified for deletion')
                # raise record not found exception
                raise RecordNotFoundException(pk_val)

            self.settings_log.info('handle_x_DELETE xpath deletion complete')
            self.settings_log.info(
                'handle_x_DELETE Full Commit Saving Config...')
            self.config.schedule_save()  # xml => file
            self.config.parse()  # reload xml => database
            if self.config.callback is not None:
                self.config.callback()

        except MissingClassException:
            self.log_error('handle_x_DELETE : ' + str(key) + ' missing class')
            raise cherrypy.HTTPError(500)
        except RecordNotFoundException:
            self.log_error('handle_x_DELETE : ' +
                           str(key) + ' record not found')
            raise cherrypy.HTTPError(404)
        except CollectionNotUpdatableException:
            self.log_error('handle_x_DELETE : ' + str(key) +
                           ' collection not deleteable')
            raise cherrypy.HTTPError(500)
        return resp

    def virtual_mower(self):
        # virtual mower
        while True:
            self.log('Virtual Mower Calling Main...')
            try:
                vmower.main()  # blocks
            except Exception as e:
                print(e)
        self.log('Virtual Mower Terminated')

    def process_image(self):
        while True:
            try:
                num_requests = len(self.camera_request_queue.queue)
                self.log(
                    'process_image get from queue[{0}] (blocks)...'.format(num_requests))
                cam_settings = {'queue': None}
                try:
                    cam_settings = self.camera_request_queue.get(timeout=40)
                    if cam_settings['queue'] == 'snap':
                        self.log(
                            'process_image get from snap queue released...')
                        self.log('process_image Processing Raw Image...')
                        disp_array = None
                        try:
                            disp_array = self.get_raw_image(cam_settings)
                        except Exception as e:
                            self.log_error(
                                'process_image get_raw_image error:' + str(e))
                        self.log('process_image get_raw_image complete')
                        self.camera_snap_queue.put(disp_array)
                    elif cam_settings['queue'] == 'raw':
                        self.log(
                            'process_image get from raw queue released...')
                        self.log('process_image Processing Raw Image...')
                        disp_array = None
                        try:
                            disp_array = self.get_raw_image(cam_settings)
                        except Exception as e:
                            self.log_error(
                                'process_image get_raw_image error:' + str(e))
                        self.log('process_image get_raw_image complete')
                        self.camera_raw_queue.put(disp_array)
                    elif cam_settings['queue'] == 'locate':
                        self.log(
                            'process_image get from locate queue released...')
                        self.log('process_image Obtaining Channel Arrays...')
                        try:
                            analysis_array, disp_array = self.get_chan_arrays(
                                cam_settings, grid=False, cap_display=True)
                        except Exception as e:
                            analysis_array = disp_array = None
                            self.log_error(
                                'process_image get_chan_arrays error:' + str(e))
                        self.log('process_image get_chan_arrays complete')
                        self.camera_locate_queue.put(
                            (analysis_array, disp_array))
                    elif cam_settings['queue'] == 'vision':
                        self.log(
                            'process_image get from vision queue released...')
                        self.log('process_image Obtaining Channel Arrays...')
                        try:
                            analysis_array, disp_array = self.get_chan_arrays(
                                cam_settings, grid=True, cap_display=False)
                        except Exception as e:
                            analysis_array = disp_array = None
                            self.log_error(
                                'process_image get_chan_arrays error:' + str(e))
                        self.log('process_image get_chan_arrays complete')
                        self.camera_vision_queue.put(
                            (analysis_array, disp_array))
                    else:
                        self.log_error('process_image UNKNOWN queue requested {0}'.format(
                            cam_settings['queue']))
                except queue.Empty as e:
                    if cam_settings['queue'] is None:
                        # this is an expected exception if no requests are made
                        pass
                    else:
                        self.log_warning('process_image {0} get from queue timed out'.format(
                            cam_settings['queue']), incl_mem_stats=True)
                except Exception as e:
                    raise (e)
            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                self.log_error('Error in process image: ' +
                               str(e) + ' on line ' + str(err_line))
        self.log('Process image thread loop terminated')

    def buffer_locate_snapshot(self):

        try:

            logger = logging.getLogger('locator')
            logger.info('In locator ' + str('-' * 80))

            locate_timesheet = Timesheet('locate')

            # do the heavy lifting of locating the target
            locate_snapshot = self.get_locate_snapshot(
                logger, locate_timesheet)
            motivate_pose = self.motivate_pose_buffer[-1] if len(
                self.motivate_pose_buffer) > 0 else None

            # do planning?
            if self.rules_engine is not None:
                self.nav_plan(locate_snapshot, motivate_pose,
                              logger, locate_timesheet)

                # add snapshot to buffer
                self.snapshot_buffer[locate_snapshot.ssid] = locate_snapshot

                msg = 'Locate Snapshots:\n'
                for ssk in self.snapshot_buffer:
                    ss = self.snapshot_buffer[ssk]
                    msg += '\t{0} {1} {2} |{3}|\n'.format(
                        ssk,
                        ss.ssid,
                        ss._pose.as_concise_str() if ss._pose is not None else 'None',
                        ss._extrapolated_pose.as_concise_str() if ss._extrapolated_pose is not None else 'None'
                    )
                logger.debug(msg)

            logger.debug(str(locate_timesheet))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            logger.error('Error in pxm buffer locate snapshot: ' +
                         str(e) + ' on line ' + str(err_line))

    def estimate_landing_time(self, rule, fixed_overhead=0.80):
        # note that durations may be negative for adaptive commands
        # employ fixed overhead? i.e. time taken to transmit the command
        landing_time = time.time()
        try:
            if (rule.duration_result is not None and
                not rule.stage_complete and
                not rule.auxiliary):
                if rule.duration_result > 0:
                    # duration-based delay + fixed overhead?
                    dur_delay = (rule.duration_result / 1000) + fixed_overhead
                    landing_time = time.time() + dur_delay
                else:
                    pass  # ignoring negative short duration of adaptive command
                # allow the current command landing time to reign
            else:
                dur_delay = fixed_overhead
                landing_time = time.time() + dur_delay
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.pxm_logger.error(
                'Error in estimate landing time: ' + str(e) + ' on line ' + str(err_line))

        return landing_time

    def get_current_command(self, rule, pose, ssid, in_flight, cmd_resp, is_frozen=None, is_static=None):

        try:

            # cmd for last n commands
            try:
                # fetch Progress named tuple
                progress = self.itinerary.progress(
                    (pose.arena.c_x_m, pose.arena.c_y_m))
                prog_compl_pc = max(0, progress.completed_pc)
            except Exception:
                prog_compl_pc = 0
            if self.itinerary is not None and not self.itinerary.is_complete and pose is not None:
                tgt_dest = self.itinerary.get_path_ends()[1]
                tgt_str = '({1:.2f}, {2:.2f}) {0:.0f}%'.format(
                    prog_compl_pc, tgt_dest.target_x, tgt_dest.target_y)
                delta_x = tgt_dest.target_x - pose.arena.c_x_m
                delta_y = tgt_dest.target_x - pose.arena.c_y_m
                delta_str = '{:.0f}&{:.2f}'.format(
                    diff_angles(pose.arena.t_deg, np.rad2deg(
                        np.mod(np.arctan2(delta_y, delta_x) - np.pi / 2, 2 * np.pi)), fmt=1),
                    np.hypot(delta_x, delta_y)
                )
            else:
                tgt_str = ''
                delta_str = ''
            rule_esc = rule.cmd.endswith('+')
            msg = '{: >4} {: >17}=>{: >10} {: >9} {}{}{} {}'.format(
                ssid,
                pose.as_concise_str() if pose is not None else '@()',
                tgt_str,
                delta_str,
                rule.cmd if in_flight else rule.cmd.upper().replace('MS', 'ms'),
                '^' if cmd_resp is None else '',
                '...' if is_static is not None and not is_static else '',
                'Frozen' if not rule_esc and is_frozen is not None and is_frozen else ''
            )
            cmd_text = datetime.datetime.now().strftime("%H:%M:%S") + ' ' + msg.strip()
            return cmd_text

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in get_current_command: ' +
                           str(e) + ' on line ' + str(err_line))

    def get_compressed_command(self, rule, pose, in_flight, cmd_resp, is_frozen=None, is_static=None):

        try:

            # commpressed cmd for last n commands
            msg = '{: >17} {}{}{} {}'.format(
                pose.as_concise_str() if pose is not None else '@()',
                rule.cmd if in_flight else rule.cmd.upper().replace('MS', 'ms'),
                '^' if cmd_resp is None else '',
                '...' if is_static is not None and not is_static else '',
                'Frozen' if is_frozen is not None and is_frozen else ''
            )
            cmd_text = datetime.datetime.now().strftime(":%S") + ' ' + msg.strip()
            return cmd_text

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in get_compressed_command: ' +
                           str(e) + ' on line ' + str(err_line))

    def log_aug_cur_cmd(self, rule, in_flight, cmd_resp, is_frozen=None, is_static=None):
        '''
            cache and log command if is_frozen is None, else augment last entry
        '''
        LastCommandData = namedtuple(
            'LastCommandData', 'Rule, Pose, SSID, InFlight, CmdResp')

        try:
            if is_frozen is None:
                # cache and log
                pose = self.snapshot_buffer.latest_pose()
                ssid = self.snapshot_buffer.latest_ssid()
                self.cached_history_cmd = LastCommandData(
                    deepcopy(rule), pose, ssid, in_flight, cmd_resp)
                cmd_text = self.get_current_command(
                    rule, pose, ssid, in_flight, cmd_resp)
                trace_rules(cmd_text)
                self.rules_engine.last_n_commands.append(cmd_text)
                self.rules_engine.lclogger.info(cmd_text)
                # compress cmd for mobile history
                comp_cmd_text = self.get_compressed_command(
                    rule, pose, in_flight, cmd_resp)
                self.rules_engine.last_n_comp_commands.append(comp_cmd_text)
            else:
                # augment history command with updated state?
                if len(self.rules_engine.last_n_commands) > 0 and 'cached_history_cmd' in vars(self) and self.cached_history_cmd is not None:
                    hist_cmd = self.rules_engine.last_n_commands[-1]
                    (rule, pose, ssid, in_flight,
                     cmd_resp) = self.cached_history_cmd
                    if rule.is_executable and 'Route Elapsed' not in hist_cmd:
                        cmd_text = self.get_current_command(
                            rule, pose, ssid, in_flight, cmd_resp, is_frozen, is_static)
                        trace_rules(cmd_text)
                        self.rules_engine.last_n_commands[-1] = cmd_text
                        self.rules_engine.lclogger.info(cmd_text)
                        # compress cmd for mobile history
                        comp_cmd_text = self.get_compressed_command(
                            rule, pose, in_flight, cmd_resp)
                        self.rules_engine.last_n_comp_commands[-1] = comp_cmd_text
                    self.cached_history_cmd = None  # only one augmentation allowed
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in log_aug_cur_cmd: ' +
                           str(e) + ' on line ' + str(err_line))

    def process_arrival(self):
        try:
            # calculate route elapsed time
            if self.rules_engine.route_started_time == -1:
                route_elapsed_time = 0
            else:
                route_elapsed_time = time.time() - self.rules_engine.route_started_time
                elapsed_mins, elapsed_secs = divmod(route_elapsed_time, 60)
                elapsed_hrs, elapsed_mins = divmod(elapsed_mins, 60)
                msg = '{} Route Elapsed {:d}:{:02d}:{:02d}'.format(
                    '     ',
                    int(elapsed_hrs),
                    int(elapsed_mins),
                    int(elapsed_secs))
                trace_rules(msg)
                self.log_debug(msg)
                cmd_text = datetime.datetime.now().strftime("%H:%M:%S") + ' ' + msg
                self.rules_engine.last_n_commands.append(cmd_text)
                self.rules_engine.last_n_comp_commands.append(cmd_text)
                self.rules_engine.lclogger.info(cmd_text)
            # update last visited node - using non-committing prefix
            if self.drive['path'] == 'Route':
                # position()
                self.config['_current.last_visited_route_node'] = self.itinerary.dest_ptr
            if not self.drive_cancel:
                self.drive["state"] = 'Reached Destination!'
            # move on to next node...
            if self.itinerary is not None:
                self.itinerary.advance_pointer()
                if self.itinerary.is_complete:
                    # calculate route elapsed time
                    if self.rules_engine.route_started_time == -1:
                        route_elapsed_time = 0
                    else:
                        route_elapsed_time = time.time() - self.rules_engine.route_started_time
                        elapsed_mins, elapsed_secs = divmod(route_elapsed_time, 60)
                        elapsed_hrs, elapsed_mins = divmod(elapsed_mins, 60)
                        msg = '{} Route Completed in {:d}:{:02d}:{:02d}'.format(
                            '     ',
                            int(elapsed_hrs),
                            int(elapsed_mins),
                            int(elapsed_secs))
                        trace_rules(msg)
                        self.log_debug(msg)
                        cmd_text = datetime.datetime.now().strftime("%H:%M:%S") + ' ' + msg
                        self.rules_engine.last_n_commands.append(cmd_text)
                        self.rules_engine.last_n_comp_commands.append(cmd_text)
                        self.rules_engine.lclogger.info(cmd_text)
                    if self.telem is not None and self.telem != {}:
                        direct_drive_disable_cutters = 'cutter(0, -1)'
                        self.log(
                            'action completed destination list - turning cutters off...')
                        self.cmds.append(
                            'direct-drive={0}'.format(direct_drive_disable_cutters))
                        self.process_instructions()
                        self.telem = fetch_telemetry(self.config, self.udp_socket)
                    if self.drive['path'] == 'Route':
                        self.config['_current.last_visited_route_node'] = None
                    # set mower to None - save battery!
                    if self.drive['path'] != 'Single':
                        self.config['current.mower'] = 'None'
                        # self.snapshot_buffer.clear()
                        # self.motivate_pose_buffer.clear()
                    self.drive['path'] = None
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in process arrival: ' +
                           str(e) + ' on line ' + str(err_line))

    def log_arrival(self, pose):

        try:
            if self.itinerary is not None:
                dest_cnt = self.itinerary.outstanding
                total_destinations = self.itinerary.num_destinations
                tgt_point = self.itinerary.get_current_path()[2:4]
                if not all(tgt_point):
                    tgt_point = (0, 0)
            else:
                dest_cnt = 0
                total_destinations = 0
                tgt_point = (0, 0)

            if pose is not None and self.itinerary is not None:
                progress = self.itinerary.progress(
                    (pose.arena.c_x_m, pose.arena.c_y_m))
                prog_compl_pc = max(0, progress.completed_pc)
                pose_str = '{0:.0f}@({1:.2f}, {2:.2f})'.format(
                    pose.arena.t_deg, pose.arena.c_x_m, pose.arena.c_y_m)
            else:
                prog_compl_pc = -1
                pose_str = '-1@()'
            self.log_debug('progress completed: {} target point: {}'.format(prog_compl_pc, tgt_point))
            tgt_str = '({1:.2f}, {2:.2f}) {0:.0f}%'.format(
                prog_compl_pc, *tgt_point)
            if self.rules_engine.stage_started_time == -1:
                stage_completed_time = 0
            else:
                stage_completed_time = time.time() - self.rules_engine.stage_started_time
            msg = '{} {}=>{}   Stage {} of {} Completed in {:.0f} seconds'.format(
                '     ',
                pose_str,
                tgt_str,
                total_destinations - dest_cnt + 1,
                total_destinations,
                stage_completed_time)
            trace_rules(msg)
            self.log_debug(msg)
            cmd_text = datetime.datetime.now().strftime("%H:%M:%S") + ' ' + msg
            self.rules_engine.last_n_commands.append(cmd_text)
            self.rules_engine.lclogger.info(cmd_text)
            # compressed version
            msg = '{} Stage {} of {} Completed'.format(
                pose_str,
                total_destinations - dest_cnt + 1,
                total_destinations)
            cmd_text = datetime.datetime.now().strftime(":%S") + ' ' + msg
            self.rules_engine.last_n_comp_commands.append(cmd_text)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in log_arrival: ' +
                           str(e) + ' on line ' + str(err_line))

    def detect_frozen(self, last_n_exec_poses):
        '''
            returns True, False
        '''
        is_frozen = False
        num_poses = len(last_n_exec_poses)
        buffer_full = (num_poses == last_n_exec_poses.maxlen)
        if buffer_full:
            # find tips and tails
            tips = [(p.arena.tip_x_m, p.arena.tip_y_m)
                    for p in last_n_exec_poses]
            tails = [(p.arena.tail_x_m, p.arena.tail_y_m)
                     for p in last_n_exec_poses]
            centres = [(p.arena.c_x_m, p.arena.c_y_m)
                       for p in last_n_exec_poses]
            for i, p in enumerate(last_n_exec_poses):
                self.log_debug('Frozen Detector {} {} ({:.2f}, {:.2f}) ---> ({:.2f}, {:.2f})'.format(
                    i, p.as_concise_str(), tails[i][0], tails[i][1], tips[i][0], tips[i][1]))

            # find mean pose - note span is not accurate
            mean_tip = np.mean(np.array(tips), axis=0)
            mean_tail = np.mean(np.array(tails), axis=0)
            mean_pose = poses.Pose.from_tip_tail(mean_tip, mean_tail)
            mean_heading = mean_pose.arena.t_rad
            self.log_debug('Frozen Detector Means ({:.2f}, {:.2f})m ---> ({:.2f}, {:.2f})m => {}'.format(
                *mean_tail, *mean_tip, mean_pose.as_concise_str()))

            # location standard deviation as spread of centres
            sd_c_xy = np.std(np.array(centres), axis=0)
            self.log_debug('Frozen Detector xy location[m] deviations from centre spread: {}'.format(
                np.round(sd_c_xy, 2)))
            sd_by_location = np.hypot(sd_c_xy[0], sd_c_xy[1])
            self.log_debug(
                'Frozen Detector sd by location: {:.2f}m'.format(sd_by_location))

            # heading standard deviation relative to mean heading

            # find relative angle from pose to mean heading
            rel_angles_rad = [diff_angles(
                p.arena.t_rad, mean_heading) for p in last_n_exec_poses]
            rel_angles_deg = [round(degrees(rh)) for rh in rel_angles_rad]
            self.log_debug(
                'Frozen Detector relative heading angles: {} degrees'.format(rel_angles_deg))
            sd_hdg = np.std(rel_angles_deg)
            self.log_debug(
                'Frozen Detector heading sd: {:.2f} degrees'.format(sd_hdg))

            lin_frozen = sd_by_location < constants.FROZEN_DISTANCE_THRESHOLD_METRES
            ang_frozen = sd_hdg < constants.FROZEN_ANGLE_THRESHOLD_DEGREES
            is_frozen = lin_frozen and ang_frozen

            self.log_debug('Frozen Detector summary: {:.3f} < {:.3f}m {:>5} and {:.3f} < {:.3f}deg {:>5} => Frozen = {:>5}'.format(
                sd_by_location,
                constants.FROZEN_DISTANCE_THRESHOLD_METRES,
                str(lin_frozen),
                sd_hdg,
                constants.FROZEN_ANGLE_THRESHOLD_DEGREES,
                str(ang_frozen),
                str(is_frozen)
            )
            )
        return is_frozen

    def detect_stasis(self):
        is_static = False
        latest_delta = self.snapshot_buffer.latest_pose_delta()
        if latest_delta is not None:
            latest_linear_displacement, latest_angular_displacement_rad = latest_delta
            latest_unmoved = latest_linear_displacement < constants.FROZEN_DISTANCE_THRESHOLD_METRES
            latest_angular_displacement_deg = abs(
                degrees(latest_angular_displacement_rad))
            latest_unturned = latest_angular_displacement_deg < constants.FROZEN_ANGLE_THRESHOLD_DEGREES
            penult_delta = self.snapshot_buffer.penultimate_pose_delta()
            if penult_delta is not None:
                penult_linear_displacement, penult_angular_displacement_rad = penult_delta
                penult_unmoved = penult_linear_displacement < constants.FROZEN_DISTANCE_THRESHOLD_METRES
                penult_angular_displacement_deg = abs(
                    degrees(penult_angular_displacement_rad))
                penult_unturned = penult_angular_displacement_deg < constants.FROZEN_ANGLE_THRESHOLD_DEGREES
                _unmoved = latest_unmoved and penult_unmoved
                _unturned = latest_unturned and penult_unturned
                # static over 3 poses - excessive?
                # static over 2 poses
                is_static = latest_unmoved and latest_unturned

        return is_static

    def governor(self):
        '''
            main loop that governs locating, planning and executing
        '''
        while True:
            logger = self.pxm_logger
            rung_index = 0
            landing_time = 0  # kick-start
            is_escalating = False
            next_escalation = 0
            while self.run_governor:

                try:
                    no_mower = self.config['current.mower'] is None or self.config['current.mower'] == 'None'
                    if no_mower and ('log_no_mower' not in vars(self) or time.time() > self.log_no_mower):
                        logger.info('In locator current mower: ' +
                                    str(self.config['current.mower']))
                        self.log_no_mower = time.time() + 300  # only log every 5 minutes
                    # if there is no mower selected we want to preserve resources for remote access!
                    if no_mower:
                        self.drive["state"] = 'Dormant'
                    else:

                        # initialise run elapsed time
                        start_time = time.time()

                        timesheet = Timesheet('governor')
                        operation_active = True

                        # obtain latest pose
                        self.buffer_locate_snapshot()
                        timesheet.add('snapshot buffered')

                        # assess progress using motivate pose
                        is_frozen = self.detect_frozen(
                            self.motivate_pose_buffer)
                        logger.info(
                            'Governor Frozen detection: {}'.format(is_frozen))
                        timesheet.add('frozen progress detected')

                        is_static = self.detect_stasis()
                        timesheet.add('stasis progress detected')

                        # determine landed state from estimated landing time
                        est_time_to_arrival = landing_time - time.time()
                        landed = est_time_to_arrival <= 0

                        if landed:
                            if self.rules_engine is not None and not self.drive_pause and self.drive['path'] is not None:
                                self.log_aug_cur_cmd(
                                    None, None, None, is_frozen, is_static)

                            # call mower for telemetry?
                            no_mower = self.config['current.mower'] is None or self.config['current.mower'] == 'None'
                            telem_demanded = time.time() - self.telemetry_updated > constants.MOWER_TELEMETRY_PERIOD_SECS
                            if not no_mower and telem_demanded:
                                logger.info(
                                    'Fetching Telemetry: period exceeded, governor predicts landed')
                                self.telem = fetch_telemetry(
                                    self.config, self.udp_socket)
                                self.telemetry_updated = time.time()
                                timesheet.add('telemetry fetched')

                        if constants.ESCALATION_ENABLED:
                            if (is_frozen and
                                (not is_escalating or time.time() > next_escalation) and
                                not self.drive_pause and
                                self.telem is not None and
                                    len(self.telem.keys()) > 0):
                                logger.info(
                                    'Governor: frozen assessment entered state Frozen, escalating...')
                                # try escalation?
                                rung_index += 1
                                is_escalating = True
                                next_escalation = time.time() + 15
                                msg = 'Escalating to rung {}'.format(
                                    rung_index
                                )
                                self.drive["state"] = msg
                                logger.info(
                                    'Governor: escalation status {}...'.format(msg))
                                sleep(5)  # pause to smooth intervention
                            elif is_escalating and not is_static:
                                # cancel escalation
                                logger.info(
                                    'Governor: frozen assessment Cancelling Escalation')
                                self.drive["state"] = 'Cancelling Escalation'
                                sleep(0)
                                rung_index = 0
                                is_escalating = False
                            elif is_escalating:
                                # escalation underway
                                logger.info(
                                    'Governor: frozen assessment escalation in progress rung {}...'.format(rung_index))
                            else:
                                # no escalation
                                logger.info(
                                    'Governor: frozen assessment escalation not required')

                        if self.snapshot_buffer.latest_pose() is None:
                            logger.info('Governor channel: No Pose')
                        elif self.telem == {}:
                            logger.info('Governor channel: No Telemetry')
                        else:
                            # select rule
                            if landed:
                                selected_rule = self.rules_engine.select(
                                    scope=RuleScope.STATIONARY,
                                    trace=operation_active
                                )
                            elif not is_escalating:
                                selected_rule = self.rules_engine.select(
                                    scope=RuleScope.IN_FLIGHT,
                                    trace=operation_active
                                )
                            else:
                                selected_rule = None

                            if selected_rule is not None:

                                arrived = selected_rule.stage_complete  # prime for processing

                                if selected_rule.is_executable:

                                    # apply escalation?
                                    selected_rule._rung_index = min(
                                        rung_index, selected_rule.num_rungs)

                                    timesheet.add('rule selected')

                                    if self.drive_pause and not self.drive_step and not selected_rule.auxiliary:
                                        self.drive["state"] = 'Pausing Drive...'
                                    elif self.itinerary is not None and self.itinerary.plan_only:
                                        self.drive["state"] = 'Planning...'
                                    else:
                                        # queue starting pose
                                        self.motivate_pose_buffer.append(
                                            self.snapshot_buffer.latest_pose())

                                        self.rules_engine.last_command = (
                                            selected_rule.left_speed_result, selected_rule.right_speed_result, selected_rule.duration_result)
                                        self.rules_engine.last_command_code = Movement.get_movement_code(
                                            selected_rule.left_speed_result,
                                            selected_rule.right_speed_result
                                        ).name

                                        # execute command
                                        timesheet.add(
                                            'transmitting selected rule command...')
                                        arrived, resp = selected_rule.execute(
                                            self.config, self.udp_socket, True)  # trace
                                        logger.info(
                                            'Governor rule {} [{}] executed arrived: {} response: {}'.format(
                                                selected_rule.cmd,
                                                self.snapshot_buffer.latest_ssid(),
                                                arrived,
                                                resp)
                                            )
                                        timesheet.add(
                                            'selected rule command acknowledged')

                                        # expecting an ACK response - but may get None...
                                        if resp is None:
                                            # update telemetry, which will halt escalation
                                            self.telem = {}
                                            logger.info(
                                                'Governor rule unacknowledged: updating telemetry status')

                                        # if command is auxiliary - hasten telemetry refresh
                                        if selected_rule.auxiliary:
                                            logger.info(
                                                'Governor rule auxiliary: telemetry refresh')
                                            self.telem = fetch_telemetry(
                                                self.config, self.udp_socket)
                                            self.telemetry_updated = time.time()

                                        # calculate estimated landing time
                                        landing_time = self.estimate_landing_time(
                                            selected_rule, fixed_overhead=0.8)
                                        timesheet.add('landing time estimated')

                                        self.log_aug_cur_cmd(
                                            selected_rule, selected_rule.scope == RuleScope.IN_FLIGHT.value, resp)
                                        timesheet.add('rule logged')

                                if arrived:
                                    self.log_arrival(
                                        self.snapshot_buffer.latest_pose())
                                    timesheet.add('arrival logged')
                                    self.process_arrival()
                                    self.rules_engine.stage_started_time = time.time()  # re-init
                                    timesheet.add('arrival processed')

                                self.drive_step = False

                        # commit snapshot
                        cur_snapshot = self.snapshot_buffer.latest()
                        if cur_snapshot is not None:
                            cur_snapshot._rules = copy.deepcopy(
                                self.rules_engine.rules)
                            cur_snapshot._growth = SnapshotGrowth.PLANNED

                            # update frame time
                            cur_snapshot.run_elapsed_secs = time.time() - start_time
                        timesheet.add('locate snapshot committed')

                        self.log_debug(timesheet)

                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    logger.error('Error in pxm governor: ' +
                                 str(e) + ' on line ' + str(err_line))
            sleep(4)

    def compile_location_stats(self, logger, pose):
        location_stat_count = 0
        location_quality = 100
        try:
            if pose is None:
                # count failed attempts?
                if None in Snapshot.location_stats:
                    Snapshot.location_stats[None] += 1
                else:
                    Snapshot.location_stats[None] = 1
                self.location_props['not_found_count'] += 1
                logger.debug(
                    'Null Pose - {0} Not Founds'.format(self.location_props['not_found_count']))
                if self.location_props['not_found_count'] > constants.NOT_FOUND_RESET_COUNT:
                    logger.debug(
                        'Null Pose - Not Founds Exceeded Threshold - Unlocking...')
                    self.location_props['not_found_count'] = 0
            else:
                pose_str = str(pose)
                logger.debug(pose_str)
                # get location key
                key = pose.location_key
                # count success?
                if key in Snapshot.location_stats:
                    Snapshot.location_stats[key] += 1
                else:
                    Snapshot.location_stats[key] = 1

                location_stat_count = sum(Snapshot.location_stats.values())
                if None not in Snapshot.location_stats:
                    Snapshot.location_stats[None] = 0
                location_quality = round(
                    100 * (1 - (Snapshot.location_stats[None] / location_stat_count)), 1)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            logger.error('Error in compile_location_stats: ' +
                         str(e) + ' on line ' + str(err_line))
            logger.error('Error in compile_location_stats: ' + pose_str)

        return location_stat_count, location_quality

    def get_locate_snapshot(self, logger, timesheet=Timesheet()):

        self.log('In locate ' + str('-' * 80))

        # Save images for debugging - slows things down
        debug_image_level = constants.DEBUG_SAVE_IMAGE_LEVEL
        # Number of generations of images for debugging
        debug_image_gens = constants.DEBUG_SAVE_IMAGE_GENERATIONS
        debug_level = constants.DEBUG_LOCATE_LEVEL
        # Exclude targets beyond fence plus border
        fence_masking = constants.FENCE_MASKING
        try:
            # create skeleton snapshot so we get an ssid
            locate_snapshot = Snapshot(self.snapshot_buffer, logger=logger)
            sid = locate_snapshot.ssid % debug_image_gens if debug_image_level > 0 else locate_snapshot.ssid

            if 'camera' in vars(self):

                # obtain the configured camera settings
                cam_settings = self.camera.settings.clone(self.config)

                # add queue and client details
                cam_settings['queue'] = 'locate'
                cam_settings['client'] = 'locate'
                logger.info('locate camera settings: ' + str(cam_settings))

                cam_settings['virtual_mower'] = self.config['mower.type'] in ['virtual', 'hybrid']

                # queue request for camera
                logger.info('pxm locate placing request on queue...')
                timesheet.add('queueing camera request')
                self.camera_request_queue.put(cam_settings)
                logger.info('pxm locate getting image from queue (blocks)...')
                analysis_array, img_array = self.camera_locate_queue.get(
                    timeout=30)
                if analysis_array is None:
                    timesheet.add('camera request complete but failed')
                else:
                    timesheet.add('camera request complete')

                    check_due = (
                        (time.time() - self.when_checked) > constants.ARCHIVE_IMAGE_RATE_SECS)
                    periodic_img_due = debug_image_level > 0 and check_due
                    archive_image_due = self.drive['path'] is not None and not self.drive_pause and check_due
                    if constants.ARCHIVE_IMAGE_RATE_SECS > 0 and (periodic_img_due or archive_image_due):
                        # update check thresholds due
                        if check_due:
                            self.when_checked = time.time()
                        raw_img = Image.fromarray(analysis_array)
                        disp_img = Image.fromarray(img_array)
                        if periodic_img_due:
                            raw_img.save(self.tmp_folder_path + os.path.sep + 'raw.jpg',
                                         optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
                        if archive_image_due:
                            # add to archive? will only archive images during excursions...
                            raw_img.save(self.image_folder_path_name + os.path.sep + 'raw-{0}.jpg'.format(
                                self.archive_image_count), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
                            disp_img.save(self.image_folder_path_name + os.path.sep + 'disp-{0}.jpg'.format(
                                self.archive_image_count), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
                            self.archive_image_count = (
                                self.archive_image_count + 1) % constants.ARCHIVE_IMAGE_MAX_COUNT
                        timesheet.add('raw image archived')

                    if constants.ANIMAL_MIN_PT_COUNT > 0 and self.drive['path'] is not None and self.drive['path'] != 'Single' and not self.drive_pause:
                        animals = lores_contours(
                            analysis_array, min_pt_count=constants.ANIMAL_MIN_PT_COUNT, debug=True, logger=logger)
                        timesheet.add(
                            '{} animals counted'.format(len(animals)))

                        if len(animals) > 0:
                            logger.info('pxm locate spotted animal(s)')
                            msg = 'Pausing/Cutter Off for Animals'
                            self.rules_engine.last_n_commands.append(msg)
                            self.rules_engine.last_n_comp_commands.append(msg)
                            self.rules_engine.lclogger.info(msg)

                            if self.telem is not None and self.telem != {}:
                                try:
                                    cutter1_state = self.telem['cutter1']
                                    cutter2_state = self.telem['cutter2']
                                except Exception:
                                    cutter1_state = cutter2_state = False

                                logger.info('animals cutter states: {} {}'.format(
                                    cutter1_state, cutter2_state))

                                # turn off cutters anyway
                                direct_drive_disable_cutters = 'cutter(0, -1)'
                                logger.info('animals - turning off cutters...')
                                self.cmds.append(
                                    'direct-drive={0}'.format(direct_drive_disable_cutters))
                                self.process_instructions()
                            self.drive_pause = True
                            self.drive["state"] = 'Animals!'

                    # get latest snapshot for pose and windowing calculations
                    latest_snapshot = self.snapshot_buffer.latest()

                    if (latest_snapshot is not None and latest_snapshot._pose is not None):
                        # viewport from pose
                        hsid = '{0}B'.format(sid)
                        zoom_scale_factor = 1
                        p = latest_snapshot._pose

                        # tightly around target...
                        self.viewport = Viewport.from_pose(
                            p, analysis_array.shape, hsid)

                        # expanded viewport from pose
                        if self.viewport is not None:
                            self.viewport.resize(constants.RESIZE_POSE_TO_VIEWPORT)
                            logger.info('pxm locate getting expanded viewport from latest pose: {0}'.format(
                                self.viewport))
                        else:
                            self.viewport = Viewport()  # Null Viewport
                            logger.info(
                                'pxm locate could not get expanded viewport from latest pose - using Null viewport')

                        vp_prospect_list = [self.viewport]
                        timesheet.add('viewport prepared')
                    else:
                        if self.viewport is None:
                            self.viewport = Viewport()  # Null Viewport
                        elif not self.viewport.isnull:
                            if self.viewport.origin > (0, 0) and self.viewport.bottom_right < (100, 100):
                                self.viewport.resize(1.2)
                                logger.info('pxm locate expanded viewport looking for escaped target: {0}'.format(
                                    self.viewport))
                                # add delay to smooth process... 
                                sleep(1)
                            else:
                                # null the viewport - reached edge...
                                self.viewport = Viewport()  # Null Viewport
                                logger.info('pxm locate viewport grown to reach edge - reset')

                        zoom_scale_factor = 4
                        lsid = '{0}A'.format(sid)

                        # now find prospects...
                        vp_prospect_list = get_prospect_list(
                            self,
                            analysis_array,
                            zoom_scale_factor,
                            self.viewport,
                            debug_image_level,
                            debug_level,
                            logger,
                            lsid
                        )
                        # advance id marker from lo-res [A] to hi-res [B]
                        for vp in vp_prospect_list:
                            vp.index = vp.index.replace('A', 'B')

                        logger.info(
                            'pxm locate getting mask from default all - null viewport')
                        timesheet.add('get prospect list')

                    # now we can probe the prospects in full res looking for the target...
                    prospect_viewports, all_contours, filtered_contour_index, filtered_projections, pose = probe_prospect_list(
                        self,
                        sid,
                        vp_prospect_list,
                        analysis_array,
                        debug_image_level,
                        debug_level,
                        logger
                    )
                    timesheet.add('probe prospect list')

                    # update pose statistics
                    location_stat_count, location_quality = self.compile_location_stats(
                        logger, pose)
                    timesheet.add('pose stats')

                    # images
                    if fence_masking:
                        fence_masked_img_arr = (
                            img_array.T * self.fence_mask_display_array.T).T  # colour
                    else:
                        fence_masked_img_arr = img_array
                    locate_snapshot._fence_masked_img_arr = fence_masked_img_arr

                    # manually reconstruct full array
                    contour_bg_arr = fence_masked_img_arr
                    locate_snapshot._source_img_arr = contour_bg_arr
                    locate_snapshot._prospect_viewports = prospect_viewports
                    locate_snapshot._growth = SnapshotGrowth.IMAGED
                    timesheet.add('images snapshotted')

                    # contours
                    locate_snapshot._contours = all_contours
                    locate_snapshot._fltrd_contour_index = filtered_contour_index
                    locate_snapshot._fltrd_projections = filtered_projections

                    # best projection confidence
                    locate_snapshot.best_proj_conf_pc = filtered_projections[0].conf_pc if len(
                        filtered_projections) > 0 else 0
                    locate_snapshot.best_proj_found = (len(filtered_projections) > 0 and
                        filtered_projections[0].conf_pc > constants.SCORE_THRESHOLD)

                    # statistics
                    locate_snapshot.loc_stat_count = location_stat_count
                    locate_snapshot.loc_quality = location_quality
                    locate_snapshot.extrapolation_incidents = self.extrapolation_incidents

                    # contour count
                    locate_snapshot.fltrd_count = len(filtered_contour_index)
                    locate_snapshot.cont_count = len(all_contours)

                    timesheet.add('json snapshotted')

                    # augment information sent as headers

                    # update drive and environment
                    # this is for any background activity - routes may repeat this for absolute latest data
                    self.drive['cur-mower'] = self.config['current.mower']
                    if self.drive['cur-mower'] in self.config['mowers']:
                        self.drive['rot-speed'] = self.config['mower.motion.set_rotation_speed_percent']
                        self.drive['drv-speed'] = self.config['mower.motion.set_drive_speed_percent']
                        self.drive['last_cmds'] = list(
                            self.rules_engine.last_n_commands)[::-1]
                        self.drive['last_comp_cmds'] = list(
                            self.rules_engine.last_n_comp_commands)[::-1]

                    # pose
                    locate_snapshot.set_pose(pose) # sets growth => POSED
                    logger.debug('Adding pose to locate snapshot {0}: {1}'.format(
                        locate_snapshot.ssid,
                        pose.as_concise_str() if pose is not None else 'None'))

                timesheet.add('snapshot complete')

        except Empty:
            # Handle empty queue here
            err_line = sys.exc_info()[-1].tb_lineno
            logger.warning('pxm find_execute get from queue timed out on line ' + str(err_line))
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            logger.error('Error in pxm locate: ' + str(e) +
                         ' on line ' + str(err_line))

        # end of locate
        return locate_snapshot

    def update_excursion_log(self, pose, locate_snapshot, motivate_pose):
        try:
            if self.itinerary is not None:
                x1_m, y1_m, x2_m, y2_m = self.itinerary.get_current_path()[:4]

                # cutter stray - lateral error from path as a proportion of cutter diameter
                stray_m = distance_to_line(
                    pose.arena.c_x_m, pose.arena.c_y_m, x1_m, y1_m, x2_m, y2_m)
                # mean
                cutter_dia_m = self.config['mower.dimensions.cutter_dia_m']
                cutter_stray_pc = 100 * stray_m / cutter_dia_m if cutter_dia_m > 0 else -1
                try:
                    sensor_iter = iter(self.telem['sensors'].values())
                    battery_pc = next(sensor_iter)
                    loaded_pc = next(sensor_iter)
                except:
                    battery_pc = -1
                    loaded_pc = -1
                conf_pc = locate_snapshot._fltrd_projections[0].conf_pc if len(
                    locate_snapshot._fltrd_projections) > 0 else 0
                if not [v for v in (x1_m, y1_m, x2_m, y2_m) if v is None]:
                    from_to_msg = '{0:.2f}, {1:.2f}, {2:.2f}, {3:.3f}'.format(
                        x1_m, y1_m, x2_m, y2_m)
                else:
                    from_to_msg = '-1, -1, -1, -1'
                # assemble excursion message from current pose and previous prediction
                msg = '{}, {}, {}, {}, {}, {:.3f}, {:.3f}, {:.0f}, {}, {:.3f}, {:.0f}, {:.2f}, {:.2f}, {:.2f}'.format(
                    datetime.datetime.now(timezone.utc),
                    locate_snapshot.ssid,
                    motivate_pose.ssid if motivate_pose is not None and 'ssid' in vars(
                        motivate_pose) else -1,
                    self.itinerary.dest_ptr,  # position(),
                    '' if from_to_msg is None else from_to_msg,
                    pose.arena.c_x_m,
                    pose.arena.c_y_m,
                    pose.arena.t_deg,
                    self.itinerary.progress(
                        (pose.arena.c_x_m, pose.arena.c_y_m)).completed_pc,
                    pose.arena.span_m,
                    cutter_stray_pc,
                    battery_pc,
                    loaded_pc,
                    conf_pc
                )
                trace_location(msg)  # single line

                query = "INSERT INTO Excursions VALUES (DEFAULT, DEFAULT, '{}', {}, {}, {}, {}, {}, {:.3f}, {:.3f}, {:.0f}, {:.2f}, {:.2f}, {:.3f}, {:.2f})".format(
                    socket.gethostname(),
                    self.config['current.excursion'],  # excursion id
                    self.itinerary.dest_ptr,  # position(), # route id
                    motivate_pose.ssid if motivate_pose is not None and 'ssid' in vars(
                        motivate_pose) else -1,
                    locate_snapshot.ssid,
                    'NULL' if from_to_msg is None else from_to_msg,
                    pose.arena.c_x_m,
                    pose.arena.c_y_m,
                    pose.arena.t_deg,
                    battery_pc,
                    loaded_pc,
                    pose.arena.span_m,
                    conf_pc
                )
                # Get Cursor? only route and fence drives establish connection
                if self.db_connection is not None:
                    cur = self.db_connection.cursor()
                    cur.execute(query)
                    self.db_connection.commit()

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in update_excursion_log: ' +
                           str(e) + ' on line ' + str(err_line) + ' query: ' + query)

    def update_drive_state(self):

        if self.itinerary is not None:
            outstanding = self.itinerary.outstanding
            plan_only = self.itinerary.plan_only
            self.log(
                'pxm nav_plan remaining destination count: {0}'.format(outstanding))
            if not self.drive_cancel:
                self.drive["state"] = '{} {} destination{}'.format(
                    'planning' if plan_only else 'processing',
                    outstanding,
                    's'[:outstanding ^ 1]
                )

    def nav_plan(self, locate_snapshot, motivate_pose, logger, timesheet=Timesheet()):

        # start of navigation planning
        pose = locate_snapshot._pose

        try:
            if pose is not None:

                self.update_drive_state()

                self.log('pxm nav_plan building context')
                self.rules_engine.build_context(
                    locate_snapshot,
                    self.itinerary,
                    self.config,
                    self.telem,
                    True
                )
                timesheet.add('build rules engine context')

                # update excursion log
                self.update_excursion_log(pose, locate_snapshot, motivate_pose)
                timesheet.add('excursion logged')

            else:
                # Robot Not Found
                if not self.drive_cancel:
                    self.drive["state"] = ''

            # terms and rules
            locate_snapshot._strategy_name = self.rules_engine.name
            locate_snapshot._terms = copy.deepcopy(self.rules_engine.terms)
            # rules are deep copied later after selection...

            # post snapshot
            self.snapshot_buffer[locate_snapshot.ssid] = locate_snapshot

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            logger.error('Error in pxm nav_plan: ' +
                         str(e) + ' on line ' + str(err_line))

    def process_instructions(self):
        resp = None
        try:
            while len(self.cmds) > 0:
                cmd = self.cmds[0].split('=')
                name = cmd[0]
                value = cmd[1]
                del self.cmds[0]
                if name.startswith('DuplicateStrategyRule'):
                    rule_name = name.split('|')[1]
                    # duplicate rule
                    self.config.duplicate_rule(rule_name)
                    # reload
                    self.rules_engine.set_rules(self.config['strategy.rules'])
                    resp = '1'
                elif name.startswith('DeleteStrategyRule'):
                    rule_name = name.split('|')[1]
                    # delete rule
                    self.config.delete_rule(rule_name)
                    # reload
                    self.rules_engine.set_rules(self.config['strategy.rules'])
                    resp = '1'
                elif name.startswith('DeleteStrategyTerm'):
                    term_name = name.split('|')[1]
                    # delete term
                    self.config.delete_term(term_name)
                    # reload
                    self.rules_engine.set_rules(self.config['strategy.rules'])
                    resp = '1'
                elif name == 'set_speeds':
                    speeds = str(value).split('.')
                    # update mower config
                    self.log(
                        'process_instruction - set speeds to {0} {1}'.format(speeds[0], speeds[1]))
                    self.config['_mower.motion.set_rotation_speed_percent'] = int(speeds[0])
                    self.config['_mower.motion.set_drive_speed_percent'] = int(speeds[1])
                elif name == 'cancel-drive':
                    self.disconnect()  # logging database
                    self.itinerary = None
                    self.drive_cancel = True
                    self.drive["state"] = 'Cancelled'
                    self.drive['state-index'] = 1  # back up
                    self.drive['path'] = None
                    self.drive_pause = False
                    host = self.config['mower.ip'] if 'mower.ip' in self.config else None
                    port = self.config['mower.port'] if 'mower.port' in self.config else None
                    if host is not None and port is not None:
                        mower_cmd = '>sweep(0, 0, 0)'
                        self.log(
                            'process_instruction - Cancel mower cmd - {0}'.format(mower_cmd))
                        resp = despatch_to_mower_udp(
                            mower_cmd, self.udp_socket, host, port, max_attempts=2)
                        self.log(
                            'process_instruction - Cancel mower Response {0}'.format(resp))
                    # temporarily disable logging
                    contour_logger = logging.getLogger('contours')
                    contour_logger.setLevel(logging.WARNING)
                    excursion_logger = logging.getLogger('excursion')
                    excursion_logger.setLevel(logging.WARNING)
                elif name == 'reset':
                    # mid-lawn
                    self.shared.set(
                        self.config['arena.width_m'] / 2,
                        self.config['arena.length_m'] / 2,
                        0,
                        self.config['mower.axle_track_m'],
                        self.config['mower.velocity_full_speed_mps']
                    )
                    # clear down quality stats
                    Snapshot.location_stats = {}

                    # stop driving and clear pause
                    self.drive['path'] = None
                    self.drive_pause = False
                    self.drive_step = False

                    # reset viewport
                    self.viewport = Viewport()  # Null Viewport
                    self.snapshot_buffer.clear()
                elif name == 'plan':
                    # values will arrive as json list
                    data_values = json.loads(value)
                    self.log(
                        'process_instruction - Plan to {0}'.format(data_values))
                    self.itinerary = Itinerary(self.snapshot_buffer.latest_pose(), [
                                               data_values], plan_only=True, logger=self.pxm_logger)
                    self.drive['path'] = 'Plan'
                    self.drive['state-index'] = 13  # prepare to drive
                    trace_command(
                        '================================================================')
                elif name == 'plan-drive':
                    # values will arrive as json list
                    data_values = json.loads(value)
                    self.log(
                        'process_instruction - Plan and Drive to {0}'.format(data_values))
                    self.itinerary = Itinerary(self.snapshot_buffer.latest_pose(), [
                                               data_values], plan_only=False, logger=self.pxm_logger)
                    self.drive['path'] = 'Single'
                    trace_command(
                        '================================================================')
                elif name == 'drive':
                    # values will arrive as csv, or json list
                    self.log(
                        'process_instruction - Drive to value: {0}'.format(value))
                    if value.startswith('['):
                        data_values = json.loads(value)
                    else:
                        data_values = [
                            float(v) if v != 'None' and v != '' else None for v in value.split(',')]
                    self.log('process_instruction - Drive to {0} {1} {2}'.format(
                        data_values[0], data_values[1], data_values[2] if len(data_values) > 2 else -1))
                    self.itinerary = Itinerary(self.snapshot_buffer.latest_pose(), [
                                               data_values], logger=self.pxm_logger)
                    self.drive['path'] = 'Single'
                    trace_command(
                        '================================================================')
                elif name == 'pause-drive':
                    self.drive_pause = not self.drive_pause
                elif name == 'step-drive':
                    self.drive_step = True
                elif name == 'drive-route':
                    # value supplied will be the last_visited_route_node index
                    self.connect()  # logging database
                    excursion_logger = logging.getLogger('excursion')
                    contour_logger = logging.getLogger('contours')
                    if value == 'null':
                        # create new excursion id
                        self.config['_current.excursion'] = int(
                            self.config['current.excursion']) + 1
                        self.log(
                            'process_instruction - Drive around route, start new logs...')
                        # initialise route start
                        self.rules_engine.route_started_time = time.time()
                        # rotate excursion log?
                        if excursion_logger.level == logging.WARNING:
                            # rotate after first run
                            excursion_logger.handlers[0].doRollover()
                        # enable excursion log
                        excursion_logger.setLevel(self.log_level)
                        # enable contour log?
                        if constants.ENABLE_CONTOUR_LOGGING:
                            # rotate contour log?
                            if contour_logger.level == logging.WARNING:
                                # rotate after first run
                                contour_logger.handlers[0].doRollover()
                            contour_logger.setLevel(self.log_level)
                    else:
                        self.log(
                            'process_instruction - Drive around route...resume from {0}'.format(value))
                        # re-enable logs, no rotation
                        excursion_logger.setLevel(self.log_level)
                        # re-enable contour log?
                        if constants.ENABLE_CONTOUR_LOGGING:
                            contour_logger.setLevel(self.log_level)

                    self.drive['state'] = 'Driving Route'
                    self.drive['path'] = 'Route'
                    self.drive_pause = False
                    self.drive_cancel = False

                    # notify applicable strategy & pattern
                    msg = '{} Pattern: "{}" Strategy: "{}"'.format(
                        datetime.datetime.now().strftime("%H:%M:%S"),
                        self.config['current.pattern'],
                        self.config['current.strategy'])

                    self.rules_engine.last_n_commands.append(msg)
                    self.rules_engine.last_n_comp_commands.append(msg)
                    self.cached_history_cmd = None

                    # write location headings
                    trace_location(LOCATION_CSV_HEADER)
                    trace_rules(
                        '\n\n============================= Start Driving Route ============================\n')
                    route_nodes_m = self.config['lawn.route']  # metres
                    # pass current pose, so rules engine can use it
                    self.itinerary = Itinerary(
                        self.snapshot_buffer.latest_pose(), route_nodes_m, logger=self.pxm_logger)
                    route_node_count = len(route_nodes_m)
                    if value != 'null' and value != 'undefined':
                        # resume
                        last_visited = int(value)
                        if last_visited < self.itinerary.num_destinations - 1:
                            self.itinerary.dest_ptr = last_visited + 1
                    self.log('process_instruction - Drive around {0} route nodes starting at {1}'.format(
                        route_node_count,
                        self.itinerary.dest_ptr
                        )
                    )
                elif name == 'skip':
                    self.log('process_instruction - Skip Itinerary Node...')
                    self.drive["state"] = 'Skipping...'
                    self.itinerary.advance_pointer()  # .advance_pointers()
                elif name == 'capture':
                    cam_settings = self.camera.settings.clone(self.config)
                    cam_settings['queue'] = 'snap'
                    cam_settings['client'] = 'calib'
                    # align resolution mode with configuration so matrices correspond!
                    cam_settings['resolution'] = self.config['optical.resolution']
                    cam_settings['display_colour'] = True
                    display_cols = self.config['optical.display_width']
                    display_rows = self.config['optical.display_height']
                    strength = self.config['optical.undistort_strength']
                    zoom = self.config['optical.undistort_zoom']
                    cache_key = 'calib'
                    self.log('pxm calib camera view')
                    self.log('pxm calib placing request on queue...')
                    self.camera_request_queue.put(cam_settings)
                    self.log(
                        'pxm calib getting image from queue (blocks)...')
                    img_arr = self.camera_snap_queue.get(timeout=30)

                    self.undistort_mapper.populate(
                        ["unbarrel"],
                        display_cols,  # img_arr_cols,
                        display_rows,  # img_arr_rows
                        strength=strength,
                        zoom=zoom
                    )

                    out_arr = self.undistort_mapper.transform_image(img_arr)
                    img = Image.fromarray(out_arr)
                    self.calib_image_array_cache[cache_key] = out_arr

                    # save calibration image
                    img.save(self.calib_img_name.format(
                        datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')))

                elif name == 'direct-drive':
                    host = self.config['mower.ip'] if 'mower.ip' in self.config else None
                    port = self.config['mower.port'] if 'mower.port' in self.config else None
                    if host is not None and port is not None:
                        mower_cmd = '' + value
                        self.log(
                            'process_instruction - Direct Drive {0}'.format(mower_cmd))
                        resp = despatch_to_mower_udp(
                            mower_cmd, self.udp_socket, host, port, await_response=True, max_attempts=1)
                        self.log(
                            'process_instruction - Direct Drive {0}:{1} Response {2}'.format(host, port, resp))
                        self.telemetry_updated = 0  # force immediate update
                    else:
                        self.log(
                            'unable to process direct drive instruction - No host:port')
                elif name == 'enrol-hotspot':
                    hotspot_name = self.config['hotspot.name']
                    self.log(
                        'process_instruction - Attempting to Enrol in Hotspot {0}...'.format(hotspot_name))
                    host = self.config['mower.ip'] if 'mower.ip' in self.config else None
                    port = self.config['mower.port'] if 'mower.port' in self.config else None
                    if host is not None and port is not None:
                        mower_cmd = 'set_priority_essid({0})'.format(
                            hotspot_name)
                        self.log(
                            'process_instruction mower cmd - {0}'.format(mower_cmd))
                        resp = despatch_to_mower_udp(
                            mower_cmd, self.udp_socket, host, port, max_attempts=2)
                        self.log(
                            'process_instruction - Enrol in Hotspot {0}:{1} Response {2}'.format(host, port, resp))
                    else:
                        self.log(
                            'unable to process enrolment instruction - No host:port')
                elif name == 'reboot':
                    # reboot pxm node
                    self.log('process_instruction - Rebooting...')
                    os.system('sudo shutdown -r now')
                elif name == 'shutdown':
                    # shutdown pxm node
                    self.log('process_instruction - Shutting Down...')
                    os.system('sudo shutdown now')
                elif name == 'calib-reset':
                    # reset calibration data
                    self.config.resetCalib()
                elif name == 'fence-reset':
                    # reset fence points
                    self.config.resetFence()
                else:
                    self.log(
                        'process_instructions - ERROR no instruction named {0}!'.format(name))
        except (RecordNotFoundException, CollectionNotDeletableException, CollectionNotExtensibleException, CollectionNotUpdatableException, DuplicateRecordException) as e:
            raise e
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in pxm process_instructions: ' +
                           str(e) + ' on line ' + str(err_line))
        return resp

    def log_debug(self, msg):
        # DEBUG logging option
        self.pxm_logger.debug(msg)

    def log(self, msg, incl_mem_stats=False):
        # INFO - default logging option
        if incl_mem_stats:
            mem_stats = get_mem_stats()
        else:
            mem_stats = ''
        self.pxm_logger.info(msg + mem_stats)

    def log_warning(self, msg, incl_mem_stats=False):
        # WARNING logging option
        if incl_mem_stats:
            mem_stats = get_mem_stats()
        else:
            mem_stats = ''
        self.pxm_logger.warning(msg + mem_stats)

    def log_error(self, msg, incl_mem_stats=False):
        # ERROR logging option
        if incl_mem_stats:
            mem_stats = get_mem_stats()
        else:
            mem_stats = ''
        self.pxm_logger.error(msg + mem_stats)

    @cherrypy.expose
    def default(self, *args, **kwargs):
        '''
            http route that is called if no others match
        '''
        if len(args) > 0 and args[0].lower() in ['api', 'xapi']:
            if args[0].lower() == 'api':
                # rest api
                method = getattr(self, "handle_" +
                                 cherrypy.request.method, None)
                if not method:
                    methods = [x.replace("handle_", "")
                               for x in dir(self) if x.startswith("handle_")]
                    cherrypy.response.headers["Allow"] = ",".join(methods)
                    raise cherrypy.HTTPError(405, "Method not implemented.")

                else:
                    if len(args) == 1:
                        # /api - return list of keys
                        kwargs['key'] = '*'
                    elif len(args) >= 2:
                        # /api/lawn/device/width
                        # strip api and join remainder
                        key = '.'.join(args[1:])
                        kwargs['key'] = key
            elif args[0].lower() == 'xapi':
                # xpath api
                method = getattr(self, "handle_x_" +
                                 cherrypy.request.method, None)
                if not method:
                    methods = [m.replace("handle_x_", "")
                               for m in dir(self) if m.startswith("handle_x_")]
                    cherrypy.response.headers["Allow"] = ",".join(methods)
                    raise cherrypy.HTTPError(405, "Method not implemented.")

            return method(*args, **kwargs)

        else:
            # template
            tmplt_route = os.path.sep.join(args)
            tmplt_folder_name = self.tmplt_path_name + os.path.sep + tmplt_route
            if os.path.isdir(tmplt_folder_name):
                # try index in that folder
                tmplt_filename = 'index.html'
            elif tmplt_route.endswith('.md'):
                # otherwise filename is last arg
                tmplt_filename = '{0}'.format(args[-1])
                # and route is shorter
                tmplt_route = os.path.sep.join(args[:-1])
                tmplt_folder_name = self.tmplt_path_name + os.path.sep + tmplt_route
            else:
                # otherwise html filename is last arg
                tmplt_filename = '{0}.html'.format(args[-1])
                # and route is shorter
                tmplt_route = os.path.sep.join(args[:-1])
                tmplt_folder_name = self.tmplt_path_name + os.path.sep + tmplt_route

            tmplt_filepath = '{0}{1}{2}'.format(
                tmplt_folder_name, os.path.sep, tmplt_filename)
            if not os.path.isfile(tmplt_filepath):
                tmplt_filename = tmplt_filepath
                tmplt_filepath = '{0}'.format(os.path.sep)

            rel_tmplt_filepath = '{0}{1}{2}'.format(
                tmplt_route, os.path.sep, tmplt_filename).replace(os.path.sep, '/')
            tmplt_names = tmplt_utils.get_included_templates(
                self.env, rel_tmplt_filepath)

            ctx = tmplt_utils.get_model_context(
                tmplt_names, self, args, kwargs, strict=False)

            try:
                tmplt = self.env.get_template(rel_tmplt_filepath)
                if rel_tmplt_filepath.endswith('.md'):
                    markdown_source = self.env.loader.get_source(self.env, rel_tmplt_filepath)
                    # md => tmplt, tmplt => html
                    html_from_md = markdown.markdown(markdown_source[0])
                    # recover jinja expressions
                    tmplt_str_from_md = html_from_md.replace('<!--', '').replace('-->', '')
                    tmplt_from_md = self.env.from_string(tmplt_str_from_md)
                    # parse
                    html = tmplt_from_md.render(ctx)
                else:
                    html = tmplt.render(ctx)
            except Exception as ex:
                err_line = sys.exc_info()[-1].tb_lineno
                self.log_error('Error in default: ' + str(ex) + ' on line ' +
                               str(err_line) + ' ' + traceback.format_exc())
                print('default Exception rendering: ',
                      rel_tmplt_filepath, ex, err_line)
                tmplt = self.env.get_template('error.html')
                html = tmplt.render(tmplt_name=tmplt_filename)

            return html

    @cherrypy.expose
    def measures_json(self, **kwargs):

        resp = '{}'  # empty response
        try:
            qs = urllib.parse.unquote(cherrypy.request.query_string)
            score_props = {}
            prop_name = None
            # -lower range | expected | +upper range | weighting
            scale_prop_suffixes = ['lower', 'scale', 'upper', 'maxscore']
            meas_prop_suffixes = ['lower', 'setpoint', 'upper', 'maxscore']
            for k in kwargs:
                if k.endswith(tuple(scale_prop_suffixes)):
                    meas_name, prop_name = k.split('_')
                    prop_index = scale_prop_suffixes.index(prop_name)
                    if meas_name == 'span' and prop_name == 'scale':
                        scale_factor = float(kwargs[k])
                        score_prop = self.config['mower.target_length_m'] * \
                            scale_factor
                    elif meas_name == 'area' and prop_name == 'scale':
                        scale_factor = float(kwargs[k])
                        score_prop = self.config['mower.target_area_m2'] * \
                            scale_factor
                    else:
                        score_prop = float(kwargs[k]) if prop_index < 3 else int(
                            kwargs[k])  # max score
                elif k.endswith(tuple(meas_prop_suffixes)):
                    meas_name, prop_name = k.split('_')
                    prop_index = meas_prop_suffixes.index(prop_name)
                    score_prop = float(kwargs[k]) if prop_index < 3 else int(
                        kwargs[k])  # max score
                else:
                    continue
                if meas_name not in score_props:
                    # group start
                    score_props[meas_name] = [None, None, None, None]
                score_props[meas_name][prop_index] = score_prop
            self.cached_scoring_props = score_props

            if cherrypy.request.method == 'POST':
                if 'save' in qs:
                    self.log('measures_json saving measure settings')
                    try:
                        for k in kwargs:
                            if k.endswith(tuple(scale_prop_suffixes)):
                                meas_name, prop_name = k.split('_')
                                prop_index = scale_prop_suffixes.index(prop_name)
                                score_prop = float(kwargs[k]) if prop_index < 3 else int(
                                    kwargs[k])  # max score
                            elif k.endswith(tuple(meas_prop_suffixes)):
                                meas_name, prop_name = k.split('_')
                                prop_index = meas_prop_suffixes.index(prop_name)
                                score_prop = float(kwargs[k]) if prop_index < 3 else int(
                                    kwargs[k])  # max score
                            else:
                                continue
                            db_key = '{}.{}'.format(meas_name, prop_name)
                            self.config[db_key] = score_prop
                        save_feedback = '0|saved'
                    except Exception as ex0:
                        err_line = sys.exc_info()[-1].tb_lineno
                        self.log_error('Error in measures_json POST: ' +
                           str(ex0) + ' on line ' + str(err_line))
                else:
                    # no instruction detected
                    save_feedback = '-1|error'

                self.log(
                    'pxm measures_json POST instruction processed => ' + save_feedback)
                cherrypy.response.headers['Content-Type'] = 'text/plain'
                return save_feedback
            else:
                try:
                    proj_idx = int(
                        kwargs['projidx']) if 'projidx' in kwargs and kwargs['projidx'] is not None else -1
                    proj = self.cached_scoring_snapshot._fltrd_projections[proj_idx]

                    # use the score properties to assess target...
                    proj.assess(score_props)

                    scorecard = render_contour_row(proj, self.pxm_logger)

                    resp = json.dumps([scorecard]).replace("NaN", "null").replace(
                        "-Infinity", "null").replace("Infinity", "null")
                except Exception:
                    pass
                cherrypy.response.headers['Content-Type'] = 'application/json'

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in measures_json: ' +
                           str(ex) + ' on line ' + str(err_line))

        return resp.encode('utf8')

    @cherrypy.expose
    def metadata_json(self, **kwargs):

        resp = '{}'  # empty response

        try:
            min_progress = int(kwargs['progress']
                               ) if 'progress' in kwargs else 0
            req_strat = kwargs['strat'] if 'strat' in kwargs else None
            selected_snapshots = [
                s for s in self.snapshot_buffer.values() if (
                    s._growth.value >= min_progress and
                    ((s._strategy_name == req_strat) or req_strat is None))
                    ]
            self.log_debug('metadata_json: min progress requested: {} {}'.format(
                min_progress,
                [(s.ssid, s._growth.value, s._strategy_name) for s in selected_snapshots]
                )
            )
            if len(selected_snapshots) > 0:
                locate_snapshot = selected_snapshots[-1]
                self.log_debug('metadata_json: selected requested snapshot: {0}'.format(
                    locate_snapshot.ssid))
            else:
                self.log_debug('metadata_json: no snapshots available')
                locate_snapshot = None

            meta_dict = {}

            meta_dict['Environment'] = self.envir if self.envir is not None else {}
            meta_dict['Driver'] = self.drive if self.drive is not None else {}
            meta_dict['Driver']['drive_pause'] = self.drive_pause
            meta_dict['Driver']['cur-mower'] = self.config['current.mower']
            meta_dict['Driver']['cutter1-avail'] = self.config['mower.dimensions.cutter1_dia_m'] > 0
            meta_dict['Driver']['cutter2-avail'] = self.config['mower.dimensions.cutter2_dia_m'] > 0

            if locate_snapshot is not None:
                meta_dict['Locator'] = locate_snapshot.as_public_dict(
                ) if locate_snapshot is not None else {}
                if locate_snapshot._pose is not None:
                    meta_dict['Pose'] = locate_snapshot._pose.as_dict()
                else:
                    meta_dict['Pose'] = {}
                meta_dict['Telemetry'] = self.telem if self.telem is not None else {}

            # convert to json
            resp = json.dumps(meta_dict)

            cherrypy.response.headers['Content-Type'] = 'application/json'

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in metadata_json: ' +
                           str(ex) + ' on line ' + str(err_line))

        return resp.encode('utf8')

    @cherrypy.expose
    def contours_json(self, ssid=-1, **_kwargs):

        resp = '{}'  # empty response

        try:
            ss_index = int(ssid)
            if ss_index in self.snapshot_buffer:
                locate_snapshot = self.snapshot_buffer[ss_index]
                # render table
                max_row_count = constants.CONTOUR_TABLE_MAX_ROWS
                rendered_projections = []
                if (locate_snapshot is not None and
                    '_fltrd_projections' in vars(locate_snapshot) and
                    locate_snapshot._fltrd_projections is not None):
                    for proj in locate_snapshot._fltrd_projections[-max_row_count:]:
                        rendered_projections.append(
                            render_contour_row(proj, self.pxm_logger))

                # convert to json
                resp = json.dumps(rendered_projections).replace("NaN", "null").replace(
                    "-Infinity", "null").replace("Infinity", "null")
            else:
                locate_snapshot = None
                self.log_warning(
                    'Problem in contours_json: No content Warning Http 204')
                cherrypy.response.status = '204'  # No Content Warning

            cherrypy.response.headers['Content-Type'] = 'application/json'

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in contours_json: ' +
                           str(ex) + ' on line ' + str(err_line))

        return resp.encode('utf8')

    @cherrypy.expose
    def strategy_json(self, ssid=-1, **_kwargs):

        resp = '{}'  # empty response

        try:
            terms = []
            rules = []
            ss_index = int(ssid)
            if ss_index in self.snapshot_buffer:
                locate_snapshot = self.snapshot_buffer[ss_index]
            else:
                locate_snapshot = None
                cherrypy.response.status = '204'  # No Content Warning

            if locate_snapshot is not None:
                if '_terms' in vars(locate_snapshot):
                    terms = [var_obj.render_dict(index, len(
                        self.rules_engine.terms) - 1) for index, var_obj in enumerate(locate_snapshot._terms)]
                    cur_ssid = [
                        t for t in locate_snapshot._terms if t.name == 'ssid'][0].result
                    if cur_ssid != int(ssid):
                        self.log_debug('strategy_json ssid mismatch snapshot ssid: {0} != requested ssid: {1}\n{2}'.format(
                            cur_ssid, ssid, str(self.snapshot_buffer)))
                    else:
                        self.log_debug('strategy_json ssid match snapshot ssid: {0} == requested ssid: {1}\n{2}\n\n{3}'.format(
                            cur_ssid,
                            ssid,
                            str(list(self.snapshot_buffer)),
                            None)
                        )

                if '_rules' in vars(locate_snapshot) and len(locate_snapshot._rules) > 0:

                    pred_cur_succ_iter = more_itertools.windowed(
                        [None] + locate_snapshot._rules + [None], n=3, step=1)
                    rules = [cur_obj.render_dict(pre_obj, succ_obj) for (
                        pre_obj, cur_obj, succ_obj) in pred_cur_succ_iter]

            tri_list = [self.rules_engine.name,
                        [list(term_dict.values()) for term_dict in terms],
                        [list(rule_dict.values()) for rule_dict in rules]
                        ]
            try:
                resp = json.dumps(tri_list)
            except Exception as ex3:
                self.log_error(
                    'Error in strategy_json converting terms and rules to json: ' + str(ex3))

            cherrypy.response.headers['Content-Type'] = 'application/json'

        except Exception as ex2:
            err_line2 = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in strategy_json: ' +
                           str(ex2) + ' on line ' + str(err_line2))

        return resp.encode('utf8')

    @cherrypy.expose
    def log_view(self, logname):
        logtext = logname
        try:
            log = logging.getLogger(logname)
            filepath = log.handlers[0].baseFilename
            f = open(filepath, "r")
            logtext = utilities.tail(f, lines=32)
            pass
        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in log_view: ' + str(ex) +
                           ' on line ' + str(err_line))

        cherrypy.response.headers['Content-Type'] = "text/plain"

        return logtext

    @cherrypy.expose
    def arena_img(self, ssid=-1, **_kwargs):
        arena_stream = None
        mime_type = 'jpeg'

        try:

            # update drive and environment
            # this is to get absolute latest data - has been populated in find_execute already

            # add current mower to drive
            self.drive['cur-mower'] = self.config['current.mower']

            # add current set speeds to drive
            self.drive['rot-speed'] = self.config['mower.motion.set_rotation_speed_percent']
            self.drive['drv-speed'] = self.config['mower.motion.set_drive_speed_percent']

            # add last visited nodes
            self.drive['last_visited_route_node'] = self.config['current.last_visited_route_node']

            # add last cmds to drive
            self.drive['last_cmds'] = list(
                self.rules_engine.last_n_commands)[::-1]

            # calculate the drive state index...
            no_mower = self.config['current.mower'] is None or self.config['current.mower'] == 'None'
            if no_mower:
                self.drive['state-index'] = 0
            else:
                if self.drive_pause:
                    self.drive['state-index'] = 4
                elif self.drive['path'] == 'Single':
                    self.drive['state-index'] = 3
                elif self.drive['path'] == 'Plan':
                    self.drive['state-index'] = 13
                elif self.drive['path'] == 'Route':
                    self.drive['state-index'] = 2
                else:
                    self.drive['state-index'] = 1

            ss_index = int(ssid)
            if ss_index in self.snapshot_buffer:
                locate_snapshot = self.snapshot_buffer[ss_index]
            else:
                locate_snapshot = None
                cherrypy.response.status = '204'  # No Content Warning

            if locate_snapshot is not None and locate_snapshot._fence_masked_img_arr is not None:
                cur_ssid = locate_snapshot.ssid
                if cur_ssid != int(ssid):
                    self.log_debug(
                        'arena_img ssid mismatch snapshot ssid: {0} != requested ssid: {1}'.format(cur_ssid, ssid))
                else:
                    self.log_debug('arena_img ssid match')

                img_arr = locate_snapshot._fence_masked_img_arr.astype(
                    np.uint8)
                ssid = locate_snapshot.ssid
                if img_arr.ndim == 3:
                    rows, cols, _chans = img_arr.shape
                    self.log(
                        'arena_img, about to transform camera colour image to world arena image...')
                else:
                    rows, cols = img_arr.shape
                    self.log(
                        'arena_img, about to transform camera gray image to world arena image...')

                top_arr = self.undistort_unwarp_mapper.transform_image(img_arr)

                # check array shapes
                self.log('arena_img, image array {0} top array {1}'.format(
                    img_arr.shape, top_arr.shape))

                # should be able to release img_arr here...
                self.log('arena_img, deleting camera image array')
                del (img_arr)

                self.log(
                    'arena_img, transform camera image to world arena image complete')
                img_width_px, img_height_px, padding, line_height, _margin, _left_x, font = self.get_draw_metrics(
                    top_arr)

                top_img_grey = Image.fromarray(top_arr)
                top_img = top_img_grey.convert('RGB')
                top_img_draw = DashedImageDraw(top_img, 'RGB')

                arrow_fill = (0, 0, 255)  # blue
                extrap_arrow_fill = (127, 127, 127)  # grey
                arrow_outline = (0, 0, 255)  # blue
                extrap_arrow_outline = (127, 127, 127)  # grey
                time_fill = (0, 255, 255)
                msg_fill = (255, 0, 0)
                route_fill = 'orange'
                route_point = 'black'
                cutter_indicator = 'crimson'
                route_img = Image.new('RGB', top_img.size, 'black')
                route_img_draw = ImageDraw.Draw(route_img, 'RGBA')

                # should be able to release top_arr here...
                self.log('arena_img, deleting top-down image array')
                del (top_arr)

                # create route image
                # draw route image |over| arena image
                route_pc = self.config['lawn.route_pc']
                if len(route_pc) > 0:
                    self.log('arena_img, about to convert {0} route percentages to pixels using {1} rows and {2} cols\n{3}'.format(
                        len(route_pc), rows, cols, route_pc))
                    route_px = [(int(p[0] * cols / 100), int((100 - p[1]) * rows / 100))
                                for p in route_pc if p[0] is not None and p[1] is not None]
                    cutter_dia_px = self.config['mower.dimensions.cutter_dia_px']
                    if cutter_dia_px is None:
                        cutter_dia_px = 3  # Need a width but want to highlight no cutter
                    route_img_draw.line(
                        route_px, fill=route_fill, width=cutter_dia_px, joint='curve')
                    node_rad = 2
                    for p in route_px:
                        route_img_draw.ellipse(
                            (p[0] - node_rad, p[1] - node_rad, p[0] + node_rad, p[1] + node_rad), fill=route_point)

                # draw viewport as dotted box
                if self.viewport.isnull:
                    margin_m = 0.25
                    bbox_col = '#ff0000'
                    closed_outer_corners = [
                        (margin_m, margin_m),
                        (margin_m, self.config['arena.width_m'] - margin_m),
                        (self.config['arena.length_m'] - margin_m,
                         self.config['arena.width_m'] - margin_m),
                        (self.config['arena.length_m'] - margin_m, margin_m),
                        (margin_m, margin_m)
                    ]
                else:
                    bbox_col = '#7cf96b'
                    # first map camera viewport to arena
                    corners_px_arr_yx = np.asarray(list(self.viewport.corners)) * [
                        self.config['optical.height'], self.config['optical.width']] / 100
                    arena_vp_corners_m = self.data_mapper.transform_contour(
                        corners_px_arr_yx)

                    # re-box, as corners may not align
                    min_corners = np.min(arena_vp_corners_m, axis=0).clip(0)
                    max_corners = np.max(arena_vp_corners_m, axis=0)
                    # closed outer corners ccw from bottom left
                    closed_outer_corners = [
                        (min_corners[0], min_corners[1]),
                        (max_corners[0], min_corners[1]),
                        (max_corners[0], max_corners[1]),
                        (min_corners[0], max_corners[1]),
                        (min_corners[0], min_corners[1])
                    ]

                # then map arena to plan
                x_scale = img_width_px / self.config['arena.width_m']
                y_scale = img_height_px / self.config['arena.length_m']
                plan_vp_corners_px = [(round(corner[0] * x_scale), round(
                    img_height_px - (corner[1] * y_scale))) for corner in closed_outer_corners]
                poly_lines = zip(plan_vp_corners_px, plan_vp_corners_px[1:])

                for poly_line in poly_lines:
                    top_img_draw.dashed_line(
                        poly_line, dash=(10, 4), fill=bbox_col, width=1)

                # current time
                self.annotate(
                    0,
                    img_height_px,
                    padding,
                    line_height,
                    font,
                    time_fill,
                    top_img_draw,
                    time.strftime('%H:%M:%S'),
                    0  # align left
                )
                # location time
                self.annotate(
                    img_width_px,
                    img_height_px,
                    padding,
                    line_height,
                    font,
                    time_fill,
                    top_img_draw,
                    '{0} '.format(ssid) +
                    time.strftime('%H:%M:%S', time.localtime(
                        locate_snapshot._t_zero)),
                    1  # align right
                )
                adr = self.config['optical.analysis_display_ratio']
                if locate_snapshot._pose is not None:
                    tip_x_px = locate_snapshot._pose.plan.tip_x_px / adr
                    tip_y_px = locate_snapshot._pose.plan.tip_y_px / adr
                    tail_x_px = locate_snapshot._pose.plan.tail_x_px / adr
                    tail_y_px = locate_snapshot._pose.plan.tail_y_px / adr
                    left_cotter_x_px = locate_snapshot._pose.plan.left_cotter_x_px / adr
                    left_cotter_y_px = locate_snapshot._pose.plan.left_cotter_y_px / adr
                    right_cotter_x_px = locate_snapshot._pose.plan.right_cotter_x_px / adr
                    right_cotter_y_px = locate_snapshot._pose.plan.right_cotter_y_px / adr
                    annot_arrow(top_img_draw, tail_x_px, tail_y_px,
                                tip_x_px, tip_y_px, arrow_fill, arrow_outline, 8)
                    annot_axle(top_img_draw, left_cotter_x_px, left_cotter_y_px,
                               right_cotter_x_px, right_cotter_y_px, arrow_fill)

                    # cutter indicators
                    cut_rad = 8
                    cut_wdth = 4
                    if ((self.telem is not None and
                         isinstance(self.telem, dict) and
                         'cutter1' in self.telem and
                         self.telem['cutter1'] == 1) or
                            (self.telem is not None and
                             isinstance(self.telem, dict) and
                             'cutter1' not in self.telem and
                             self.cutter1_state)):
                        self.cutter1_state = True
                        top_img_draw.arc(
                            (tip_x_px - cut_rad, tip_y_px - cut_rad,
                             tip_x_px + cut_rad, tip_y_px + cut_rad),
                            start=360 - locate_snapshot._pose.plan.t_deg + 150,
                            end=360 - locate_snapshot._pose.plan.t_deg + 30,
                            fill=cutter_indicator,
                            width=cut_wdth)
                    else:
                        self.cutter1_state = False

                    if ((self.telem is not None and
                         isinstance(self.telem, dict) and
                         'cutter2' in self.telem and
                         self.telem['cutter2'] == 1) or
                            (self.telem is not None and
                             isinstance(self.telem, dict) and
                             'cutter2' not in self.telem and
                             self.cutter2_state)):
                        self.cutter2_state = True
                        top_img_draw.arc(
                            (tail_x_px - cut_rad, tail_y_px - cut_rad,
                             tail_x_px + cut_rad, tail_y_px + cut_rad),
                            start=360 - locate_snapshot._pose.plan.t_deg + 30,
                            end=360 - locate_snapshot._pose.plan.t_deg + 150,
                            fill=cutter_indicator,
                            width=cut_wdth)
                    else:
                        self.cutter2_state = False

                else:
                    self.annotate(
                        img_width_px,
                        img_height_px,
                        padding,
                        line_height,
                        font,
                        msg_fill,
                        top_img_draw,
                        'Robot Not Found',
                        2  # align centre
                    )

                latest_extrap_pose = self.snapshot_buffer.latest_extrap_pose()
                if latest_extrap_pose is not None and constants.OVERLAY_EXTRAPOLATED_POSE:
                    tip_x_px = latest_extrap_pose.plan.tip_x_px / adr
                    tip_y_px = latest_extrap_pose.plan.tip_y_px / adr
                    tail_x_px = latest_extrap_pose.plan.tail_x_px / adr
                    tail_y_px = latest_extrap_pose.plan.tail_y_px / adr
                    annot_arrow(top_img_draw, tail_x_px, tail_y_px, tip_x_px,
                                tip_y_px, extrap_arrow_fill, extrap_arrow_outline, 3)

                # add graphical user-defined symbolic annotation here...

                # get a list of user-defined terms that have a colour specified...
                if self.snapshot_buffer.latest() is not None and '_terms' in vars(self.snapshot_buffer.latest()):
                    terms = self.snapshot_buffer.latest()._terms
                    graphical_terms = [
                        t for t in terms if t.colour is not None and t.colour.lower() != 'none']
                    self.log('Graphical Terms: {}'.format(
                        [(gt.name, gt.result, gt.colour) for gt in graphical_terms]))

                    # create a dictionary of shapes keyed by colour => [coordinates]
                    shape_dict = {}
                    shape_term_dict = {}
                    for gt in graphical_terms:
                        res = gt.result
                        col = gt.colour
                        # count the number of coordinates
                        try:
                            coord_count = 1 if isinstance(res, str) else len(res)
                        except Exception:
                            coord_count = 1
                        # add to dictionaries
                        shape_term_dict[col] = gt
                        if col in shape_dict:
                            if coord_count == 1:
                                shape_dict[col] += [res]
                            else:
                                shape_dict[col] += list(res)
                        else:
                            if coord_count == 1:
                                shape_dict[col] = [res]
                            else:
                                shape_dict[col] = list(res)

                    self.log(
                        'Graphical Terms shape dictionary: {}'.format(shape_dict))

                    # find widest text
                    tmplt = '{}: {} {}'
                    widest = ''
                    for shape_colour, coords in shape_dict.items():
                        if len(coords) == 1:
                            gterm = shape_term_dict[shape_colour]
                            text = tmplt.format(
                                gterm.name, coords[0], gterm.units)
                            if len(text) > len(widest):
                                widest = text

                    line_height_px = int(font.size * 0.75)
                    ann_font = ImageFont.truetype(self.font_path, line_height_px)
                    ann_padding = 4
                    ann_line = 1  # initialise annotation line
                    for shape_colour, coords in shape_dict.items():
                        if len(coords) == 1:
                            # annotation
                            gterm = shape_term_dict[shape_colour]
                            position = (3 * img_width_px / 4, (2 * img_height_px /
                                 3) + ((line_height_px + (1 * ann_padding)) * ann_line))
                            text = tmplt.format(gterm.name, coords[0], gterm.units)
                            bbox = list(top_img_draw.textbbox(position, widest, font=ann_font))
                            bbox[0] -= ann_padding
                            bbox[1] -= ann_padding
                            bbox[2] += ann_padding
                            bbox[3] += ann_padding
                            top_img_draw.rectangle(bbox, fill="ivory", outline="grey")
                            top_img_draw.text(
                                position,
                                text,
                                font=ann_font,
                                fill=shape_colour
                            )
                            ann_line += 1
                        elif len(coords) == 2:
                            try:
                                # point or symbol
                                x_coord = coords[0] * x_scale
                                y_coord = img_height_px - (coords[1] * y_scale)
                                rad = 3
                                top_img_draw.ellipse(
                                    [x_coord - rad, y_coord - rad, x_coord + rad, y_coord + rad], fill=shape_colour, outline=shape_colour, width=1)
                            except Exception:
                                pass
                        elif len(coords) == 3:
                            # circle
                            try:
                                # x, y, r
                                x_coord = coords[0] * x_scale
                                y_coord = img_height_px - (coords[1] * y_scale)
                                rad = coords[2] * x_scale
                                top_img_draw.ellipse(
                                    [x_coord - rad, y_coord - rad, x_coord + rad, y_coord + rad], fill=None, outline=shape_colour, width=1)
                            except Exception:
                                pass
                        elif len(coords) == 4:
                            try:
                                # line
                                x1_coord = coords[0] * x_scale
                                y1_coord = img_height_px - \
                                    (coords[1] * y_scale)
                                x2_coord = coords[2] * x_scale
                                y2_coord = img_height_px - \
                                    (coords[3] * y_scale)
                                top_img_draw.dashed_line([(x1_coord, y1_coord), (x2_coord, y2_coord)], dash=(
                                    2, 6), fill=shape_colour, width=1)
                            except Exception:
                                pass
                # end graphical user-defined symbolic annotation

                # combine images
                img = Image.blend(top_img, route_img, 0.1)
                buffer = io.BytesIO()
                img.save(buffer, mime_type)
                arena_stream = buffer.getvalue()

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in arena_img: ' + str(ex) +
                           ' on line ' + str(err_line))

        cherrypy.response.headers['Content-Type'] = "image/{0}".format(
            mime_type)

        return arena_stream

    @cherrypy.expose
    def contour_img(self, ssid=-1, **_kwargs):
        contour_stream = None
        timesheet = Timesheet('Contour Image')
        try:
            if ssid is not None and int(ssid) >= 0:
                ss_index = int(ssid)
                if ss_index in self.snapshot_buffer:
                    locate_snapshot = self.snapshot_buffer[ss_index]
                else:
                    locate_snapshot = None
                    cherrypy.response.status = '204'  # No Content Warning
            else:
                # just return latest
                locate_snapshot = self.snapshot_buffer.latest()

            if (locate_snapshot is not None and
                '_source_img_arr' in vars(locate_snapshot) and
                locate_snapshot._source_img_arr is not None):

                img_height_px = self.config['optical.height']
                img_width_px = self.config['optical.width']
                img_arr = locate_snapshot._source_img_arr.astype(np.uint8)

                cont_img_grey = Image.fromarray(img_arr)
                cont_img = cont_img_grey.convert('RGB')
                cont_img_draw = DashedImageDraw(cont_img, 'RGB')
                timesheet.add('draw canvas obtained')

                # current time
                img_width_px, img_height_px, padding, line_height, _margin, _left_x, font = self.get_draw_metrics(
                    img_arr)
                sm_font = ImageFont.truetype(self.font_path, 12)

                self.annotate(
                    0,
                    img_height_px,
                    padding,
                    line_height,
                    font,
                    'yellow',
                    cont_img_draw,
                    time.strftime('%H:%M:%S'),
                    0  # align left
                )
                # location time
                self.annotate(
                    img_width_px,
                    img_height_px,
                    padding,
                    line_height,
                    font,
                    'yellow',
                    cont_img_draw,
                    '{0} '.format(ssid) +
                    time.strftime('%H:%M:%S', time.localtime(
                        locate_snapshot._t_zero)),
                    1  # align right
                )
                timesheet.add('location time overlaid')

                # overlay all raw contours
                adr = self.config['optical.analysis_display_ratio']

                fill_col = 'yellow'
                if '_contours' in vars(locate_snapshot) and locate_snapshot._contours is not None:
                    for n, contour in enumerate(locate_snapshot._contours):

                        # convert to flat list for plotting
                        flat_points = list(
                            np.flip(np.array(contour / [adr, adr]).flatten().astype(int)))

                        # sketch outline
                        cont_img_draw.line(flat_points, fill=fill_col, width=1)

                    # overlay filtered body contours
                    fill_col = 'orange'
                    if '_fltrd_contour_index' in vars(locate_snapshot) and locate_snapshot._fltrd_contour_index is not None:
                        for n, contour in enumerate(locate_snapshot._contours):

                            if n in locate_snapshot._fltrd_contour_index.keys():

                                # convert to flat list for plotting
                                fltrd_flat_points = list(
                                    np.flip(np.array(contour / [adr, adr]).flatten().astype(int)))

                                # sketch outline
                                cont_img_draw.line(
                                    fltrd_flat_points, fill=fill_col, width=1)
                                cont_img_draw.text((max(fltrd_flat_points[::2]) + random.randint(10, 100), max(fltrd_flat_points[1::2]) + random.randint(10, 100)), '{0}:{1}'.format(
                                    n, locate_snapshot._fltrd_contour_index[n]), fill=fill_col, font=sm_font)
                timesheet.add('contours overlaid')

                if locate_snapshot._pose is None:
                    self.annotate(
                        img_width_px,
                        img_height_px // 1,
                        padding,
                        line_height,
                        font,
                        'red',
                        cont_img_draw,
                        'Robot Not Found',
                        2  # align centre
                    )
                timesheet.add('pose overlaid')

                # draw viewport as dotted box
                poly_lines = self.viewport.xyxy_polylines(img_arr.shape)
                for poly_line in poly_lines:
                    p_line = [(p[0], p[1]) for p in poly_line]
                    cont_img_draw.dashed_line(
                        p_line, dash=(4, 4), fill='white', width=1)
                timesheet.add('viewport overlaid')

                if constants.DEBUG_SAVE_IMAGE_LEVEL > 0:
                    cont_img.save(self.tmp_folder_path + 'contours.jpg',
                                  optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

                buffer = io.BytesIO()
                cont_img.save(buffer, 'JPEG')
                contour_stream = buffer.getvalue()

            cherrypy.response.headers['Content-Type'] = "image/jpg"
            timesheet.add('response complete')
            self.log_debug(timesheet)

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in contour_img: ' +
                           str(ex) + ' on line ' + str(err_line))

        return contour_stream

    @cherrypy.expose
    def projection_analysis_img(self, **kwargs):
        img_stream = None
        try:
            prj_idx = int(kwargs['projidx']) if 'projidx' in kwargs else 0
            try:
                entry = self.contours_buffer[prj_idx]
                img_buf = plot_contour_entry_as_projection(
                    self, entry, False, self.pxm_logger)
                img_stream = img_buf.getvalue()
            except IndexError:
                err_image = Image.new("RGBA", (240, 360))
                err_draw = ImageDraw.Draw(err_image)
                err_font = ImageFont.truetype(self.font_path, 12)
                err_draw.text((10, 10), "No Contours Available",
                              fill='grey', font=err_font)
                img_stream = io.BytesIO()
                # need transparent background
                err_image.save(img_stream, 'png')
                img_stream.seek(0)
            cherrypy.response.headers['Content-Type'] = "image/jpg"

        except Exception as ex1:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in cont_analysis: ' +
                           str(ex1) + ' on line ' + str(err_line))

        return img_stream

    @cherrypy.expose
    def target_analysis_img(self, **kwargs):

        img_stream = None
        try:
            prj_idx = int(kwargs['projidx']) if 'projidx' in kwargs else 0
            num_entries = len(
                self.cached_scoring_snapshot._fltrd_projections) if self.cached_scoring_snapshot is not None else 0
            max_id = num_entries - 1
            if prj_idx >= 0 and prj_idx <= max_id:
                proj = self.cached_scoring_snapshot._fltrd_projections[prj_idx]
                score_props = self.cached_scoring_props
                proj.assess(score_props)
                try:
                    vp = [vp for vp in self.cached_scoring_snapshot._prospect_viewports if proj.ssid.startswith(
                        vp.index)][0]
                    src_img_arr = vp.analysis_sub_array
                    disp_img_arr = vp.display_sub_array
                except Exception:
                    src_img_arr = None
                    disp_img_arr = None
                img_buf = io.BytesIO()
                plot_projection_img(
                    proj,
                    datetime.datetime.fromtimestamp(
                        proj.start_time_secs).strftime("%Y-%m-%d %H:%M:%S"),
                    src_img_arr,
                    disp_img_arr,
                    img_buf,
                    logger=self.pxm_logger
                )
                img_stream = img_buf.getvalue()
            else:
                err_image = Image.new("RGBA", (240, 360))
                err_draw = ImageDraw.Draw(err_image)
                err_font = ImageFont.truetype(self.font_path, 12)
                err_draw.text((10, 10), "No Contours Available",
                              fill='black', font=err_font)
                img_stream = io.BytesIO()
                # need transparent background
                err_image.save(img_stream, 'png')
                img_stream.seek(0)
            cherrypy.response.headers['Content-Type'] = "image/jpg"

        except Exception as ex1:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in cont_analysis: ' +
                           str(ex1) + ' on line ' + str(err_line))

        return img_stream

    @cherrypy.expose
    def stage_img(self, **kwargs):

        srid = int(kwargs['srid']) if 'srid' in kwargs else 1
        erid = int(kwargs['erid']) if 'erid' in kwargs else srid
        crid = self.config['current.last_visited_route_node']
        arrow_length_m = self.config['mower.target_length_m'] / 2
        self.pxm_logger.debug('Arrow Length: ' + str(arrow_length_m))
        excursion_logger = logging.getLogger('excursion')
        # get filename
        excursion_log_handler = excursion_logger.handlers[0]
        log_file_path = excursion_log_handler.baseFilename
        if log_file_path is not None:
            img_buf = plot_excursion(
                log_file_path, srid, erid, crid, arrow_length_m, logger=self.pxm_logger, annotate=False)
            cherrypy.response.headers['Content-Type'] = "image/jpg"
            return img_buf.getvalue()
        else:
            return None

    @cherrypy.expose
    def tracking_img(self, **_kwargs):
        '''
            assemble tracking image
        '''
        rows = self.config['optical.height']
        cols = self.config['optical.width']
        track_img = Image.new('RGB', (cols, rows), color='black')
        track_img_draw = ImageDraw.Draw(track_img, 'RGBA')

        # draw route over image
        route_pc = self.config['lawn.route_pc']
        if len(route_pc) > 0:
            radius = 12
            for pt in route_pc:
                xy = (int(pt[0] * cols / 100) - radius, int((100 - pt[1]) * rows / 100) - radius,
                      int(pt[0] * cols / 100) + radius, int((100 - pt[1]) * rows / 100) + radius)
                track_img_draw.ellipse(xy, fill='orange')

            route_px = [(int(p[0] * cols / 100), int((100 - p[1]) * rows / 100))
                        for p in route_pc if p[0] is not None and p[1] is not None]
            track_img_draw.line(route_px, fill='orange',
                                width=10, joint='curve')

        # next we add the mower pose from location log
        if self.excursion_log_file_path is not None:
            with open(self.excursion_log_file_path, 'r') as f:
                locations = f.readlines()
            line_count = len(locations)
            for line_index in range(line_count):
                line = locations[line_index]
                cells = line.split(",")
                try:
                    x_m = float(cells[8])
                    y_m = float(cells[9])
                    t_deg = float(cells[10])
                    t_rad = radians(t_deg)
                    p = poses.Pose(x_m, y_m, t_rad)
                    radius = 2
                    xy = p.plan.c_x_px - radius, p.plan.c_y_px - \
                        radius, p.plan.c_x_px + radius, p.plan.c_y_px + radius
                    track_img_draw.ellipse(xy, fill='blue')
                    self.annot_arrow(track_img_draw, p.plan.tail_x_px, p.plan.tail_y_px,
                                     p.plan.tip_x_px, p.plan.tip_y_px, outline='blue', fill='cyan')

                except Exception:
                    pass  # over headings
        else:
            self.log_error('tracking_img: No excursion log found')
        # Send the result
        cherrypy.response.headers['Content-Type'] = "image/jpg"
        buffer = io.BytesIO()
        track_img.save(buffer, 'JPEG')
        track_stream = buffer.getvalue()
        return track_stream

    @cherrypy.expose
    def vision_img(self, **_kwargs):
        timesheet = Timesheet('Vision Image')
        qs = urllib.parse.unquote(cherrypy.request.query_string)
        timesheet.add('query string parsed')
        self.log('-----------------pxm vision_img: ' + qs)
        self.log_debug('vision_img self.camera:' + str(self.camera))
        self.log_debug('vision_img self.camera.settings:' +
                       str(self.camera.settings))
        cam_settings = self.camera.settings.clone(qs)
        timesheet.add('settings cloned')
        if cherrypy.request.method == 'POST':
            if 'save' in qs:
                self.log('vision_img saving camera settings')
                cam_settings.save_settings(self.config)
                save_feedback = '0|saved'
                timesheet.add('settings saved')
            else:
                # no instruction detected
                save_feedback = '-1|error'

            self.log(
                'pxm vision_image POST instruction processed => ' + save_feedback)
            return save_feedback
        else:
            cam_settings['queue'] = 'vision'  # 'locate' 'snap'
            cam_settings['client'] = 'vision'
            cache_key = 'vision'
            mime_type = 'jpeg'
            self.log('pxm vision_img placing request on queue...')
            self.camera_request_queue.put(cam_settings)
            timesheet.add('image request submitted')
            self.log('pxm vision_img getting image from raw queue (blocks)...')
            queue_delay_start = time.time()
            analysis_array, img_array = self.camera_vision_queue.get(timeout=30)
            self.log('pxm vision_img getting image from raw queue (blocks)... {0:.3f}secs'.format(
                time.time() - queue_delay_start))
            timesheet.add('image response received')

            if analysis_array is not None:

                # find and count contours
                sizables = len(lores_contours(analysis_array, min_pt_count=1))
                timesheet.add('lo-res contours counted')

            if img_array is not None:

                raw_img = Image.fromarray(img_array)
                buffer = io.BytesIO()
                raw_img.save(buffer, 'JPEG')
                img_stream = buffer.getvalue()

                self.calib_image_array_cache[cache_key] = img_array
                timesheet.add('image cached for ???')

            else:
                img_stream = None
                timesheet.add('image error')

            cherrypy.response.headers['Content-Type'] = 'image/{0}'.format(
                mime_type)
            cherrypy.response.headers['Content-Info-Revision'] = self.camera.revision
            try:
                cherrypy.response.headers['Content-Info-Dimensions'] = '{1}x{0}'.format(
                    *img_array.shape)
                cherrypy.response.headers['Content-Info-Memory'] = '{0}'.format(
                    get_mem_stats())
                cherrypy.response.headers['Content-Info-ContourCount'] = '{0}'.format(
                    sizables)
                cherrypy.response.headers['Content-Info-RawSensor'] = '{0}'.format(
                    self.camera.picam2.camera_configuration()['raw'])

                cherrypy.response.headers['Content-Info-Model'] = str(
                    self.camera.picam2.camera_properties['Model'])

                cherrypy.response.headers['Content-Info-Iso'] = cam_settings['iso']
                cherrypy.response.headers['Content-Info-Resolution'] = cam_settings['resolution']
                cherrypy.response.headers['Content-Info-ShutterSpeed'] = str(
                    self.camera.shutter_speed)
                cherrypy.response.headers['Content-Info-SensorMode'] = str(
                    self.camera.sensor_mode)
                cherrypy.response.headers['Content-Info-FrameRate'] = str(
                    self.camera.framerate)
                cherrypy.response.headers['Content-Info-AwbGains'] = str(
                    [round(float(g), 1) for g in self.camera.awb_gains])

            except Exception:
                pass

            cherrypy.response.headers['Content-Info-Settings'] = str(
                cam_settings.get_filtered_settings())
            if self.camera.revision == 'Pi Camera II':
                exclusions = ['ColourCorrectionMatrix']
                filtered_metadata = {
                    k: v for k, v in self.camera.metadata.items() if k not in exclusions}
                cherrypy.response.headers['Content-Info-Metadata'] = filtered_metadata

            self.log('=================pxm vision_img finished: ' + qs)
            timesheet.add('vision image processing complete')
            self.log_debug(timesheet)

            return img_stream

    @cherrypy.expose
    def calib_img_stack(self, src=None, **_kwargs):
        '''
            return a stack of images, one for each mode!
        '''
        qs = cherrypy.request.query_string
        self.log('pxm calib_imgs: ' + qs)
        cam_settings = self.camera.settings.clone(self.config)
        cam_settings['queue'] = 'snap'
        cam_settings['client'] = 'calib'
        # align resolution mode with configuration so matrices correspond!
        cam_settings['resolution'] = self.config['optical.resolution']
        cam_settings['display_colour'] = True
        display_cols = self.config['optical.display_width']
        display_rows = self.config['optical.display_height']
        strength = self.config['optical.undistort_strength']
        zoom = self.config['optical.undistort_zoom']
        mime_type = 'jpeg'

        self.log('pxm calib_imgs placing request on queue...')
        self.camera_request_queue.put(cam_settings)
        self.log('pxm calib_imgs getting image from queue (blocks)...')
        img_arr = self.camera_snap_queue.get(timeout=30)

        self.undistort_mapper.populate(
            ["unbarrel"],
            display_cols,  # img_arr_cols,
            display_rows,  # img_arr_rows
            strength=strength,
            zoom=zoom
        )
        undist_arr = self.undistort_mapper.transform_image(img_arr)
        undist_img = Image.fromarray(undist_arr)
        undist_img_draw = ImageDraw.Draw(undist_img)
        undist_img_draw.text((5, 5), 'Live', font_size=24)

        self.unwarp_mapper.populate(
            ["transform"],
            display_cols,  # img_arr_cols,
            display_rows,  # img_arr_rows
            matrix=self.config['calib.img_matrix']
        )
        arena_arr = self.unwarp_mapper.transform_image(undist_arr)
        arena_img = Image.fromarray(arena_arr)

        # find latest archive image
        list_of_files = glob.glob(self.calib_folder_path_name + os.sep + '*.jpg')
        if len(list_of_files) > 0:
            latest_file = max(list_of_files, key=os.path.getctime)
            arc_img = Image.open(latest_file)
            arc_img_draw = ImageDraw.Draw(arc_img)
            text_width = arc_img_draw.textlength(latest_file)
            arc_img_draw.text((display_cols - (text_width * 24 / arc_img_draw.font.size), 5), '{}'.format(latest_file), font_size=24)
            self.log(
                'pxm calib_imgs archive view latest file: {}'.format(latest_file))
        else:
            # create a blank image to pad payload
            arc_img = Image.new('RGB', undist_img.size, 'brown')
            arc_img_draw = ImageDraw.Draw(arc_img)
            arc_img_draw.text((50, 5), 'No Archive Images Available - use capture...', font_size=24)

        # blended archive with live view
        self.log('pxm calib_imgs live blended with archive view')
        try:
            blend_img = Image.blend(undist_img.convert("RGBA"), arc_img.convert(
                "RGBA"), 0.5).convert('RGB')

        except Exception as e:
            self.log_error('Error blending images: ' + str(e) +
                           ' sizes: ' + str(undist_img.size) + ' ' + str(arc_img.size))

        # stack images?
        if src is None:
            images = [undist_img, arc_img, blend_img, arena_img]
        elif src == '0':
            images = [undist_img]
        elif src == '1':
            images = [arc_img]
        elif src == '2':
            images = [blend_img]
        elif src == '3':
            images = [arena_img]

        widths, heights = zip(*(i.size for i in images))

        max_width = max(widths)
        total_height = sum(heights)

        stack_img = Image.new('RGB', (max_width, total_height))

        y_offset = 0
        for img in images:
            stack_img.paste(img, (0, y_offset))
            y_offset += img.size[1]

        buffer = io.BytesIO()
        stack_img.save(buffer, 'JPEG')
        img_stream = buffer.getvalue()

        cherrypy.response.headers['Content-Type'] = "image/{0}".format(
            mime_type)
        cherrypy.response.headers['Content-Info-Revision'] = self.camera.revision
        try:
            cherrypy.response.headers['Content-Info-Iso'] = str(
                self.camera.iso)
            cherrypy.response.headers['Content-Info-ShutterSpeed'] = str(
                self.camera.shutter_speed)
            cherrypy.response.headers['Content-Info-AwbGains'] = str(
                self.camera.awb_gains)
        except Exception:
            pass
        cherrypy.response.headers['Content-Info-Settings'] = str(cam_settings)

        return img_stream

    @cherrypy.expose
    def fence_img(self, **_kwargs):

        qs = cherrypy.request.query_string
        self.log('pxm fence_img: ' + qs)
        cam_settings = self.camera.settings.clone(self.config)
        cam_settings['queue'] = 'snap'
        cam_settings['client'] = 'fence'
        mime_type = 'jpeg'

        self.log('pxm fence_img placing request on queue...')
        self.camera_request_queue.put(cam_settings)
        self.log('pxm fence_img getting image from queue (blocks)...')
        img_arr = self.camera_snap_queue.get(timeout=30)

        if img_arr is not None:
            arena_arr = self.undistort_unwarp_mapper.transform_image(img_arr)
            arena_img = Image.fromarray(arena_arr)
            buffer = io.BytesIO()
            arena_img.save(buffer, 'JPEG')
            img_stream = buffer.getvalue()
        else:
            img_stream = None

        cherrypy.response.headers['Content-Type'] = "image/{0}".format(
            mime_type)
        cherrypy.response.headers['Content-Info-Revision'] = self.camera.revision
        try:
            cherrypy.response.headers['Content-Info-Iso'] = str(
                self.camera.iso)
            cherrypy.response.headers['Content-Info-ShutterSpeed'] = str(
                self.camera.shutter_speed)
            cherrypy.response.headers['Content-Info-AwbGains'] = str(
                self.camera.awb_gains)
        except Exception:
            pass
        cherrypy.response.headers['Content-Info-Settings'] = str(cam_settings)

        return img_stream

    @cherrypy.expose
    def raw_img(self, **kwargs):

        timesheet = Timesheet('Raw Img')

        qs = cherrypy.request.query_string
        self.log('pxm raw_img: ' + qs)
        req_format = kwargs['fmt'] if 'fmt' in kwargs else None
        if req_format is None:
            mime_type = 'jpeg'
        else:
            mime_type = req_format
        cam_settings = self.camera.settings.clone(qs)
        cam_settings['queue'] = 'raw'
        self.log('pxm raw_img placing request on queue...')
        self.log('raw_img settings...' + str(cam_settings))
        # calls get_raw_image(cam_settings)
        self.camera_request_queue.put(cam_settings)
        self.log('pxm raw_img getting image from queue (blocks)...')
        img_arr = self.camera_raw_queue.get(timeout=15)
        timesheet.add('image returned from raw camera queue')
        self.log('pxm raw_img mean intensity: {:.3f}'.format(np.mean(img_arr)))
        
        if img_arr is not None:
            if mime_type == 'raw':
                self.log('raw_img format: ' + mime_type)
                img_stream = img_arr.astype(np.uint8).tobytes()  # io.BytesIO()
                self.log('raw_img streaming raw array: ' + str(img_arr.shape))
                timesheet.add('byte stream created')
            else:
                img = Image.fromarray(img_arr)
                buffer = io.BytesIO()
                img.save(buffer, mime_type)
                img_stream = buffer.getvalue()
                timesheet.add('image stream created')
        else:
            img_stream = None
        cherrypy.response.headers['Content-Type'] = "image/{0}".format(
            mime_type)
        cherrypy.response.headers['Content-Info-Revision'] = self.camera.revision
        try:
            cherrypy.response.headers['Content-Info-Iso'] = str(
                self.camera.iso)
            cherrypy.response.headers['Content-Info-ShutterSpeed'] = str(
                self.camera.shutter_speed)
            cherrypy.response.headers['Content-Info-AwbGains'] = str(
                self.camera.awb_gains)
        except Exception:
            pass
        cherrypy.response.headers['Content-Info-Settings'] = str(cam_settings)

        self.log_debug(str(timesheet))
        return img_stream

    def annotate(self, img_width_px, img_height_px, padding, line_height, draw_font, draw_col, draw_on, time_str, align=0, bg_col=None):
        text_width = draw_on.textlength(time_str, font=draw_font)
        if align == 0:  # align left
            left_x = padding
            right_x = padding + text_width + padding
        elif align == 1:  # align right
            left_x = img_width_px - (padding + text_width + padding)
            right_x = img_width_px - padding
        else:  # align centre
            left_x = (img_width_px // 2) - (padding + (text_width // 2))
            right_x = padding + left_x + text_width + padding
        if bg_col is not None:
            draw_on.rectangle(
                (left_x, img_height_px - line_height, right_x, img_height_px), fill=bg_col)
        draw_on.text((left_x + padding, img_height_px - (line_height - 2)),
                     time_str, font=draw_font, fill=draw_col)

    def get_draw_metrics(self, image):
        # image can be PIL or numpy array
        img_width_px = img_height_px = padding = line_height = margin = left_x = -1
        font = None
        try:
            if type(image) is np.ndarray:
                if image.ndim == 2:
                    img_height_px, img_width_px = image.shape
                elif image.ndim == 3:
                    img_height_px, img_width_px, _img_chans = image.shape

            else:
                img_width_px, img_height_px = image.size
            font_size = 96 * img_width_px // constants.RESOLUTIONS[0][0]
            padding = img_width_px // 100
            line_height = padding + font_size + padding
            margin = 10 * img_width_px // 100
            left_x = margin - padding
            font = ImageFont.truetype(self.font_path, font_size)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in get_draw_metrics: ' + \
                str(e) + ' on line ' + str(err_line)
            self.log_error(msg)
        return img_width_px, img_height_px, padding, line_height, margin, left_x, font

    def draw_grid(
        self,
        cam_settings,
        lawn_width_m,
        lawn_length_m,
        border_m,
        arena_matrix,
        raw_draw,
        timesheet=None,
        data_mapper=None,
        just_periphery=True
    ):
        # create on-the-fly mapper and matrix?
        try:

            img_width_px = int(cam_settings['resolution'].split('x')[0])
            img_height_px = int(cam_settings['resolution'].split('x')[1])

            # need a fresh arena matrix
            calib_width_m = self.config['calib.width_m']
            calib_length_m = self.config['calib.length_m']
            calib_offset_x_m = self.config['calib.offset_x_m']
            calib_offset_y_m = self.config['calib.offset_y_m']
            lawn_border_m = self.config['lawn.border_m']
            calib_percent_points = self.config['lawn.calib']
            calib_pc_points = [[p.x, p.y] for p in calib_percent_points]
            _M, _N, L, _K = matrices_from_quad_points(
                calib_pc_points,
                calib_width_m,
                calib_length_m,
                calib_offset_x_m,
                calib_offset_y_m,
                lawn_width_m,
                lawn_length_m,
                lawn_border_m,
                img_height_px,
                img_width_px,
                logger=self.pxm_logger,
                debug=True
            )

            arena_matrix = L

            if data_mapper is None:
                # need new dynamic mapper to follow vision query string...
                data_mapper = DataMapper(
                    ["unbarrel_inv", "transform"],
                    img_width_px,
                    img_height_px,
                    matrix=arena_matrix,
                    strength=cam_settings['undistort_strength'],
                    zoom=cam_settings['undistort_zoom'],
                    logger=self.pxm_logger
                )
                if timesheet is not None:
                    timesheet.add('data mapper created')
            else:
                data_mapper.populate(
                    ["unbarrel_inv", "transform"],
                    img_width_px,
                    img_height_px,
                    matrix=arena_matrix,
                    strength=cam_settings['undistort_strength'],
                    zoom=cam_settings['undistort_zoom']
                )
                self.log_debug(
                    'draw grid populated data grid mapper: key ' + data_mapper.cache_key)
                if timesheet is not None:
                    timesheet.add('data mapper populated')

            # obtain grid intersection coordinates
            cam_c_px = grid_intersections_camera(
                lawn_width_m, lawn_length_m, border_m, data_mapper, logger=self.pxm_logger, debug=False)
            if timesheet is not None:
                timesheet.add('grid intersections calculated')

            fill_col = 'white' if cam_settings['display_colour'] else 'black'
            dash_spec = (8, 8)
            # draw horizontals
            for row in [cam_c_px[0], cam_c_px[-1]] if just_periphery else cam_c_px:
                raw_draw.dashed_line(row, dash=dash_spec,
                                     fill=fill_col, width=1)
            if timesheet is not None:
                timesheet.add('horizontals drawn')

            # draw verticals
            cam_c_px_tp = np.transpose(cam_c_px, (1, 0, 2))
            for row in [cam_c_px_tp[0], cam_c_px_tp[-1]] if just_periphery else cam_c_px_tp:
                raw_draw.dashed_line(row, dash=dash_spec,
                                     fill=fill_col, width=1)
            if timesheet is not None:
                timesheet.add('verticals drawn')

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('draw_grid Error: ' + str(e) +
                           ' on line ' + str(err_line))

    def get_raw_image(self, cam_settings):
        img_arr = None
        try:
            timesheet = Timesheet('Get Raw Image')
            self.log('get_raw_image - starting setup...' + str(cam_settings))

            trace, changed = self.camera.apply_settings(cam_settings)
            self.log('get_raw_image apply to camera changed {0} trace:\n{1}'.format(
                changed, trace))

            disp_col = cam_settings['display_colour']  # True or False
            analysis_chan = 'gray'
            display_chan = 'col' if disp_col else 'gray'
            lawn_width_m = self.config['lawn.width_m']
            lawn_length_m = self.config['lawn.length_m']
            border_m = self.config['lawn.border_m']
            _arena_width_m = self.config['arena.width_m']
            _arena_length_m = self.config['arena.length_m']
            _img_width_px = self.config['optical.width']
            _img_height_px = self.config['optical.height']
            arena_matrix = self.config['calib.arena_matrix']
            img_arr = self.camera.snap(
                'yuv' if analysis_chan == 'gray' and display_chan == 'gray' else 'rgb')
            if img_arr is not None:
                self.log('raw_image capture complete, array shape: ' +
                     str(img_arr.shape))

                # decide if any overlays are needed...
                virtual_mower = 'virtual_mower' in cam_settings and cam_settings['virtual_mower']
                self.log('raw_image capture rgb virtual robot mode: {0}'.format(
                    virtual_mower is not None and virtual_mower))
                annotate = (
                    'annotate' in cam_settings and cam_settings['annotate'])
                overlaying = (virtual_mower or annotate)
                raw_fs_img = Image.fromarray(img_arr)
                # downsize display image if necessary
                if cam_settings['client'] == 'remote':
                    raw_img = raw_fs_img
                else:
                    display_width = self.config['optical.display_width']
                    display_height = self.config['optical.display_height']
                    raw_img = raw_fs_img.resize(
                        (display_width, display_height), resample=Image.Resampling.LANCZOS)
                    img_arr = np.asarray(raw_img)

                if overlaying:

                    if virtual_mower:
                        self.overlay_virtual_mower(raw_img)

                    raw_draw = DashedImageDraw(raw_img)

                    if virtual_mower:
                        if constants.VIRTUAL_NOISE > 0 or constants.VIRTUAL_OBSTACLE_LINE_WIDTH > 0:
                            self.overlay_virtual_noise(raw_draw)

                    if annotate and cam_settings['client'] == 'vision':
                        font = ImageFont.truetype(self.font_path, 24)
                        # fill colour will be interpreted as red in colour modes and white otherwise
                        raw_draw.text((raw_img.size[0] / 2, raw_img.size[1] / 2), time.strftime(
                            '%H:%M:%S.') + str(datetime.datetime.now().microsecond), fill=0, font=font)

                    if cam_settings.client not in ['calib', 'remote']:
                        self.log('get_raw_image - starting grid...')
                        if cam_settings['client'] == 'fence':
                            # display resolution
                            cam_settings['resolution'] = '{0}x{1}'.format(
                                display_width, display_height)
                            self.draw_grid(
                                cam_settings,
                                lawn_width_m,
                                lawn_length_m,
                                border_m,
                                arena_matrix,
                                raw_draw,
                                timesheet,
                                data_mapper=self.grid_data_mapper,
                                just_periphery=True
                            )
                        else:
                            self.draw_grid(
                                cam_settings,
                                lawn_width_m,
                                lawn_length_m,
                                border_m,
                                arena_matrix,
                                raw_draw,
                                timesheet,
                                data_mapper=self.grid_data_mapper,
                                just_periphery=False
                            )
                        self.log('get_raw_image - grid complete')

                    # convert overlaid image back to array
                    img_arr = np.array(raw_img)

                    self.log_debug(timesheet)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('Error in get_raw_image: ' +
                           str(e) + ' on line ' + str(err_line))

        return img_arr

    def overlay_virtual_mower(self, raw_img):
        try:
            shared_pose = self.shared.get()
            if shared_pose is not None:
                if sum(shared_pose) == 0:  # initialise virtual mower?
                    self.shared.set(
                        self.config['arena.width_m'] / 2,
                        self.config['arena.length_m'] / 2,
                        0,
                        self.config['mower.axle_track_m'],
                        self.config['mower.velocity_full_speed_mps']
                    )
                else:
                    mower_xm, mower_ym, mower_t_deg = shared_pose
                self.log('virtual overlay obtained data from shared pose')

            vp = self.shared.get()
            if vp is None:
                raise SharedMemoryException(
                    'Shared Pose for Virtual Mower Unavailable')
            else:
                mower_xm, mower_ym, mower_t_deg = vp

            self.log(
                'virtual camera mower:{0:.0f}@({1:.2f}, {2:.2f})'.format(mower_t_deg, mower_xm, mower_ym))
            # construct temp pose
            p = poses.Pose(mower_xm, mower_ym, radians(
                mower_t_deg), mapper=self.data_mapper)
            self.log('virtual camera pose:{0:.0f}@({1:.2f}, {2:.2f})'.format(
                p.arena.t_deg, p.arena.c_x_m, p.arena.c_y_m))

            target_rgb = 'white'  # 'white'
            target_body_rgb = '#444444'  # 'dark grey'

            rgb_draw = DashedImageDraw(raw_img)

            # draw body in near black et al if valid?
            if 'corners_px' in vars(p.cam):
                body_px_lst = p.cam.corners_px
                rgb_draw.polygon(body_px_lst, fill=target_body_rgb)

                trunc_px_lst = (
                    [
                        p.cam.tp12_x_px, p.cam.tp12_y_px,
                        p.cam.m12_x_px, p.cam.m12_y_px,
                        p.cam.tp21_x_px, p.cam.tp21_y_px,

                        p.cam.tp23_x_px, p.cam.tp23_y_px,
                        p.cam.m23_x_px, p.cam.m23_y_px,
                        p.cam.tp32_x_px, p.cam.tp32_y_px,

                        p.cam.tp31_x_px, p.cam.tp31_y_px,
                        p.cam.m31_x_px, p.cam.m31_y_px,
                        p.cam.tp13_x_px, p.cam.tp13_y_px,
                    ]
                )

                rgb_draw.polygon(trunc_px_lst, fill=target_rgb,
                                 outline=target_rgb)

        except SharedMemoryException as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_mower Problem processing virtual mower: ' + \
                str(e) + ' on line ' + str(err_line)
            self.log_warning(msg)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_mower Error processing virtual mower: ' + \
                str(e) + ' on line ' + str(err_line)
            self.log_error(msg)

    def random_shape(self, rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px):
        # draw random shape at random size
        radius = random.randint(int(span_px / 1.5), int(span_px / 1.5))
        bounding_circle = int(offset_centre_x_px), int(
            offset_centre_y_px), radius
        n_sides = random.randint(3, 16)  # 3, 10
        rotation = random.randint(0, 360)
        try:
            shape_color = 'white'  # random.randint(200, 255)
            rgb_draw.regular_polygon(
                bounding_circle, n_sides, rotation=rotation, fill=shape_color, outline=None)  # gray or neg
        except Exception as e0:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_noise random shape drawing Error: ' + \
                str(e0) + ' colours:' + str(shape_color) + \
                ' on line ' + str(err_line)
            self.log_error(msg)

    def random_ellipse(self, rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px):
        # draw random ellipse at random size
        maj_radius = random.randint(int(span_px / 4), int(span_px / 2))
        min_radius = random.randint(int(span_px / 4), int(span_px / 2))
        try:
            shape_color = 'white'  # random.randint(200, 255)
            rgb_draw.ellipse((offset_centre_x_px - maj_radius,
                             offset_centre_y_px - min_radius,
                             offset_centre_x_px + maj_radius,
                             offset_centre_y_px + min_radius), fill=shape_color, outline=None)  # gray or neg
        except Exception as e0:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_noise random ellipse drawing Error: ' + \
                str(e0) + ' colours:' + str(shape_color) + \
                ' on line ' + str(err_line)
            self.log_error(msg)

    def fixed_shape(self, rgb_draw, _span_px, offset_centre_x_px, offset_centre_y_px, random_rotation=False):
        # draw fixed shape at fixed size
        radius = 10
        bounding_circle = int(offset_centre_x_px), int(
            offset_centre_y_px), radius
        n_sides = 3
        rotation = random.randint(0, 360) if random_rotation else 0
        try:
            color = 255
            rgb_draw.regular_polygon(
                bounding_circle, n_sides, rotation=rotation, fill=color, outline=None)  # gray or neg
        except Exception as e0:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_noise around Drawing Error: ' + \
                str(e0) + ' colours:' + str(color) + \
                ' on line ' + str(err_line)
            self.log_error(msg)

    def overlay_virtual_noise(self, rgb_draw):
        mode = constants.VIRTUAL_NOISE
        try:
            if mode > 0:
                shared_pose = self.shared.get()
                if shared_pose is not None:
                    mower_xm, mower_ym, mower_t_deg = shared_pose
                    self.log('virtual overlay obtained data from shared pose')

                # construct temp pose?
                if mower_xm is not None and mower_ym is not None and mower_t_deg is not None:
                    p = poses.Pose(mower_xm, mower_ym, radians(mower_t_deg))
                    span_px = np.hypot(
                        p.cam.tail_x_px - p.cam.tip_x_px, p.cam.tail_y_px - p.cam.tip_y_px)
                    x_base_offset, y_base_offset = 16 * span_px / 3, 12 * span_px / 3
                    if mode == 1:
                        for angle in range(0, 360, 45):
                            # spiral around target?
                            x_offset = sin(radians(angle)) * \
                                x_base_offset * ((angle / 720) + 0.5)
                            y_offset = cos(radians(angle)) * \
                                y_base_offset * ((angle / 720) + 0.5)
                            offset_centre_x_px = p.cam.c_x_px + x_offset
                            offset_centre_y_px = p.cam.c_y_px + y_offset
                            self.random_shape(
                                rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px)
                    elif mode == 2:
                        offset_centre_x_px = random.randint(
                            0, self.config['optical.width'])
                        offset_centre_y_px = random.randint(
                            0, self.config['optical.height'])
                        self.random_shape(
                            rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px)
                    elif mode == 3:
                        offset_centre_x_px = int(
                            2 * self.config['optical.width'] / 3)
                        offset_centre_y_px = int(
                            2 * self.config['optical.height'] / 3)
                        self.fixed_shape(
                            rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px)
                    elif mode == 4:
                        for _n in range(0, 10):
                            offset_centre_x_px = random.randint(
                                0, self.config['optical.width'])
                            offset_centre_y_px = random.randint(
                                0, self.config['optical.height'])
                            self.random_ellipse(
                                rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px)
                    elif mode == 5:
                        x_base_offset, y_base_offset = 5 * span_px / 2, 5 * span_px / 2
                        for angle in range(0, 360, 180):
                            # spiral around target
                            x_offset = sin(radians(angle)) * \
                                x_base_offset * ((angle / 720) + 0.5)
                            y_offset = cos(radians(angle)) * \
                                y_base_offset * ((angle / 720) + 0.5)
                            offset_centre_x_px = p.cam.c_x_px + x_offset
                            offset_centre_y_px = p.cam.c_y_px + y_offset
                            self.fixed_shape(
                                rgb_draw, span_px, offset_centre_x_px, offset_centre_y_px)
                    elif mode == 6:
                        if random.randint(0, 20) == 5:
                            offset_centre_x_px = random.randint(
                                0, self.config['optical.display_width'] * 2)
                            offset_centre_y_px = random.randint(
                                0, self.config['optical.display_height'] * 2)
                            self.random_ellipse(
                                rgb_draw, span_px * 4, offset_centre_x_px, offset_centre_y_px)
            if constants.VIRTUAL_OBSTACLE_LINE_WIDTH > 0:
                width_px = self.config['optical.width'] - 1
                height_px = self.config['optical.height'] - 1
                vinc_px = width_px // 8
                hinc_px = height_px // 8
                left_px = (width_px // 2) - hinc_px
                right_px = (width_px // 2) + hinc_px
                top_px = (height_px // 2) - vinc_px
                bottom_px = (height_px // 2) + vinc_px
                xy = [(0, height_px // 2), (left_px, height_px // 2), (left_px, top_px), (right_px, top_px),
                      (right_px, bottom_px), (left_px, bottom_px),
                      (left_px, top_px), (right_px, top_px),
                      (right_px, height_px // 2), (width_px, height_px // 2)]
                rgb_draw.line(xy, fill='black', joint='curve',
                              width=constants.VIRTUAL_OBSTACLE_LINE_WIDTH)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'overlay_virtual_noise Error: ' + \
                str(e) + ' on line ' + str(err_line)
            self.log_error(msg)

    def get_chan_arrays(self, cam_settings, grid=False, cap_display=True):

        timesheet = Timesheet('Get Channel Arrays')
        analysis_chan_array = None
        capped_display_img = None

        try:

            self.log('get_chan_arrays - starting setup...' + str(cam_settings))
            trace, changed = self.camera.apply_settings(cam_settings)
            timesheet.add('settings applied to camera')
            self.log('get_chan_arrays apply to camera changed {0} trace:\n{1}'.format(
                changed, trace))

            disp_col = cam_settings['display_colour']  # True or False
            display_chan = 'col' if disp_col else 'gray'

            delay_secs = constants.WAIT_FOR_CAMERA_SECS
            sleep(delay_secs)
            if self.debug:
                if delay_secs > 0:
                    self.log_warning(
                        'get_chan_arrays wait for camera - slept for {0} seconds'.format(delay_secs))
                else:
                    self.log_debug(
                        'get_chan_arrays wait for camera not required')

            img_arr = self.camera.snap(
                'yuv' if display_chan == 'gray' else 'rgb')
            timesheet.add('camera snap complete')
            
            if img_arr is None:
                self.log('get_chan_arrays capture empty', incl_mem_stats=True)
            else:
                self.log('get_chan_arrays capture complete, array shape: ' +
                         str(img_arr.shape), incl_mem_stats=True)
    
                # decide if any overlays are needed...
                virtual_mower = 'virtual_mower' in cam_settings and cam_settings['virtual_mower']
                self.log('get_chan_arrays capture rgb virtual robot mode: {0}'.format(
                    virtual_mower is not None and virtual_mower))
                annotate = (
                    'annotate' in cam_settings and cam_settings['annotate'])
                overlaying = (virtual_mower or annotate)
    
                rgb_img = Image.fromarray(img_arr)
                self.log(
                    'get_chan_arrays rgb capture complete, array size: ' + str(img_arr.shape))
    
                if overlaying:
    
                    if virtual_mower:
                        self.overlay_virtual_mower(rgb_img)
    
                    if display_chan == 'col':
                        ovl_draw = ImageDraw.Draw(rgb_img, 'RGB')
                    elif display_chan == 'gray':
                        ovl_draw = ImageDraw.Draw(rgb_img)
    
                    if virtual_mower:
                        if constants.VIRTUAL_NOISE > 0 or constants.VIRTUAL_OBSTACLE_LINE_WIDTH > 0:
                            self.overlay_virtual_noise(ovl_draw)
    
                    # overlaid image back to array
                    img_arr = np.array(rgb_img)
    
                    timesheet.add('overlay complete')
    
                if display_chan == 'gray':
                    self.log(
                        'get_chan_arrays using single grayscale image for both channels')
                    analysis_chan_array = disp_chan_array = img_arr
                else:
                    self.log(
                        'get_chan_arrays using rgb image => grayscale for analysis')
                    analysis_chan_array = np.array(
                        Image.fromarray(img_arr).convert('L'))
                    disp_chan_array = img_arr
    
                grid_ovl_img = Image.fromarray(disp_chan_array)
                if grid:
                    timesheet.add('grid image from array')
                    grid_ovl_draw = DashedImageDraw(grid_ovl_img)
                    timesheet.add('grid draw from img')
                    lawn_width_m = self.config['lawn.width_m']
                    lawn_length_m = self.config['lawn.length_m']
                    border_m = self.config['lawn.border_m']
                    arena_matrix = self.config['calib.arena_matrix']
    
                    if cam_settings['client'] == 'vision':
                        self.draw_grid(
                            cam_settings,
                            lawn_width_m,
                            lawn_length_m,
                            border_m,
                            arena_matrix,
                            grid_ovl_draw,
                            timesheet=timesheet,
                            data_mapper=self.grid_data_mapper,
                            just_periphery=True
                        )
                    elif cam_settings['client'] == 'locate':
                        self.draw_grid(
                            cam_settings,
                            lawn_width_m,
                            lawn_length_m,
                            border_m,
                            arena_matrix,
                            grid_ovl_draw,
                            timesheet=timesheet,
                            data_mapper=self.data_mapper,
                            just_periphery=False
                        )
                    elif cam_settings['client'] != 'calib':
                        self.draw_grid(
                            cam_settings,
                            lawn_width_m,
                            lawn_length_m,
                            border_m,
                            arena_matrix,
                            grid_ovl_draw,
                            timesheet=timesheet,
                            data_mapper=self.data_mapper,
                            just_periphery=False
                        )
    
                    timesheet.add('grid drawn')

            # down-size display image if necessary
            if cap_display:
                display_width = self.config['optical.display_width']
                display_height = self.config['optical.display_height']
                capped_display_img = grid_ovl_img.resize(
                    (display_width, display_height), resample=Image.Resampling.LANCZOS)
            else:
                capped_display_img = grid_ovl_img

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.log_error('get_chan_arrays Error: ' +
                           str(e) + ' on line ' + str(err_line))

        self.log_debug(str(timesheet))

        return analysis_chan_array, np.asarray(capped_display_img)

    def connect(self):
        if self.db_connection is None:
            try:
                host = self.config['dbconn.host']
                port = int(self.config['dbconn.port'])
                database = self.config['dbconn.db']
                user = self.config['dbconn.user']
                password = self.config['dbconn.password']
                # attempt connection if ip address is real!
                if host is not None and host != '192.0.2.0':
                    self.db_connection = mariadb.connect(
                        host=host,
                        port=port,
                        database=database,
                        user=user,
                        password=password
                    )
            except mariadb.Error as e:
                err_line = sys.exc_info()[-1].tb_lineno
                self.log_error('Unable to connect to Logging Database: ' +
                               str(e) + ' on line ' + str(err_line))

    def disconnect(self):
        self.db_connection = None


def error_500(status, message='', traceback='', version=''):  # @UnusedVariable
    return "Error " + str(status) + ' ' + str(message)


def error_404(status, message='', traceback='', version=''):  # @UnusedVariable
    return "Error " + str(status) + ' ' + str(message)


if __name__ == '__main__':

    linux = (platform.system() == 'Linux')  # Windows | Linux | Darwin(mac)
    parser = ArgumentParser(
        prog='Proxymow-Server',
        description='Automated Mower Server',
        epilog='start the server (python proxymow.py) then point your browser at http://{}:8081'.format(
            socket.gethostname())
    )
    parser.add_argument('-d', '--debug', action='store_true',
                        help="enhanced logging (recommended)")
    parser.add_argument('--work_folder', nargs='?', default=None,
                        help="specify an alternative folder path for logs, images, etc. (the default is ~/)")

    args = parser.parse_args()
    if args.work_folder is None:
        work_folder_path = Path.home()
    else:
        work_folder_path = Path(args.work_folder).resolve()
    log_folder_path = (work_folder_path / 'logs').resolve()

    # ensure folder exists
    if not os.path.exists(log_folder_path):
        os.makedirs(log_folder_path)

    cherrypy_log_file_name = (
        (log_folder_path / 'cherrypy-error.log').resolve()).__str__()

    app_root_path = Path(__file__).parent

    cherrypy_svrconf_file_name = (
        (app_root_path / 'configs' / 'server.conf').resolve()).__str__()

    cherrypy.config.update(
        {
            'server.socket_host': '0.0.0.0', 'server.socket_port': 8082,
            'error_page.500': error_500, 'error_page.404': error_404,
            'log.screen': False, 'log.error_file': cherrypy_log_file_name,
            'tools.staticdir.root': app_root_path
        }
    )
    cherrypy.tree.mount(ProxymowServer(args), '/', cherrypy_svrconf_file_name)
    cherrypy.engine.start()
    cherrypy.engine.block()
