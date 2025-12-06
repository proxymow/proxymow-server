import sys
import geom_lib
from math import cos, sin, radians
from shapely.geometry import LineString, Polygon
from shapely import affinity


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, _cutter_dia_m, logger, debug):

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

        inner_fence_polygon = affinity.scale(
            fence_polygon, xfact=0.8, yfact=0.8)
        if inner_fence_polygon.geom_type == 'MultiPolygon':
            inner_fence_polygon = inner_fence_polygon[0]

        # first calculate centroid
        centroid = geom_lib.polygon_centroid(
            [(p.x, p.y) for p in fence_points_pc])
        if calc_rte_debug:
            logger.debug('centroid: {0}'.format(centroid))

        # create radials over 360 degree range
        # angular increment
        ang_inc_deg = 5
        diamond_angle_deg = 30
        contacts = []
        left_contacts = []
        right_contacts = []
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

            # find point of contact on inner fence that intersects with radial
            inner_inter_line = inner_fence_polygon.intersection(radial)
            inner_contact = inner_inter_line.coords[-1]
            if calc_rte_debug:
                logger.debug(
                    'inner intersection point of contact: {0}'.format(inner_contact))
            # inner_contacts.append(inner_contact)

            # rotate contact point cw and ccw
            ccw_line = affinity.rotate(
                inner_inter_line, diamond_angle_deg / 2, (contact[0], contact[1]))
            cw_line = affinity.rotate(
                inner_inter_line, diamond_angle_deg / -2, (contact[0], contact[1]))
            ccw_inner_contact = ccw_line.coords[-1]
            right_contacts.append(ccw_inner_contact)
            cw_inner_contact = cw_line.coords[-1]
            left_contacts.append(cw_inner_contact)

        # start at top
        # route_pc.append(inner_contacts[0])
        route_pc.append(left_contacts[0])
        route_pc.append(contacts[0])
        route_pc.append(right_contacts[0])

        contact_count = len(contacts)
        opp_offset = int(contact_count / 2)
        n = 0
        opp_index = int((n + opp_offset - 1) % contact_count)
        for n in range(contact_count - 1):
            if calc_rte_debug:
                logger.debug('point index: {0}'.format(n))
            if calc_rte_debug:
                logger.debug('opposite point index:{0}'.format(opp_index))
            # route_pc.append(inner_contacts[opp_index])
            route_pc.append(left_contacts[opp_index])
            route_pc.append(contacts[opp_index])
            route_pc.append(right_contacts[opp_index])
            opp_index = int((opp_index + opp_offset - 1) % contact_count)

        for n, m in enumerate(route_pc):
            if calc_rte_debug:
                logger.debug('{0} ({1:.2f}, {2:.2f})'.format(n, m[0], m[1]))

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.log_error('Error in route calculation: ' +
              str(e) + ' on line ' + str(err_line))

    return route_pc
