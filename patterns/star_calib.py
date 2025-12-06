import sys
import geom_lib
from math import cos, sin, radians
from shapely.geometry import LineString, Polygon


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, debug):

    calc_rte_debug = debug

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

        fence_polygon = Polygon(fence_polygon_pts)

        # first calculate centroid
        centroid = geom_lib.polygon_centroid(
            [(p.x, p.y) for p in fence_points_pc])
        if calc_rte_debug:
            logger.debug('centroid: {0}'.format(centroid))

        # start  in middle
        route_pc.append((centroid.x, centroid.y))

        # create radials over 360 degree range
        # angular increment
        ang_inc_deg = 30
        contacts = []
        for omega in range(0, 360, ang_inc_deg):
            if calc_rte_debug:
                logger.debug('omega angle: {0}'.format(omega))

            # create radial
            omega_rads = radians(omega)
            rx = sin(omega_rads) * 100
            ry = cos(omega_rads) * 100
            radial = LineString(
                [(centroid.x, centroid.y), (centroid.x + rx, centroid.y + ry)])
            if calc_rte_debug:
                logger.debug('radial: {0}'.format(radial))

            # find point of contact on fence that intersects with radial
            inter_line = fence_polygon.intersection(radial)
            contact = inter_line.coords[-1]
            if calc_rte_debug:
                logger.debug(
                    'intersection point of contact: {0}'.format(contact))

            contacts.append(contact)

        # start at top
        route_pc.append(contacts[0])

        contact_count = len(contacts)
        opp_offset = int(contact_count / 2)
        n = 0
        opp_index = int((n + opp_offset - 1) % contact_count)
        for n in range(contact_count - 1):
            if calc_rte_debug:
                logger.debug('point index: {0}'.format(n))
                logger.debug('opposite point index: {0}'.format(opp_index))
            route_pc.append(contacts[opp_index])
            opp_index = int((opp_index + opp_offset - 1) % contact_count)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return route_pc
