import sys
import numpy as np
from shapely import geometry
from math import floor
import pprint

def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, debug, start_corner='SE', direction='H'):

    calc_rte_debug = debug

    '''
        generic push-me-pull-you module for all 8 permutations

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
                'using default cutter width: {}'.format(cutter_dia_m))

    # cutter_dia_m = 0.75 # temporarily override configured cutter for testing
    if calc_rte_debug:
        logger.debug('using cutter width: {}m'.format(cutter_dia_m))

    # using exact cutter dimension does not allow for any overlap
    #     this is equivalent to an overlap factor of 1.0
    # reduce the overlap factor to overlap the cutter lanes...
    # but be mindful of making inter-node gaps too small!
    # this is governed by constants.MINIMUM_INTER_NODE_DISTANCE_M
    # check the patterns log for skipped nodes
    # for example 0.75 was too conservative and caused skipped nodes
    # 0.92 was too liberal and caused gaps
    overlap_factor = 1.0
    if calc_rte_debug:
        logger.debug('using overlap factor: {}'.format(overlap_factor))
    cutter_lane_width_m = cutter_dia_m * overlap_factor
    if calc_rte_debug:
        logger.debug('using a cutter lane width of: {}m'.format(
            cutter_lane_width_m))

    try:
        # convert fence points to (x, y) coordinates
        fence_point_count = len(fence_points_pc)
        fence_polygon_pts = []
        for i in range(fence_point_count):
            fence_polygon_pts.append(
                (fence_points_pc[i].x, fence_points_pc[i].y))

        fence_polygon = geometry.Polygon(fence_polygon_pts)
        fence_min_x_pc = min([p[0] for p in fence_polygon_pts])
        fence_max_x_pc = max([p[0] for p in fence_polygon_pts])
        fence_min_y_pc = min([p[1] for p in fence_polygon_pts])
        fence_max_y_pc = max([p[1] for p in fence_polygon_pts])
        
        fence_width_pc = fence_max_x_pc - fence_min_x_pc
        fence_length_pc = fence_max_y_pc - fence_min_y_pc
        if calc_rte_debug:
            logger.debug(
                'fence_width_pc: {:.1f}% fence_length_pc: {:.1f}'.format(fence_width_pc, fence_length_pc))

        fence_width_m = fence_width_pc * arena_width_m / 100
        fence_length_m = fence_length_pc * arena_length_m / 100
        if calc_rte_debug:
            logger.debug(
                'fence_width_m: {:.3f} fence_length_m: {:.3f}'.format(fence_width_m, fence_length_m))

        # estimate number of verticals across the fence
        est_verts = floor(fence_width_m / cutter_lane_width_m)
        if calc_rte_debug:
            logger.debug(
                'estimated number of verticals: {}'.format(est_verts))

        # ensure an even number of verticals to return mower to starting edge
        num_verts = (est_verts // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'even number of verticals: {}'.format(num_verts))

        # estimate number of horizontals down the fence
        est_hors = floor(fence_length_m / cutter_lane_width_m)
        if calc_rte_debug:
            logger.debug(
                'estimated number of horizontals: {}'.format(est_hors))

        # ensure an even number of horizontals to return mower to starting edge
        num_hors = (est_hors // 2) * 2
        if calc_rte_debug:
            logger.debug(
                'even number of horizontals: {}'.format(num_hors))

        # define a grid across the fence
        perm = start_corner + direction
        if perm == 'SEV':
            verticals_x = np.linspace(fence_max_x_pc, fence_min_x_pc, num=num_verts)
        elif perm == 'SEH':
            horizontals_y = np.linspace(fence_min_y_pc, fence_max_y_pc, num=num_hors)
        elif perm == 'SWV':
            verticals_x = np.linspace(fence_min_x_pc, fence_max_x_pc, num=num_verts)
        elif perm == 'SWH':
            horizontals_y = np.linspace(fence_min_y_pc, fence_max_y_pc, num=num_hors)
        elif perm == 'NWV':
            verticals_x = np.linspace(fence_min_x_pc, fence_max_x_pc, num=num_verts)
        elif perm == 'NWH':
            horizontals_y = np.linspace(fence_max_y_pc, fence_min_y_pc, num=num_hors)
        elif perm == 'NEV':
            verticals_x = np.linspace(fence_max_x_pc, fence_min_x_pc, num=num_verts)
        elif perm == 'NEH':
            horizontals_y = np.linspace(fence_max_y_pc, fence_min_y_pc, num=num_hors)

        if calc_rte_debug:
            logger.debug(
                'horizontal y interval: {} vertical x interval: {}'.format(
                    np.round(horizontals_y) if direction == 'H' else '', 
                    np.round(verticals_x) if direction == 'V' else '')
                )

        end_crossings = []
        start_crossings = []

        for offset in (horizontals_y if direction == 'H' else verticals_x):
            if direction == 'H':
                if start_corner[1] == 'E':
                    bisector = geometry.LineString([(100, offset), (0, offset)])
                else:
                    bisector = geometry.LineString([(0, offset), (100, offset)])
            else:
                if start_corner[0] == 'N':
                    bisector = geometry.LineString([(offset, 100), (offset, 0)])
                else:
                    bisector = geometry.LineString([(offset, 0), (offset, 100)])

            # find points of contact on fence where gridlines intersect
            crossings_geom = bisector.intersection(fence_polygon)
            if crossings_geom.geom_type == 'MultiLineString':
                # multiple line segments
                crossings_ls = list(crossings_geom.geoms)[0] # can only accept first linestring
            elif crossings_geom.geom_type == 'MultiPoint':
                # multiple points
                crossings_ls = list(crossings_geom.geoms)[0] # can only accept first point
            else:
                # single line
                crossings_ls = crossings_geom
            num_crossings = np.asarray(crossings_ls.coords).shape[0]
            if num_crossings == 2:
                start_crossing_pt = crossings_ls.coords[0]
                end_crossing_pt = crossings_ls.coords[1]
                if calc_rte_debug:
                    logger.debug('start crossing: {} end crossing: {}'.format(
                        start_crossing_pt, end_crossing_pt))
                start_crossings.append(start_crossing_pt)
                end_crossings.append(end_crossing_pt)
            else:
                if calc_rte_debug:
                    logger.debug('single crossing point, ignoring intersection')

        # alternate crossing offset
        open_rect_index = 0

        try:
            while True:
                if open_rect_index == 0:
                    route_pc.append(start_crossings[open_rect_index])
                route_pc.append(
                    (end_crossings[open_rect_index][0], end_crossings[open_rect_index][1]))               # 1
                route_pc.append(
                    (end_crossings[open_rect_index + 1][0], end_crossings[open_rect_index + 1][1]))       # 2
                route_pc.append(
                    (start_crossings[open_rect_index + 1][0], start_crossings[open_rect_index + 1][1]))   # 3
                route_pc.append(
                    (start_crossings[open_rect_index + 2][0], start_crossings[open_rect_index + 2][1]))   # 4
                open_rect_index += 2  # stripe_width
        except Exception as e1:
            err_line = sys.exc_info()[-1].tb_lineno
            if calc_rte_debug:
                logger.debug(
                    'exhausted space {} on line {}'.format(e1, err_line)
                )

        if calc_rte_debug:
            logger.debug(pprint.pformat(route_pc))

    except Exception as e2:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in pmpy route calculation: ' +
                     str(e2) + ' on line ' + str(err_line))
        raise(e2)
    return route_pc
