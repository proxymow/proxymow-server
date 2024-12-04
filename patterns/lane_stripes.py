import sys
import numpy as np
from shapely import geometry
from math import floor
from pattern_utils import densify


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, start_corner='SE', direction='V'):

    calc_rte_debug = True

    '''
        generic stripe module for all 8 permutations

        Start    Direction    Orientation    Crossing
        =====    =========    ===========    ========
        SE            V            CCW        x-desc
        SE            H            CW         y-asc
        SW            V            CW         x-asc
        SW            H            CCW        y-asc
        NW            V            CCW        x-asc
        NW            H            CW         y-desc
        NE            V            CW         x-desc
        NE            H            CCW        y-desc

        construct sequence of open proper isosceles trapezoids
        i.e. rectangles with a full left side, shortened right side, and shortened bottom

        1
                          >                 2

                                            v

                                            3
            4             <

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
                'stripes using default cutter width: {0}'.format(cutter_dia_m))

    # cutter_dia_m = 0.5 # temporarily override configured cutter for testing

    # using exact cutter dimension does not allow for any overlap
    overlap_factor = 0.67
    cutter_lane_width_m = cutter_dia_m * overlap_factor

    # calculate cutter as percentage of arena
    cutter_lane_width_pc = 100 * cutter_lane_width_m / arena_width_m
    if calc_rte_debug:
        logger.debug('stripes cutter as percentage of arena: {0:.1f}'.format(
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
                'stripes estimated number of verticals: {0}'.format(est_verts))

        # ensure an even number of verticals to make valid rectangles!
        num_verts = (est_verts // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'stripes even number of verticals: {0}'.format(num_verts))

        # estimate number of horizontals down the arena
        est_hors = floor(arena_length_m / cutter_lane_width_m)
        if calc_rte_debug:
            logger.debug(
                'stripes estimated number of horizontals: {0}'.format(est_hors))

        # ensure an even number of horizontals to make valid rectangles!
        num_hors = (est_hors // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'stripes even number of horizontals: {0}'.format(num_hors))

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
                    logger.debug('horizontal stripes start crossing: {0} end crossing: {1}'.format(
                        start_crossing, end_crossing))
                if j % 2 == 1:
                    start_crossing = (start_crossing[0], start_crossing[1])
                    end_crossing = (end_crossing[0], end_crossing[1])
                    if calc_rte_debug:
                        logger.debug('horizontal stripes offset start crossing: {0} end crossing: {1}'.format(
                            start_crossing, end_crossing))
                start_crossings.append(start_crossing)
                end_crossings.append(end_crossing)
            else:
                if calc_rte_debug:
                    logger.debug(
                        'horizontal stripes single crossing, ignoring horizontal')

        # alternate crossing offset
        alt_crossing_offset = cutter_lane_width_pc  # e.g. 2%

        open_rect_index = 0
        stripe_width = 6  # verticals

        try:
            while True:
                striped_lanes = 0
                while striped_lanes < stripe_width:

                    if striped_lanes == 0:
                        route_pc.append(start_crossings[open_rect_index])

                    route_pc.append(end_crossings[open_rect_index])

                    # now move down {stripe_width} verticals - constrained
                    open_rect_index = open_rect_index + stripe_width

                    if direction == 'V':
                        if start_corner[0] == 'S':
                            route_pc.append(
                                (end_crossings[open_rect_index][0], end_crossings[open_rect_index][1] - alt_crossing_offset))
                            route_pc.append(
                                (start_crossings[open_rect_index][0], start_crossings[open_rect_index][1] + alt_crossing_offset))
                        else:
                            route_pc.append(
                                (end_crossings[open_rect_index][0], end_crossings[open_rect_index][1] + alt_crossing_offset))
                            route_pc.append(
                                (start_crossings[open_rect_index][0], start_crossings[open_rect_index][1] - alt_crossing_offset))
                    else:
                        if start_corner[1] == 'W':
                            route_pc.append(
                                (end_crossings[open_rect_index][0] - alt_crossing_offset, end_crossings[open_rect_index][1]))
                            route_pc.append(
                                (start_crossings[open_rect_index][0] + alt_crossing_offset, start_crossings[open_rect_index][1]))
                        else:
                            route_pc.append(
                                (end_crossings[open_rect_index][0] + alt_crossing_offset, end_crossings[open_rect_index][1]))
                            route_pc.append(
                                (start_crossings[open_rect_index][0] - alt_crossing_offset, start_crossings[open_rect_index][1]))

                    # move back shortened bottom [5]?
                    if striped_lanes < (stripe_width - 1):
                        open_rect_index -= (stripe_width - 1)
                        route_pc.append(start_crossings[open_rect_index])

                    # increment count
                    striped_lanes += 1
                open_rect_index += 1  # stripe_width
        except Exception as e1:
            err_line = sys.exc_info()[-1].tb_lineno
            if calc_rte_debug:
                logger.debug(
                    'stripes exhausted space {0} on line {1}'.format(e1, err_line))
            pass

        # max distance between nodes 40%
        dense_route_pc = densify(route_pc, 40, logger)

    except Exception as e2:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in stripes route calculation: ' +
                     str(e2) + ' on line ' + str(err_line))

    return dense_route_pc
