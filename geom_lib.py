import sys
from math import sqrt, pi, sin, cos, atan2, acos, degrees, ceil
from shapely.geometry import LineString
from shapely.geometry import Polygon
import numpy as np


def get_angle_between_cartesian_points(tail_x, tail_y, tip_x, tip_y, default=None):
    # calculate the angle between 2 world points
    # first is the tail, 2nd is the tip
    return get_angle_between_points(tail_x, tip_y, tip_x, tail_y, default)


def get_angle_between_points(tail_x, tail_y, tip_x, tip_y, default=None):

    # calculate the angle between 2 points
    # if the points are coincident, then return default
    result = default

    # returns result in radians
    if tail_x is not None and tail_y is not None and tip_x is not None and tip_y is not None:

        delta_x = tip_x - tail_x
        delta_y = tip_y - tail_y

        if abs(delta_x) > 0.001 or abs(delta_y) > 0.001:

            theta_radians = atan2(delta_x, delta_y)
            theta_adj = theta_radians + pi
            result = theta_adj if theta_adj < (
                2 * pi) else theta_adj - (2 * pi)

    return result


def get_distance_between_points(x1, y1, x2, y2):

    # compute deltas
    delta_x = x2 - x1
    delta_y = y2 - y1

    # compute distance from pythag
    dist = sqrt(delta_x ** 2 + delta_y ** 2)

    return dist


def get_shortest_angle_between_radii(r1, r2):
    # shortest route angle
    return (((r2 - r1) + pi) % (2 * pi)) - pi


def diff_angles(t1, t2, fmt=0):
    '''
        diff angles accounting for underflow/overflow
        fmt = 0 is radians, 1 is degrees
    '''
    if fmt == 0:
        # radians
        whole = 2 * pi
        half = whole / 2
    else:
        # degrees
        whole = 360
        half = 180

    diff = (t2 - t1 + half) % whole - half
    return diff + whole if diff < -half else diff


def checkLineIntersection(line1StartX, line1StartY, line1EndX, line1EndY, line2StartX, line2StartY, line2EndX, line2EndY):

    # if the lines intersect, the result contains the x and y of the intersection
    # (treating the lines as infinite) and booleans for whether line segment 1 or line segment 2 contain the point
    # variables: denominator, a, b, numerator1, numerator2, result
    result = {
        'x': None,
        'y': None,
        'onLine1': False,
        'onLine2': False
    }
    denominator = ((line2EndY - line2StartY) * (line1EndX - line1StartX)) - \
        ((line2EndX - line2StartX) * (line1EndY - line1StartY))
    if denominator == 0:
        return result

    a = line1StartY - line2StartY
    b = line1StartX - line2StartX
    numerator1 = ((line2EndX - line2StartX) * a) - \
        ((line2EndY - line2StartY) * b)
    numerator2 = ((line1EndX - line1StartX) * a) - \
        ((line1EndY - line1StartY) * b)
    a = numerator1 / denominator
    b = numerator2 / denominator

    # if we cast these lines infinitely in both directions, they intersect here:
    result['x'] = line1StartX + (a * (line1EndX - line1StartX))
    result['y'] = line1StartY + (a * (line1EndY - line1StartY))
    # if line1 is a segment and line2 is infinite, they intersect if:
    if a > 0 and a < 1:
        result['onLine1'] = True

    # if line2 is a segment and line1 is infinite, they intersect if:
    if b > 0 and b < 1:
        result['onLine2'] = True

    # if line1 and line2 are segments, they intersect if both of the above are true
    return result


def polygon_centroid(polygon_pts):
    centroid = (0, 0)
    try:
        if len(polygon_pts) > 0:
            if isinstance(polygon_pts, np.ndarray):
                polygon = Polygon(polygon_pts)
            else:
                polygon = Polygon(polygon_pts)
            centroid = polygon.centroid
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        print('Error in polygon centroid calculation: ' +
              str(e) + ' on line ' + str(err_line))
    return centroid


def midpoint(lineStartX, lineStartY, lineEndX, lineEndY):
    result = {}
    line = LineString([(lineStartX, lineStartY), (lineEndX, lineEndY)])
    mid_pt = line.interpolate(0.5, normalized=True)
    result['x'] = mid_pt.x
    result['y'] = mid_pt.y
    return result


