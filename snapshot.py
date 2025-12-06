import sys
import time
from itertools import count
from enum import Enum
from math import degrees, sin, cos, pi

from poses import Pose, PoseOrigination
import constants


class SnapshotGrowth(Enum):
    EMPTY = 0
    IMAGED = 1
    POSED = 2
    PLANNED = 3


class Snapshot():
    '''
        Represents the single frame from a raw capture
    '''

    # class variables
    location_stats = {}
    _ssid = count(0)

    def __init__(self, container=None, ssid=None, logger=None):
        self._t_zero = time.time()
        self._container = container
        if ssid is None:
            self.ssid = next(self._ssid) % constants.MAX_SNAPSHOT_ID
        else:
            self.ssid = ssid
        self._logger = logger
        self._growth = SnapshotGrowth.EMPTY
        self._fence_masked_img_arr = None
        self._pose = None
        self.run_elapsed_secs = 0
        self.loc_stat_count = 0
        self.loc_quality = 100
        self.best_proj_conf_pc = 0
        self._contours = []
        self.cont_count = 0
        self.fltrd_count = 0
        self._strategy_name = None
        self._terms = None
        self._rules = None

        # we haven't been added yet, so latest is p2 and penultimate is p1
        p1 = self._container.penultimate_pose()
        p2 = self._container.latest_pose()

        s1 = self._container[list(self._container.keys())[-2]].ssid if len(self._container.keys()) > 1 else -1
        s2 = self._container[list(self._container.keys())[-1]].ssid if len(self._container.keys()) > 0 else -1

        # first log all the ssids
        if self._logger:
            self._logger.debug(
                'Snapshot Constructor - Locate Snapshots: {0}'.format(self._container.keys()))
            self._logger.debug('Snapshot Constructor - Poses: {0}'.format(
                [ss._pose.as_concise_str() if ss._pose is not None else
                 '|{0}|'.format(ss._extrapolated_pose.as_concise_str()) if ss._extrapolated_pose is not None else
                 'None' for ss in self._container.values()]))
        # [p1, p2] => p3
        if self._logger:
            self._logger.debug('Potential Extrapolation sources: penultimate_pose => latest_pose {} {} {} => {} {} {}'.format(
                s1, 
                p1.as_concise_str() if p1 is not None else 'None', 
                p1.origination if p1 is not None else '', 
                s2, 
                p2.as_concise_str() if p2 is not None else 'None',
                p2.origination if p2 is not None else '' 
                )
            )
        # Least restrictive without free-for-all
        if (p1 is not None and 
            p2 is not None and 
            (p1.origination == PoseOrigination.DETECTED or p2.origination == PoseOrigination.DETECTED)):
            p_start = p1
            p_finish = p2
        else:
            p_start = None
            p_finish = None

        self.extrapolate_pose(p_start, p_finish)

    def set_pose(self, pose):
        self._pose = pose
        self._growth = SnapshotGrowth.POSED

    def extrapolate_pose(self, p_start, p_finish):

        # use previous snapshots to extrapolate pose
        # assumes snapshots occur at regular intervals

        try:
            if p_start is not None and p_finish is not None:
                linear_displacement, angular_displacement = p_finish - p_start
                if (
                    linear_displacement > constants.FROZEN_DISTANCE_THRESHOLD_METRES or
                    degrees(angular_displacement) > constants.FROZEN_ANGLE_THRESHOLD_DEGREES
                    ): 
                    t1 = p_start.t_zero
                    t2 = p_finish.t_zero
                    time_displacement = round(t2 - t1, 2)
                    if self._logger:
                        self._logger.debug(
                            'Snapshot Constructor - linear_displacement: {0:.2f}m angular_displacement: {1:.2f}deg time_displacement: {2:.2f}secs'.format(
                                linear_displacement,
                                degrees(angular_displacement),
                                time_displacement)
                        )
                    x_displacement = linear_displacement * \
                        sin((2 * pi) - p_finish.arena.t_rad)  # ccw
                    y_displacement = linear_displacement * \
                        cos((2 * pi) - p_finish.arena.t_rad)
                    if self._logger:
                        self._logger.debug(
                            'Snapshot Constructor - calculating extrapolation displacement ({0:.2f}, {1:.2f})'.format(x_displacement, y_displacement))
                    p3_cxm = p_finish.arena.c_x_m + \
                        (x_displacement * time_displacement)
                    p3_cym = p_finish.arena.c_y_m + \
                        (y_displacement * time_displacement)
                    if self._logger:
                        self._logger.debug(
                            'Snapshot Constructor - calculating extrapolation landing ({0:.2f}, {1:.2f})'.format(p3_cxm, p3_cym))
                    self._extrapolated_pose = Pose(
                        p3_cxm, p3_cym, p_finish.arena.t_rad)
                    self._extrapolated_pose.origination = PoseOrigination.PREDICTED
                    if self._logger:
                        self._logger.debug('Snapshot Constructor - Posting Extrapolation {0}'.format(
                            self._extrapolated_pose.as_concise_str()))
                else:
                    if self._logger:
                        self._logger.debug(
                            'Snapshot Constructor - Unable to compute extrapolated pose - insufficient discrimination')
                    self._extrapolated_pose = None            
            else:
                if self._logger:
                    self._logger.debug(
                        'Snapshot Constructor - Unable to compute extrapolated pose')
                self._extrapolated_pose = None

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Snapshot Extrapolated Pose Error: ' + \
                str(e) + ' on line ' + str(err_line)
            if self._logger:
                self._logger.error(msg)
            else:
                print(msg)

    def as_public_dict(self):
        pdict = {k: round(v, 2) for k, v in vars(
            self).items() if not k.startswith('_')}
        pdict['growth'] = self._growth.value
        if self._pose is not None:
            pdict['current'] = self._pose.as_concise_str()
        return pdict
