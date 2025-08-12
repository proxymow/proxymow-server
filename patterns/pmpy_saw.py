import sys
import numpy as np
from shapely import geometry
from math import floor
import pprint


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, start_corner='SE', direction='H'):

    calc_rte_debug = True

    '''
        generic push-me-pull-you saw module for all 8 permutations
        generates parallel lanes, but keeps nodes apart
        useful to seperate stage_complete actions

        Start    Direction    Orientation    Crossing
        =====    =========    ===========    ========
        SE            V            CCW        x-desc
        SE            H            CW         y-asc
        SW            H            CCW        y-asc
        SW            V            CW         x-asc
        NW            V            CCW        x-asc
        NW            H            CW         y-desc
        NE            H            CCW        y-desc
        NE            V            CW         x-desc

        construct sequence of parallel opposing paths

        6            5
                     |
        3 ----       4
        |
        2  ----      1
    '''

    # check start corner
    valid_corners = ['SE', 'SW', 'NW', 'NE']
    if start_corner not in valid_corners:
        raise Exception(
            'start corner must be one of: {}'.format(valid_corners))

    # check direction
    valid_dir = ['V', 'H']
    if direction not in valid_dir:
        raise Exception('direction must be one of: {}'.format(valid_dir))

    # calculate the route within the fence
    route_pc = []

    if cutter_dia_m <= 0:
        cutter_dia_m = 0.1
        if calc_rte_debug:
            logger.warning(
                'pmpy using default cutter width: {0}'.format(cutter_dia_m))

    # cutter_dia_m = 0.75 # temporarily override configured cutter for testing
    if calc_rte_debug:
        logger.debug('pmpy using cutter width: {0}m'.format(cutter_dia_m))

    # using exact cutter dimension does not allow for any overlap
    #     this is equivalent to an overlap factor of 1.0
    # reduce the overlap factor to overlap the cutter lanes...
    overlap_factor = 0.67
    if calc_rte_debug:
        logger.debug('pmpy using overlap factor: {}'.format(overlap_factor))
    cutter_lane_width_m = cutter_dia_m * overlap_factor
    if calc_rte_debug:
        logger.debug('pmpy using a cutter lane width of: {}m'.format(
            cutter_lane_width_m))
        
    # calculate saw_offset_x and saw_offset_y depending on direction
    saw_offset = 5 # percentage
    saw_offset_x = saw_offset if direction == 'H' else 0
    saw_offset_y = saw_offset if direction == 'V' else 0

    # calculate cutter as percentage of arena
    cutter_lane_width_pc = 100 * cutter_lane_width_m / arena_width_m
    if calc_rte_debug:
        logger.debug('pmpy cutter lane as percentage of arena: {0:.1f}'.format(
            cutter_lane_width_pc))

    try:
        # convert fence points to (x, y) coordinates
        fence_point_count = len(fence_points_pc)
        fence_polygon_pts = []
        for i in range(fence_point_count):
            fence_polygon_pts.append(
                (fence_points_pc[i].x, fence_points_pc[i].y))

        fence_polygon = geometry.Polygon(fence_polygon_pts)
        fence_min_x = min([p[0] for p in fence_polygon_pts])
        fence_max_x = max([p[0] for p in fence_polygon_pts])
        fence_min_y = min([p[1] for p in fence_polygon_pts])
        fence_max_y = max([p[1] for p in fence_polygon_pts])

        # estimate number of verticals across the arena
        est_verts = floor(arena_width_m / cutter_lane_width_m)
        if calc_rte_debug:
            logger.debug(
                'pmpy estimated number of verticals: {0}'.format(est_verts))

        # ensure an even number of verticals to make valid rectangles!
        num_verts = (est_verts // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'pmpy even number of verticals: {0}'.format(num_verts))

        # estimate number of horizontals down the arena
        est_hors = floor(arena_length_m / cutter_lane_width_m)
        if calc_rte_debug:
            logger.debug(
                'stripes estimated number of horizontals: {0}'.format(est_hors))

        # ensure an even number of horizontals to make valid rectangles!
        num_hors = (est_hors // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'pmpy even number of horizontals: {0}'.format(num_hors))

        # define some rectangular skeletons across the fence

        perm = start_corner + direction
        if perm == 'SEV':
            verticals_x = np.linspace(fence_max_x, fence_min_x, num=num_verts)
        elif perm == 'SEH':
            horizontals_y = np.linspace(fence_min_y, fence_max_y, num=num_hors)
        elif perm == 'SWV':
            verticals_x = np.linspace(fence_min_x, fence_max_x, num=num_verts)
        elif perm == 'SWH':
            horizontals_y = np.linspace(fence_min_y, fence_max_y, num=num_hors)
        elif perm == 'NWV':
            verticals_x = np.linspace(fence_min_x, fence_max_x, num=num_verts)
        elif perm == 'NWH':
            horizontals_y = np.linspace(fence_max_y, fence_min_y, num=num_hors)
        elif perm == 'NEV':
            verticals_x = np.linspace(fence_max_x, fence_min_x, num=num_verts)
        elif perm == 'NEH':
            horizontals_y = np.linspace(fence_max_y, fence_min_y, num=num_hors)

        end_crossings = []
        start_crossings = []

        for j, v in enumerate(horizontals_y if direction == 'H' else verticals_x):

            if direction == 'H':
                if start_corner[1] == 'E':
                    bisector = geometry.LineString([(100, v), (0, v)])
                else:
                    bisector = geometry.LineString([(0, v), (100, v)])
            else:
                if start_corner[0] == 'N':
                    bisector = geometry.LineString([(v, 100), (v, 0)])
                else:
                    bisector = geometry.LineString([(v, 0), (v, 100)])

            # find points of contact on fence that intersects with bisector
            crossings = bisector.intersection(fence_polygon)
            num_crossings = np.asarray(crossings.coords).shape[0]
            if num_crossings == 2:
                start_crossing = crossings.coords[0]
                end_crossing = crossings.coords[1]
                if calc_rte_debug:
                    logger.debug('start crossing: {0} end crossing: {1}'.format(
                        start_crossing, end_crossing))
                if j % 2 == 1:
                    start_crossing = (start_crossing[0], start_crossing[1])
                    end_crossing = (end_crossing[0], end_crossing[1])
                    if calc_rte_debug:
                        logger.debug('horizontal pmpy offset start crossing: {0} end crossing: {1}'.format(
                            start_crossing, end_crossing))
                start_crossings.append(start_crossing)
                end_crossings.append(end_crossing)
            else:
                if calc_rte_debug:
                    logger.debug('single crossing, ignoring horizontal')

        # alternate crossing offset

        open_rect_index = 0

        try:
            while True:

                if open_rect_index == 0:
                    route_pc.append(start_crossings[open_rect_index])
                    
                x1 = end_crossings[open_rect_index][0]
                y1 = end_crossings[open_rect_index][1]
                x2 = max(0, end_crossings[open_rect_index + 1][0] - saw_offset_x)
                y2 = min(100, end_crossings[open_rect_index + 1][1] + saw_offset_y)
                x3 = start_crossings[open_rect_index + 1][0]
                y3 = start_crossings[open_rect_index + 1][1]
                x4 = min(100, start_crossings[open_rect_index + 2][0] + saw_offset_x)
                y4 = max(0, start_crossings[open_rect_index + 2][1] - saw_offset_y)
                
                route_pc.extend([(x1, y1), (x2, y2), (x3, y3), (x4, y4)])
                open_rect_index += 2  # stripe_width
        except Exception as e1:
            err_line = sys.exc_info()[-1].tb_lineno
            if calc_rte_debug:
                logger.debug(
                    'pmpy exhausted space {0} on line {1}'.format(e1, err_line))

        if calc_rte_debug:
            logger.debug(pprint.pformat(route_pc))

    except Exception as e2:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in pmpy route calculation: ' +
                     str(e2) + ' on line ' + str(err_line))

    return route_pc
