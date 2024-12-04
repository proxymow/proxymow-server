import sys
from patterns import ever_decreasing_polygons
from pattern_utils import densify


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger):

    calc_rte_debug = False
    max_seg_pc = 20

    try:

        route_pc = ever_decreasing_polygons.calculate_route(
            fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, calc_rte_debug)
        # max distance between nodes
        dense_route_pc = densify(route_pc, max_seg_pc, logger)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return dense_route_pc
