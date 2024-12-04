import sys
import numpy as np
from math import ceil


def densify(route, max_dist, logger=None, debug=False):
    '''
        Ensure all sequential pairs of points in route
            are at most max_dist apart, by adding intermediates
    '''
    try:

        if debug and logger is not None:
            logger.debug('route points: {0}'.format(route))

        dense_route_coords = []
        starts = [(fp[0], fp[1]) for fp in route[:-1]]
        finishes = [(fp[0], fp[1]) for fp in route[1:]]
        for lid in range(len(starts)):
            start = starts[lid]
            finish = finishes[lid]
            dist_pc = np.hypot(finish[0] - start[0], finish[1] - start[1])
            num_waypoints = ceil(dist_pc / max_dist)
            if debug and logger is not None:
                logger.debug('{0}-{1} start: ({2:.2f},{3:.2f}) finish: ({4:.2f}, {5:.2f}) dist: {6:.2f}% num_waypoints: {7}'.format(
                    lid,
                    lid + 1,
                    *start,
                    *finish,
                    dist_pc,
                    num_waypoints
                )
                )
            xs = np.linspace(start[0], finish[0],
                             num_waypoints, endpoint=False)
            ys = np.linspace(start[1], finish[1],
                             num_waypoints, endpoint=False)
            dense_line_points = np.round(
                np.dstack((xs.flatten(), ys.flatten()))[0], 3).tolist()

            dense_route_coords.extend(dense_line_points)

        dense_route_coords.append(finishes[-1])

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in densify: ' + str(e) +
                     ' on line ' + str(err_line))

    return dense_route_coords