def percent_along_line(start_x, start_y, finish_x, finish_y, percentage):

    mid_x = start_x + (finish_x - start_x) * percentage / 100
    mid_y = start_y + (finish_y - start_y) * percentage / 100
    if (
            isinstance(start_x, int) and
            isinstance(start_y, int) and
            isinstance(finish_x, int) and
            isinstance(finish_y, int)):
        mid_x = round(mid_x)
        mid_y = round(mid_y)

    return mid_x, mid_y


def get_circle_from_world_points(x1, y1, t1, x2, y2, pragmatic=True, debug=False):

    # find the circle (x, y, radius) for which the 2 points are tangential
    # calculate arrival angle from path
    # if t1 ~= t2 i.e. driving straight, then the radius will be infinity
    # calculate the delta angle i.e. change in start and arrival angles, and the veer [left | right]

    # need to calculate the angle of arrival
    # from the path angle
    x = x1
    y = y1
    r = 0
    arrival_angle_norm = t1
    sector_angle = 0
    sector_portion = 0
    try:
        if debug:
            print('get_circle_from_world_points x1: {}m y1: {}m t1: {}deg x2: {}m y2: {}m'.format(
                x1,
                y1,
                degrees(t1),
                x2,
                y2)
            )
        path_angle = get_angle_between_cartesian_points(x1, y1, x2, y2)
        if path_angle is not None:
            if debug:
                print('get_circle_from_world_points path angle {0} degrees'.format(
                    degrees(path_angle)))
            path_distance = get_distance_between_points(x1, y1, x2, y2)
            if debug:
                print('get_circle_from_world_points path distance {0}'.format(
                    round(path_distance, 2)))
            arrival_angle = (2 * path_angle) - t1
            arrival_angle_norm = (
                2 * pi) + arrival_angle if arrival_angle < 0 else arrival_angle
            if debug:
                print('get_circle_from_world_points arrival angle {0} normalised {1} degrees'.format(
                    degrees(arrival_angle), degrees(arrival_angle_norm)))
            x, y, r = get_circle_from_world_tangents(
                x1, y1, t1, x2, y2, arrival_angle_norm)
            if r is not None:
                if debug:
                    print('get_circle_from_world_points radius: {:.3f}'.format(r))
                try:
                    sector_angle = acos(
                        1 - (path_distance ** 2 / (2 * r ** 2)))
                except Exception as e:
                    print('Error in get_circle_from_world_points sector angle formula: {0} path_distance={1} r={2}'.format(
                        e, path_distance, r))
                sector_portion = sector_angle / (2 * pi)
                if debug:
                    print('get_circle_from_world_points sector portion: {}'.format(
                        sector_portion)
                        )

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        print('Error in get_circle_from_world_points: ' +
              str(e) + ' on line ' + str(err_line))
    if pragmatic:
        return (
            round(x, 3) if x is not None else -1,
            round(y, 3) if y is not None else -1,
            round(r, 3) if r is not None else -1,
            round(arrival_angle_norm, 3) if arrival_angle_norm is not None else 0,
            round(sector_angle, 3) if sector_angle is not None else 0,
            # sector portion for near infinitely large circles will be very small, so don't round
            sector_portion if sector_portion is not None else 0
        )
    else:
        return x, y, r, arrival_angle_norm, sector_angle, sector_portion


def get_circle_from_world_tangents(x1, y1, t1, x2, y2, t2):

    # find the circle (x, y, radius) for which the 2 points are tangential
    # if t1 ~= t2 i.e. driving straight, then the radius will be very large approaching infinity
    intersection = {}
    intersection['x'] = None
    intersection['y'] = None
    r = None

    try:

        # find the equations of lines perpendicular to the poses

        t1p = t1 + (pi / 2)
        x1b = x1 + sin(t1p)
        y1b = y1 - cos(t1p)

        t2p = t2 + (pi / 2)
        x2b = x2 + sin(t2p)
        y2b = y2 - cos(t2p)

        intersection = checkLineIntersection(
            x1, y1, x1b, y1b, x2, y2, x2b, y2b)

        # finally calculate radius from pythag
        r = sqrt((intersection['x'] - x1) ** 2 + (intersection['y'] - y1) ** 2)

    except Exception as e:
        print('Error calculating circle from tangents: ' + str(e))

    return intersection['x'], intersection['y'], r


