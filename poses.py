import sys
from types import SimpleNamespace
import copy
import numpy as np
from math import sin, cos, degrees, isnan
import time
from enum import Enum, auto

import geom_lib
import shared.shared_utils as su



class PoseOrigination(Enum):
    UNDEFINED = auto()
    DEFINED = auto()
    DETECTED = auto()
    PREDICTED = auto()


class Pose():
    '''
        represents the robot location and heading
        holds tip and tail information
        and triangular vertices
        for multiple perspectives
    '''

    class Perspective(SimpleNamespace):
        pass

    tip_offset_ym = -1
    tail_offset_ym = -1
    target_width_m = -1
    target_length_m = -1
    target_radius_m = -1
    target_offset_pc = 0
    body_width_m = -1
    body_length_m = -1
    arena_width_m = -1
    arena_length_m = -1
    image_width_px = 0
    image_height_px = 0
    config = None
    mapper = None
    logger = None

    @classmethod
    def init(
            cls,
            config,
            target_width_m,
            target_length_m,
            target_radius_m,
            target_offset_pc,
            axle_track_m,
            body_width_m,
            body_length_m,
            arena_width_m,
            arena_length_m,
            image_width_px,
            image_height_px,
            mapper,
            logger
    ):
        '''
            Class Initialisation

            target_width_m is triangular base
            target_length_m is triangular height (tip-tail separation)

            body_width_m, body_length_m is the robot extremities
        '''
        cls.config = config
        cls.target_width_m = target_width_m
        cls.target_length_m = target_length_m
        cls.target_radius_m = target_radius_m
        cls.target_offset_pc = target_offset_pc
        cls.axle_track_m = axle_track_m
        cls.tip_offset_ym = target_length_m * target_offset_pc / 100
        cls.tail_offset_ym = target_length_m * (100 - target_offset_pc) / 100
        cls.body_width_m = body_width_m
        cls.body_length_m = body_length_m
        cls.arena_width_m = arena_width_m
        cls.arena_length_m = arena_length_m
        cls.image_width_px = image_width_px
        cls.image_height_px = image_height_px
        cls.mapper = mapper
        cls.logger = logger

    # Main Constructor
    def __init__(self, cx_m=-1, cy_m=-1, t_rad=-1, ssid=-1, nose_tilt_rad=0, mapper=None):

        try:
            self.t_zero = time.time()
            self.ssid = ssid

            if mapper is None:
                if 'mapper' in vars(self):
                    mapper = self.mapper

            # create the arena perspective [m]
            self.arena = self.create_arena_perspective(
                float(cx_m) if cx_m is not None else None,
                float(cy_m) if cy_m is not None else None,
                float(t_rad) if t_rad is not None else None,
                float(nose_tilt_rad) if nose_tilt_rad is not None else None
            )

            # create the plan perspective [px]
            # use arena and image dimensions to derive plan pixels
            self.plan = self.create_plan_perspective(self.arena)

            # create the camera perspective [px]
            self.cam = self.create_camera_perspective()

            self.location_key = self.as_key()
            self.origination = PoseOrigination.DEFINED

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in Pose constructor: ' + \
                str(e) + ' on line ' + str(err_line)
            try:
                self.logger.error(msg)
            except Exception:
                print(msg)

    # Alternative Constructor
    @classmethod
    def from_tip_tail(cls, tip_m, tail_m, t_rad=-1, ssid=-1):  # @UnusedVariable

        try:
            # calculate offset centre from tip and tail
            cxm, cym = geom_lib.percent_along_line(
                *tip_m, *tail_m, cls.target_offset_pc)
            # calculate heading if not passed in...
            if t_rad is None or t_rad == -1:
                t_rad = geom_lib.get_angle_between_cartesian_points(
                    tail_m[0], tail_m[1], tip_m[0], tip_m[1], 0)
            pose_inst = cls(cx_m=cxm, cy_m=cym, t_rad=t_rad, ssid=ssid)
            # update the measured span as main constructor applies configured dimensions
            pose_inst.arena.span_m = np.hypot(
                tip_m[0] - tail_m[0], tip_m[1] - tail_m[1])
            pose_inst.origination = PoseOrigination.DETECTED

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Warning: unable to create Pose from tip tail: ' + \
                str(e) + ' on line ' + str(err_line)
            try:
                self.logger.error(msg)
            except Exception:
                print(msg)

        return pose_inst

    def create_arena_perspective(self, cx_m, cy_m, t_rad, nose_tilt_rad):

        arena = self.Perspective()

        try:
            arena.c_x_m = cx_m
            arena.c_y_m = cy_m
            arena.t_rad = t_rad
            arena.t_deg = degrees(t_rad) if t_rad != -1 else -1

            # calculate bot centre as percentage of arena?
            arena.c_x_pc = round(100 * cx_m / self.arena_width_m, 2)
            arena.c_y_pc = round(100 * cy_m / self.arena_length_m, 2)

            # assemble salient local points of a Northerly target for communal rotation later

            # Tip
            tip_x_m = cx_m  # no lateral allowance for target - it must be central
            tip_y_m = cy_m + self.tip_offset_ym

            # Tail
            tail_x_m = cx_m
            tail_y_m = cy_m - self.tail_offset_ym

            # Left Cotter
            left_cotter_x_m = cx_m - (self.axle_track_m / 2)
            left_cotter_y_m = cy_m

            # Right Cotter
            right_cotter_x_m = cx_m + (self.axle_track_m / 2)
            right_cotter_y_m = cy_m

            # Vertices
            # tip is v1, tail is midpoint between v2 and v3
            tgt_width_m = self.target_width_m
            half_tgt_width_m = tgt_width_m / 2
            tgt_length_m = self.target_length_m * cos(nose_tilt_rad)

            # position v1 - then v2, v3 relative to v1
            v1_x_m = cx_m
            v1_y_m = cy_m + (self.tip_offset_ym * cos(nose_tilt_rad))
            v2_x_m = v1_x_m - half_tgt_width_m
            v3_x_m = v1_x_m + half_tgt_width_m
            v2_y_m = v3_y_m = v1_y_m - (tgt_length_m * cos(nose_tilt_rad))

            # body corners
            half_body_width_m = self.body_width_m / 2
            half_body_length_m = self.body_length_m / 2

            # top left
            top_left_x_m = cx_m - half_body_width_m
            top_left_y_m = cy_m + half_body_length_m

            # bottom left
            bottom_left_x_m = cx_m - half_body_width_m
            bottom_left_y_m = cy_m - half_body_length_m

            # bottom right
            bottom_right_x_m = cx_m + half_body_width_m
            bottom_right_y_m = cy_m - half_body_length_m

            # top right
            top_right_x_m = cx_m + half_body_width_m
            top_right_y_m = cy_m + half_body_length_m

            corners_m = [
                top_left_x_m, top_left_y_m,
                bottom_left_x_m, bottom_left_y_m,
                bottom_right_x_m, bottom_right_y_m,
                top_right_x_m, top_right_y_m
            ]

            # simple radius-based touch-points
            tp12_x_m, tp12_y_m = geom_lib.get_point_adistance_along_line(
                v1_x_m, v1_y_m, v2_x_m, v2_y_m, self.target_radius_m)
            tp13_x_m, tp13_y_m = geom_lib.get_point_adistance_along_line(
                v1_x_m, v1_y_m, v3_x_m, v3_y_m, self.target_radius_m)
            tp21_x_m, tp21_y_m = geom_lib.get_point_adistance_along_line(
                v2_x_m, v2_y_m, v1_x_m, v1_y_m, self.target_radius_m)
            tp23_x_m, tp23_y_m = geom_lib.get_point_adistance_along_line(
                v2_x_m, v2_y_m, v3_x_m, v3_y_m, self.target_radius_m)
            tp32_x_m, tp32_y_m = geom_lib.get_point_adistance_along_line(
                v3_x_m, v3_y_m, v2_x_m, v2_y_m, self.target_radius_m)
            tp31_x_m, tp31_y_m = geom_lib.get_point_adistance_along_line(
                v3_x_m, v3_y_m, v1_x_m, v1_y_m, self.target_radius_m)

            # simplified midpoints of touch-point pairs
            m12_x_m, m12_y_m = np.mean(
                [(tp13_x_m, tp13_y_m), (tp23_x_m, tp23_y_m)], axis=0)
            m23_x_m, m23_y_m = np.mean(
                [(tp21_x_m, tp21_y_m), (tp31_x_m, tp31_y_m)], axis=0)
            m31_x_m, m31_y_m = np.mean(
                [(tp32_x_m, tp32_y_m), (tp12_x_m, tp12_y_m)], axis=0)

            # communal rotation about centre
            # loop through all salient points and rotate them
            salient_descriptors = locals()

            for desc_key in [k for k in salient_descriptors if k.endswith('_m')]:
                desc_val = salient_descriptors[desc_key]

                if isinstance(desc_val, float):
                    # simple values
                    # we need to find xy coordinate pairs!
                    if desc_key.endswith('_x_m'):
                        try:
                            matched_y_key = desc_key.replace('_x_m', '_y_m')
                            if matched_y_key in salient_descriptors:
                                matched_y_val = salient_descriptors[matched_y_key]
                                x_pt_rotated, y_pt_rotated = su.getPointRotatedCounterClockwise(
                                    desc_val, matched_y_val, t_rad, cx_m, cy_m)
                                setattr(arena, desc_key, x_pt_rotated)
                                setattr(arena, matched_y_key, y_pt_rotated)
                        except Exception as e1:
                            err_line = sys.exc_info()[-1].tb_lineno
                            msg = 'Pose Error: unable to rotate salient property: {0} {1} on line {2}'.format(
                                desc_key, e1, err_line)
                            if self.logger:
                                self.logger.error(msg)
                            else:
                                print(msg)

                elif isinstance(desc_val, list):
                    try:
                        # list of values x, y, x, y, etc.
                        pts_rotated = [su.getPointRotatedCounterClockwise(
                            desc_val[i], desc_val[i + 1], t_rad, cx_m, cy_m) for i in range(0, len(desc_val), 2)]
                        setattr(arena, desc_key, list(sum(pts_rotated, ())))
                    except Exception as e2:
                        err_line = sys.exc_info()[-1].tb_lineno
                        msg = 'Pose Error: unable to rotate list: {0} {1} on line {2}'.format(
                            desc_key, e2, err_line)
                        if self.logger:
                            self.logger.error(msg)
                        else:
                            print(msg)
                elif isinstance(desc_val, np.ndarray):
                    try:
                        # array of values - assume contour format r, c
                        x_pts = [cos(t_rad) * (x - cx_m)
                                 for x in desc_val[:, 0]]
                        y_pts = [sin(t_rad) * (y - cy_m)
                                 for y in desc_val[:, 1]]
                        setattr(arena, desc_key, np.dstack([x_pts, y_pts])[0])
                    except Exception as e3:
                        err_line = sys.exc_info()[-1].tb_lineno
                        msg = 'Pose Error: unable to rotate array: {0} {1} on line {2}'.format(
                            desc_key, e3, err_line)
                        if self.logger:
                            self.logger.error(msg)
                        else:
                            print(msg)

            # composite corners
            arena.corners_m = [
                arena.top_left_x_m, arena.top_left_y_m,
                arena.bottom_left_x_m, arena.bottom_left_y_m,
                arena.bottom_right_x_m, arena.bottom_right_y_m,
                arena.top_right_x_m, arena.top_right_y_m
            ]

            # composite vertices
            arena.vertices_m = [arena.v1_x_m, arena.v1_y_m,
                                arena.v2_x_m, arena.v2_y_m, arena.v3_x_m, arena.v3_y_m]

            # Span
            arena.span_m = np.hypot(
                arena.tail_x_m - arena.tip_x_m, arena.tail_y_m - arena.tip_y_m)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Pose Error: unable to create the arena perspective "' + \
                str(e) + '" on line ' + str(err_line)
            try:
                self.logger.error(msg)
            except Exception:
                print(msg)

        return arena

    def create_plan_perspective(self, arena):
        '''
            scale cartesian metres => non-cartesian pixels
        '''

        plan = self.Perspective()

        try:
            x_scale = self.image_width_px / self.arena_width_m
            y_scale = self.image_height_px / self.arena_length_m

            # loop through all arena points and transform them
            arena_descriptors = vars(self.arena)

            for desc_key in [k for k in arena_descriptors if k.endswith('_m')]:
                desc_val = arena_descriptors[desc_key]

                if isinstance(desc_val, float) and not isnan(desc_val):
                    # simple values
                    # we need to find xy coordinate pairs!
                    try:
                        if desc_key.endswith('_x_m'):
                            matched_y_key = desc_key.replace('_x_m', '_y_m')
                            matched_y_val = arena_descriptors[matched_y_key]
                            x_pt_px = round(desc_val * x_scale)
                            y_pt_px = round(
                                self.image_height_px - (matched_y_val * y_scale))
                            x_desc_key = desc_key.replace('_x_m', '_x_px')
                            y_desc_key = matched_y_key.replace('_y_m', '_y_px')
                            setattr(plan, x_desc_key, x_pt_px)
                            setattr(plan, y_desc_key, y_pt_px)
                    except Exception as e2:
                        err_line = sys.exc_info()[-1].tb_lineno
                        msg = 'Pose Error: unable to scale salient property: {0} {1} on line {2}'.format(
                            desc_key, e2, err_line)
                        if self.logger:
                            self.logger.error(msg)
                        else:
                            print(msg)
                elif isinstance(desc_val, list):
                    try:
                        # list of values x, y, x, y, etc.
                        tgt_desc_key = desc_key.replace('_m', '_px')
                        x_pts_px = [round(ptx * x_scale)
                                    for ptx in desc_val[::2]]
                        y_pts_px = [round(self.image_height_px - (pty * y_scale))
                                    for pty in desc_val[1::2]]
                        setattr(plan, tgt_desc_key, list(
                            zip(x_pts_px, y_pts_px)))
                    except Exception as e3:
                        err_line = sys.exc_info()[-1].tb_lineno
                        msg = 'Pose Error: unable to scale list: {0} {1} on line {2}'.format(
                            desc_key, e3, err_line)
                        if self.logger:
                            self.logger.error(msg)
                        else:
                            print(msg)
                elif isinstance(desc_val, np.ndarray):
                    pass

            plan.t_rad = arena.t_rad
            plan.t_deg = arena.t_deg

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Pose Error: unable to create the plan perspective "' + \
                str(e) + '" on line ' + str(err_line)
            try:
                self.logger.error(msg)
            except Exception:
                print(msg)

        return plan

    def create_camera_perspective(self):
        '''
            scale metres => distorted, warped pixels
        '''
        cam = None
        try:

            # use inverse matrix transform to derive img coordinates
            if self.mapper is not None:

                # no mapper - no camera perspective!
                cam = self.Perspective()

                # loop through all arena points and transform them
                arena_descriptors = vars(self.arena)

                for desc_key in [k for k in arena_descriptors if k.endswith('_m')]:
                    desc_val = arena_descriptors[desc_key]

                    if isinstance(desc_val, float):
                        # simple values
                        # we need to find xy coordinate pairs!
                        if desc_key.endswith('_x_m'):
                            try:
                                cam_coords = None
                                matched_y_key = desc_key.replace(
                                    '_x_m', '_y_m')
                                matched_y_val = arena_descriptors[matched_y_key]
                                if matched_y_val is not None:
                                    cam_coords = self.mapper.reverse_coordinates(
                                        desc_val, matched_y_val)
                                    if cam_coords is not None:
                                        pt_px = np.round(
                                            cam_coords).astype(int)
                                        x_desc_key = desc_key.replace(
                                            '_x_m', '_x_px')
                                        y_desc_key = matched_y_key.replace(
                                            '_y_m', '_y_px')
                                        setattr(cam, x_desc_key, pt_px[0])
                                        setattr(cam, y_desc_key, pt_px[1])
                            except Exception as e1:
                                err_line = sys.exc_info()[-1].tb_lineno
                                msg = 'Pose Error: unable to create the camera perspective {} for ({}, {}) => ({}) on line {} mapper {}'.format(
                                    e1,
                                    desc_val,
                                    matched_y_val,
                                    cam_coords,
                                    err_line,
                                    self.mapper
                                )
                                try:
                                    self.logger.error(msg)
                                except Exception:
                                    print(msg)
                    elif isinstance(desc_val, list):
                        # list of values x, y, x, y, etc.
                        tgt_desc_key = desc_key.replace('_m', '_px')
                        cam_coords = self.mapper.reverse_coordinates(
                            desc_val[::2], desc_val[1::2])
                        if cam_coords is not None:
                            pts_px = np.round(cam_coords).astype(int)
                            setattr(cam, tgt_desc_key, np.column_stack(
                                pts_px).flatten().tolist())
                    elif isinstance(desc_val, np.ndarray):
                        # array of values - assume contour format r, c
                        tgt_desc_key = desc_key.replace('_m', '_px')
                        cam_coords = self.mapper.reverse_coordinates(
                            desc_val[:, 1], desc_val[:, 0])
                        if cam_coords is not None:
                            pts_px = np.round(cam_coords).astype(int)
                            setattr(cam, tgt_desc_key, np.dstack(pts_px)[0])

                # new theta
                if ('tail_x_px' in vars(cam) and
                    'tail_y_px' in vars(cam) and
                    'tip_x_px' in vars(cam) and
                        'tip_y_px' in vars(cam)):
                    cam.t_rad = geom_lib.get_angle_between_points(
                        cam.tail_x_px, cam.tail_y_px, cam.tip_x_px, cam.tip_y_px)
                    cam.t_deg = degrees(
                        cam.t_rad) if cam.t_rad is not None else -1

        except Exception as e2:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Pose Error: unable to create the camera perspective "' + \
                str(e2) + '" on line ' + str(err_line)
            try:
                self.logger.error(msg)
            except Exception:
                print(msg)

        return cam

    def copy(self):
        # return a copy of this object
        pose_copy = copy.copy(self)
        return pose_copy

    def __add__(self, mvmt):

        # add movement to get new pose
        # scale speeds into velocities
        v_left = mvmt.velocity_full_speed_mps * mvmt.left_speed_unit
        v_right = mvmt.velocity_full_speed_mps * mvmt.right_speed_unit
        (cx, cy), turn_radius, ccw = su.get_turn_circle_from_relative_velocities(
            self.arena.c_x_m,
            self.arena.c_y_m,
            self.arena.t_rad,
            v_left,
            v_right,
            mvmt.axle_track_m,
            debug=False,
            logger=self.logger
        )

        alpha_rad = su.get_turn_circle_sector_angle(
            turn_radius, ccw, v_left, v_right, mvmt.duration_s)

        # negate sector angle for clockwise rotation
        new_x_m, new_y_m = su.getPointRotatedCounterClockwise(
            self.arena.c_x_m, self.arena.c_y_m, alpha_rad, cx, cy)

        new_t_rad = su.sum_angles(self.arena.t_rad, alpha_rad)
        return Pose(new_x_m, new_y_m, new_t_rad)

    def __sub__(self, other):

        lin = ang = None

        if other is not None:
            lin = geom_lib.get_distance_between_points(
                self.arena.c_x_m, self.arena.c_y_m, other.arena.c_x_m, other.arena.c_y_m)
            ang = geom_lib.get_shortest_angle_between_radii(
                self.arena.t_rad, other.arena.t_rad)
        return lin, ang

    def as_arrow(self, length):
        arrow_from_pose = geom_lib.get_arrow_from_pose(
            self.arena.c_x_m, self.arena.c_y_m, self.arena.t_rad, length)
        start = round(arrow_from_pose[0], 2), round(arrow_from_pose[1], 2)
        finish = round(arrow_from_pose[2], 2), round(arrow_from_pose[3], 2)
        return start, finish

    def as_dict(self):
        pose_dict = {}
        try:
            pose_dict['c_x_m'] = round(self.arena.c_x_m, 2)
            pose_dict['c_y_m'] = round(self.arena.c_y_m, 2)
            pose_dict['t_deg'] = round(
                self.arena.t_deg) if self.arena.t_deg is not None else -1
            pose_dict['physical_span_m'] = self.target_length_m
            pose_dict['tip_m'] = (round(self.arena.tip_x_m, 3), round(
                self.arena.tip_y_m, 3)) if self.arena.tip_x_m is not None and self.arena.tip_y_m is not None else None
            pose_dict['tail_m'] = (round(self.arena.tail_x_m, 3), round(
                self.arena.tail_y_m, 3)) if self.arena.tail_x_m is not None and self.arena.tail_y_m is not None else None
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            info = 'Error in Pose.as_dict: ' + \
                str(e) + ' on line ' + str(err_line)
            self.logger.error(info)
        return pose_dict

    def as_concise_str(self):
        return '{0:.0f}@({1:.3f}, {2:.3f})'.format(
            degrees(self.arena.t_rad) if self.arena.t_deg is not None else -1,
            self.arena.c_x_m,
            self.arena.c_y_m
        )

    def as_key(self):
        '''
            return the pose as a 4 character string, suitable for dictionary keying
        '''
        bucket_factor = 1  # make this big enough to swallow jitter!
        return '{0:.0f}{1:.0f}'.format(
            bucket_factor * (self.arena.c_x_pc // bucket_factor),
            bucket_factor * (self.arena.c_y_pc // bucket_factor)
        )

    def __repr__(self):

        result = ''
        try:
            result += 'Origination: {0}'.format(self.origination.name if 'origination' in vars(
                self) and self.origination is not None else 'Unknown')
            if 'arena' in vars(self):
                result += '\nArena ({0}m, {1}m) {2} deg'.format(
                    round(self.arena.c_x_m, 2),
                    round(self.arena.c_y_m, 2),
                    round(self.arena.t_deg,
                          2) if self.arena.t_deg is not None else 'Unknown'
                )
                result += ' vertices: {0}m'.format(
                    [round(v, 2) for v in self.arena.vertices_m]
                )
            if 'plan' in vars(self):
                result += '\nPlan ({0}px, {1}px) {2} deg'.format(
                    round(self.plan.c_x_px, 2),
                    round(self.plan.c_y_px, 2),
                    round(self.plan.t_deg,
                          2) if self.plan.t_deg is not None else 'Unknown'
                )
                result += ' vertices: {0}px'.format(
                    self.plan.vertices_px
                )
            if 'cam' in vars(self) and 'c_x_px' in vars(self.cam) and 'c_y_px' in vars(self.cam):
                result += '\nCam ({0:.0f}px, {1:.0f}px) {2} deg'.format(
                    self.cam.c_x_px,
                    self.cam.c_y_px,
                    round(self.cam.t_deg,
                          2) if self.cam.t_deg is not None else 'Unknown'
                )
                result += ' vertices: {0}px'.format(
                    self.cam.vertices_px
                )
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            info = 'Error in Pose representation: ' + \
                str(e) + ' on line ' + str(err_line)
            self.logger.error(info)
        return result
