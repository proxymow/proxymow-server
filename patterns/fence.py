import sys


def calculate_route(fence_points_pc, _arena_width_m, _arena_length_m, _cutter_dia_m, logger, debug):

    # calculate the route within the fence
    fence_polygon_pts = []
    try:
        fence_point_count = len(fence_points_pc)
        for i in range(fence_point_count):
            fence_polygon_pts.append(
                (fence_points_pc[i].x, fence_points_pc[i].y))
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return fence_polygon_pts