def make_equilateral_triangle(r, theta=0, offset=(0, 0)):
    res = []
    try:
        angles = [0, 2 * pi / 3, 4 * pi / 3]
        res = [((-sin(a + theta) * r) + offset[0],
                (-cos(a + theta) * r) + offset[1]) for a in angles]
    except Exception:
        pass
    return res


def get_arrow_from_pose(cx, cy, t, length):
    # get start and end points of an arrow representing pose
    arr_radius = length / 2
    x_offset = sin(t) * arr_radius
    y_offset = cos(t) * arr_radius
    return cx + x_offset, cy - y_offset, cx - x_offset, cy + y_offset


def annot_arrow(draw_on, tail_x_px, tail_y_px, tip_x_px, tip_y_px, fill, outline, k=4):
    # split line into k segments, and shorten line by 1 segment in from each end
    start_x_px, start_y_px, end_x_px, end_y_px = get_shortened_line(
        tail_x_px, tail_y_px, tip_x_px, tip_y_px, k)
    # use get_angle_between_points because we are working in image pixels!
    arrow_rad = get_angle_between_points(
        tail_x_px, tail_y_px, tip_x_px, tip_y_px)
    vertices = make_equilateral_triangle(
        4, arrow_rad, offset=(end_x_px, end_y_px))
    draw_on.line((end_x_px, end_y_px, start_x_px,
                 start_y_px), fill=fill, width=4)
    if len(vertices) > 0:
        draw_on.polygon(vertices, fill=fill, outline=outline)


def annot_axle(draw_on, left_cotter_x_px, left_cotter_y_px, right_cotter_x_px, right_cotter_y_px, fill):
    draw_on.line((left_cotter_x_px, left_cotter_y_px,
                 right_cotter_x_px, right_cotter_y_px), fill=fill, width=2)


def get_end_point_of_shortened_line(start_x, start_y, finish_x, finish_y, k):
    # split line into k segments, shorten line by 1 segment, return new end
    new_end_x, new_end_y = (finish_x - ((1 / k) * (finish_x - start_x))
                            ), finish_y - ((1 / k) * (finish_y - start_y))
    return new_end_x, new_end_y


def get_shortened_line(start_x, start_y, finish_x, finish_y, k=10):
    # split line into k segments, and shorten line by 1 segment in from each end
    new_start_x, new_start_y = get_end_point_of_shortened_line(
        finish_x, finish_y, start_x, start_y, k)
    new_end_x, new_end_y = get_end_point_of_shortened_line(
        start_x, start_y, finish_x, finish_y, k)
    return new_start_x, new_start_y, new_end_x, new_end_y


def get_point_adistance_along_line(start_x, start_y, finish_x, finish_y, d):
    # using similar triangles
    try:
        x_length = finish_x - start_x
        y_length = finish_y - start_y
        if x_length == 0 and y_length == 0:
            new_x = start_x
            new_y = start_y
        else:
            line_length = np.hypot(x_length, y_length)
            ratio = d / line_length
            new_x = start_x + (x_length * ratio)
            new_y = start_y + (y_length * ratio)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        print('d:', d, 'line_length:', line_length)
        print('Error in get_point_adistance_along_line: ' +
              str(e) + ' on line ' + str(err_line))
    return new_x, new_y


def get_evenly_spaced_points_on_line(x1, y1, x2, y2, min_d):
    '''
        split line (x1, y1) ------------- (x2, y2)
        into (x1, y1) --- (x11, y11) --- (x22, y22) --- (x2, y2)
                |   <- d ->   |   <- d ->   |   <- d ->   |
        such that dist d < min_d
    '''
    hypot = np.hypot((x2 - x1), (y2 - y1))
    num_pts = ceil(hypot / min_d)
    points = []
    for i in range(1, num_pts):
        a = float(i) / num_pts  # rescale 0 < i < n --> 0 < a < 1
        x = (1 - a) * x1 + a * x2  # interpolate x coordinate
        y = (1 - a) * y1 + a * y2  # interpolate y coordinate
        points.append((x, y))
    return points


def triangle_isoscelicity(arr, ia, ib, ic, tir):
    '''
        calculates the isoscelicty factor of a triangle given its vertex indices and target isos ratio (tir)
        f = (1 - (abs(shortest-side / longest-side - tir) / tir)) * (middle-side / longest-side)
    '''
    p1 = arr[ia]
    p2 = arr[ib]
    p3 = arr[ic]
    s1 = np.hypot(p2[0] - p1[0], p2[1] - p1[1])
    s2 = np.hypot(p3[0] - p2[0], p3[1] - p2[1])
    s3 = np.hypot(p1[0] - p3[0], p1[1] - p3[1])
    sides = [s1, s2, s3]
    sorted_sides = sorted(sides)
    shortest, middle, longest = sorted_sides
    f1 = 1 - abs(((shortest / longest) - tir) / tir)
    f2 = middle / longest
    f = f1 * f2
    return f


