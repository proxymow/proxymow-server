import sys
from types import SimpleNamespace
from collections import namedtuple
import numpy as np

from destination import Destination, Attitude

Progress = namedtuple(
    'Progress', 'completed_m completed_pc outstanding_m outstanding_pc', defaults=(-1, -1, -1, -1))


class Itinerary(object):
    '''
        represents a list of destinations
        navigation is focused on driving:
            from the COMPLETED destination
            to the   CURRENT destination

        initially there is no COMPLETED, so from is current location
        finally CURRENT == COMPLETED

    '''

    def __init__(self, launch_pose=None, dest_list=None, plan_only=False, logger=None):
        '''
            Constructor
        '''
        self.destinations = []
        self.plan_only = plan_only
        self.logger = logger
        self.dest_ptr = 0  # kicks things off

        self.launch_dest = None
        if launch_pose is not None:
            self.launch_dest = Destination(
                launch_pose.arena.c_x_m, launch_pose.arena.c_y_m)
        else:
            self.dest_ptr = 1  # first path is [0] => [1]
        if dest_list is not None:
            self.add_destinations(dest_list)

    @property
    def num_destinations(self):
        return len(self.destinations)

    @property
    def is_complete(self):
        return self.dest_ptr >= self.num_destinations

    @property
    def outstanding(self):
        return self.num_destinations - self.dest_ptr

    def __str__(self):
        return 'Destinations: {}{}\n\tDestination Pointer: {}'.format(
            len(self.destinations),
            ['{}=>({}, {})'.format(
                d.attitude.name.replace('FORWARD', 'FWD').replace(
                    'REVERSE', 'REV').replace('DEFAULT', '').replace('DRIVE', 'DRV'),
                d.target_x,
                d.target_y
            ) for d in self.destinations],
            self.dest_ptr
        )

    def add_destination(self, x, y, att=Attitude.DEFAULT):
        self.destinations.append(Destination(x, y, att))

    def add_destinations(self, dest_list):
        for d in dest_list:
            self.add_destination(*d)

    def advance_pointer(self):
        if self.dest_ptr < len(self.destinations):
            self.dest_ptr += 1

    def get_current_path(self):
        start, finish = self.get_path_ends()
        return start.target_x, start.target_y, finish.target_x, finish.target_y, finish.attitude

    def get_path_ends(self):
        '''
            There are 5 states to consider:
                A: dest_ptr < 0
                B: dest_ptr == 0 and launch destination available
                C: dest_ptr == 0 and no launch destination
                D: dest_ptr == length, itinerary is complete
                E: dest_ptr > 0 and < length

            A no path available
            B path runs from launch to d[0]
            C partial path (-1, -1)..(d[0])
            D partial path (d[-1])..(-1, -1)
            E path runs from (d[ptr-1]..d[ptr])
        '''
        def_dict = {'target_x': None, 'target_y': None,
                    'attitude': Attitude.DEFAULT}
        start = SimpleNamespace(**def_dict)
        finish = SimpleNamespace(**def_dict)
        if self.dest_ptr < 0:
            pass  # no valid path
        if self.dest_ptr == 0 and len(self.destinations) > 0 and self.launch_dest is not None:
            start = self.launch_dest
            finish = self.destinations[self.dest_ptr]
        elif self.dest_ptr == 0 and len(self.destinations) > 0 and self.launch_dest is None:
            finish = self.destinations[self.dest_ptr]
        elif self.dest_ptr == len(self.destinations) and len(self.destinations) > 0:
            # indication of complete, but index is invalid
            start = self.destinations[self.dest_ptr - 1]
        elif len(self.destinations) >= 2:
            start = self.destinations[self.dest_ptr - 1]
            finish = self.destinations[self.dest_ptr]
        return start, finish

    @property
    def current_path_length(self):
        try:
            x1_m, y1_m, x2_m, y2_m = self.get_current_path()[:4]
            if None in (x1_m, y1_m, x2_m, y2_m):
                cpl = -1
            else:
                cpl = np.hypot(x2_m - x1_m, y2_m - y1_m)
        except Exception:
            cpl = -1
        return cpl

    def progress(self, cur_pos):

        result = Progress(-1, -1, -1, -1)
        try:
            cur_path_length_m = self.current_path_length
            start_x_m, start_y_m, finish_x_m, finish_y_m = self.get_current_path()[
                :4]
            if start_x_m is not None and start_y_m is not None:
                completed_distance_m = np.hypot(
                    cur_pos[0] - start_x_m, cur_pos[1] - start_y_m)
            else:
                completed_distance_m = -1
            if finish_x_m is not None and finish_y_m is not None:
                outstanding_distance_m = np.hypot(
                    finish_x_m - cur_pos[0], finish_y_m - cur_pos[1])
            else:
                outstanding_distance_m = -1
            result = Progress(
                completed_distance_m,
                round(completed_distance_m * 100 / cur_path_length_m),
                outstanding_distance_m,
                round(outstanding_distance_m * 100 / cur_path_length_m)
            )
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            if self.logger:
                self.logger.error('Error in progress: ' +
                                  str(e) + ' on line ' + str(err_line))
            else:
                print('Error in progress: ' + str(e) +
                      ' on line ' + str(err_line))

        return result
