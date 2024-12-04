import sys


def calculate_route(fence_points_pc, _arena_width_m, _arena_length_m, _cutter_dia_m, logger):

    calc_rte_debug = False

    # calculate the route within the fence
    route_pc = []

    try:
        fence_point_count = len(fence_points_pc)
        if calc_rte_debug:
            logger.debug('fence_point_count: {0}'.format(fence_point_count))
        fence_polygon_pts = []
        for i in range(fence_point_count):
            fence_polygon_pts.append(
                (fence_points_pc[i].x, fence_points_pc[i].y))
        for p in fence_polygon_pts:
            route_pc.append(p)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return route_pc
