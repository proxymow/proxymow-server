import sys
import numpy as np
import geom_lib
from math import ceil


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger):

    calc_rte_debug = False

    # calculate the route within the fence
    route_pc = []

    try:

        if calc_rte_debug:
            logger.debug('width_m: {0}'.format(arena_width_m))
            logger.debug('length_m: {0}'.format(arena_length_m))
            logger.debug(
                'fence point percentages: {0}'.format(fence_points_pc))

        fence_point_count = len(fence_points_pc)
        fence_polygon_pts = []
        for i in range(fence_point_count):
            fence_polygon_pts.append(
                (fence_points_pc[i].x, fence_points_pc[i].y))

        lane_overlap_m = 0
        if cutter_dia_m == 0:
            cutter_width_m = arena_width_m / 2  # default to one circuit
        else:
            cutter_width_m = cutter_dia_m - lane_overlap_m

        max_cct_count = 100 if cutter_dia_m > 0 else 1

        # first calculate centroid
        centroid = geom_lib.polygon_centroid(
            [(p.x, p.y) for p in fence_points_pc])
        if calc_rte_debug:
            logger.debug('centroid: {0}'.format(centroid))

        # then calculate radial lengths
        radial_lengths = [np.hypot(p.x - centroid.x, p.y - centroid.y)
                          for p in fence_points_pc]
        if calc_rte_debug:
            logger.debug('radial_lengths: {0}'.format(radial_lengths))

        # find longest radial as it dictates number of circuits
        longest_radial = max(radial_lengths)
        if calc_rte_debug:
            logger.debug('longest radial: {0}'.format(longest_radial))

        # how many lane widths are needed?
        cutter_width_pc = 100 * cutter_width_m / arena_width_m
        max_cct_count = ceil(longest_radial / cutter_width_pc)
        if calc_rte_debug:
            logger.debug('cutter_width_m: {0} arena_width_m: {1} cutter_width_pc: {2} max_cct_count: {3}'.format(
                cutter_width_m, arena_width_m, cutter_width_pc, max_cct_count
            ))

        # what are the points?
        xs = np.linspace([fp.x for fp in fence_points_pc],
                         centroid.x, max_cct_count + 2, endpoint=False)
        ys = np.linspace([fp.y for fp in fence_points_pc],
                         centroid.y, max_cct_count + 2, endpoint=False)
        route_pc = np.round(
            np.dstack((xs.flatten(), ys.flatten()))[0], 3).tolist()

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return route_pc