def triangle_area(p1, p2, p3):
    """
    calculates the area of a triangle given its vertices
    """
    return abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])) / 2.


def line_intersect(a_starts, a_finishes, b_starts, b_finishes):
    T = np.array([[0, -1], [1, 0]])
    da = np.atleast_2d(a_finishes - a_starts)
    db = np.atleast_2d(b_finishes - b_starts)
    dp = np.atleast_2d(a_starts - b_starts)
    dap = np.dot(da, T)
    denom = np.sum(dap * db, axis=1)
    num = np.sum(dap * dp, axis=1)
    result = np.atleast_2d(np.divide(num, denom, out=np.full_like(
        num, np.nan), where=denom != 0)).T * db + b_starts
    return result  # * parallels[:, None]


def closest_point_on_line(x1, y1, x2, y2, x, y):
    dx, dy = x2 - x1, y2 - y1
    det = dx * dx + dy * dy
    a = (dy * (y - y1) + dx * (x - x1)) / det
    return x1 + a * dx, y1 + a * dy


def distance_to_line(x, y, x1, y1, x2, y2):
    '''
        find the perpendicular distance from (x, y) to line (x1, y1)..(x2, y2)
    '''
    d = 0
    try:
        line_length = np.hypot(x2 - x1, y2 - y1)
        if line_length > 0:
            d = (((x2 - x1) * (y - y1)) - ((x - x1) * (y2 - y1))) / line_length
    except Exception:
        pass
    return d


def line_circle_intersection(x, y, x1, y1, x2, y2, look_ahead_distance, pragmatic=True, debug=False, logger=None):

    # helper function: sgn(num)
    # returns -1 if num is negative, 1 otherwise
    def sgn(num):
        if num >= 0:
            return 1
        else:
            return -1

    # output stored in arrays sol1 and sol2 in the form of sol1 = [sol1_x, sol1_y]
    sol = None

    try:
        incoming = [x, y, x1, y1, x2, y2]
        msg = 'line circle intersection incoming: {}'.format(
            [None if elem is None else round(elem, 3) for elem in incoming])
        if debug:
            if logger:
                logger.debug(msg)
            else:
                print(msg)

        # pragmatism
        if None in incoming:
            if pragmatic:
                if None not in [x1, y1, x2, y2]:
                    # no path to intersect
                    if x is not None and y is not None:
                        # just return current location - effectively look_ahead_distance = 0
                        sol = (x, y)
                    else:
                        # unable to compute any sensible point
                        sol = (0, 0)
                elif x2 is not None and y2 is not None:
                    sol = (x2, y2)
                elif x1 is not None and y1 is not None:
                    sol = (x1, y1)

        elif x1 == x2 and y1 == y2:
            # zero length line so can't find intersection
            sol = (x1, y1)
        else:
            # subtract currentX and currentY from [x1, y1] and [x2, y2] to offset the system to origin
            x1_offset = x1 - x
            y1_offset = y1 - y
            x2_offset = x2 - x
            y2_offset = y2 - y

            # calculate the discriminant
            dx = x2_offset - x1_offset
            dy = y2_offset - y1_offset
            dr = sqrt(dx ** 2 + dy ** 2)
            D = x1_offset * y2_offset - x2_offset * y1_offset  # determinant
            discriminant = (look_ahead_distance ** 2) * (dr ** 2) - D ** 2

            # pragmatic solution is closest point on line if no solution exists
            if pragmatic:
                sol = closest_point_on_line(x1, y1, x2, y2, x, y)
                msg = 'line circle intersection fallback solution ({:.2f}, {:.2f})'.format(
                    *sol)
            else:
                sol = None
                msg = 'line circle intersection fallback solution None'
            if debug:
                if logger:
                    logger.debug(msg)
                else:
                    print(msg)

            # if discriminant is >= 0, there exist solutions
            if discriminant >= 0:

                # calculate the solutions
                sol_x1 = (D * dy + sgn(dy) * dx *
                          np.sqrt(discriminant)) / dr ** 2
                sol_x2 = (D * dy - sgn(dy) * dx *
                          np.sqrt(discriminant)) / dr ** 2
                sol_y1 = (-D * dx + abs(dy) * np.sqrt(discriminant)) / dr ** 2
                sol_y2 = (-D * dx - abs(dy) * np.sqrt(discriminant)) / dr ** 2

                # add currentX and currentY back to the solutions, offset the system back to its original position
                sol1 = [sol_x1 + x, sol_y1 + y]
                sol2 = [sol_x2 + x, sol_y2 + y]
                msg = 'line circle intersection solution 1 ({:.2f}, {:.2f}) solution 2 ({:.2f}, {:.2f})'.format(
                    *sol1, *sol2)
                if debug:
                    if logger:
                        logger.debug(msg)
                    else:
                        print(msg)

                # check to see which of the two solution points is nearest target
                sol1_tgt_dist = np.hypot(x2 - sol1[0], y2 - sol1[1])
                sol2_tgt_dist = np.hypot(x2 - sol2[0], y2 - sol2[1])
                if (sol1_tgt_dist < sol2_tgt_dist):
                    msg = 'line circle intersection solution 1 ({:.2f}, {:.2f}) is closest to ({:.2f}, {:.2f})'.format(
                        *sol1, x2, y2)
                    sol = sol1
                else:
                    msg = 'line circle intersection solution 2 ({:.2f}, {:.2f}) is closest to ({:.2f}, {:.2f})'.format(
                        *sol2, x2, y2)
                    sol = sol2
                if debug:
                    if logger:
                        logger.debug(msg)
                    else:
                        print(msg)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error processing line circle intersection: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger is not None:
            logger.error(msg)
        else:
            print(msg)

    return (round(sol[0], 3), round(sol[1], 3)) if pragmatic else sol


def get_velocity_ratio(axle_track_m, turn_circle_radius, sector_portion, pragmatic=True, debug=False, logger=None):

    turn_circle_circumference = 2 * pi * turn_circle_radius
    outer_tyre_radius = turn_circle_radius + (axle_track_m / 2)
    inner_tyre_radius = turn_circle_radius - (axle_track_m / 2)
    msg = 'outer_tyre_radius: ' + \
        str(round(outer_tyre_radius, 2)) + ' inner_tyre_radius: ' + \
        str(round(inner_tyre_radius, 2))
    if debug and logger:
        logger.info(msg)
    outer_tyre_circumference = 2 * pi * outer_tyre_radius
    inner_tyre_circumference = 2 * pi * inner_tyre_radius
    msg = 'outer_tyre_circumference: ' + \
        str(round(outer_tyre_circumference, 2)) + \
        ' inner_tyre_circumference: ' + str(round(inner_tyre_circumference, 2))
    if debug and logger:
        logger.info(msg)
    arc_length = turn_circle_circumference * sector_portion
    outer_tyre_distance = outer_tyre_circumference * sector_portion
    inner_tyre_distance = inner_tyre_circumference * sector_portion
    msg = 'outer_tyre_distance: ' + str(round(outer_tyre_distance, 2)) + ' arc_length: ' + str(
        round(arc_length, 2)) + ' inner_tyre_distance: ' + str(round(inner_tyre_distance, 2))
    if debug and logger:
        logger.info(msg)

    if outer_tyre_distance > 0:
        velocity_ratio = inner_tyre_distance / outer_tyre_distance
    else:
        velocity_ratio = 1
    msg = 'velocity_ratio: ' + str(round(velocity_ratio, 2))
    if debug and logger:
        logger.info(msg)

    if pragmatic:
        return round(velocity_ratio, 3), round(arc_length, 3)
    else:
        return velocity_ratio, arc_length

def is_left_of_line(x1, y1, x2, y2, x, y):
    # Given a line (x1, y1)--(x2, y2) and point (x, y)
    # return True if point is on left of line
    return (x2 - x1)*(y - y1) - (y2 - y1)*(x - x1) > 0

def same_side_of_line(x1, y1, x2, y2, ax, ay, bx, by):
    # Given a line (x1, y1)--(x2, y2) and 2 points (ax, ay) (bx, by)
    # return True if points on same side of line
    return not(is_left_of_line(x1, y1, x2, y2, ax, ay) ^ is_left_of_line(x1, y1, x2, y2, bx, by))