# WARNING - this file will be copied and minified for MicroPython!
# Ensure it does not contain multiline comments or multiline if debug statements

from math import pi, cos, sin, degrees


def get_turn_circle_from_relative_velocities(x1, y1, t1, v_left, v_right, axle_track_m, ccw_min_vdiff=1.0e-5, debug=False, logger=None):
    # calculate turn circle from relative velocities
    if debug and logger:
        logger.debug('get_turn_circle_from_relative_velocities v_left: {0:.3f}, v_right: {1:.3f}, axle_track_m: {2}'.format(
            v_left, v_right, axle_track_m))
    cx = x1
    cy = y1
    turn_radius = 0
    ccw = True
    try:
        if v_left is not None and v_right is not None:
            # we can't let v_left == v_right otherwise we have an infinite turn circle radius!
            if v_left == v_right:
                if v_left < 0:
                    v_left += ccw_min_vdiff
                else:
                    v_right -= ccw_min_vdiff
            if debug and logger:
                logger.debug(
                    'adjusted left: {:.3f} adjusted right: {:.3f}'.format(v_left, v_right))
            reverse = v_left <= 0 and v_right <= 0
            if debug and logger:
                logger.debug('straight: {} forward: {} reverse: {}'.format(
                    v_left == v_right, v_left > 0 and v_right > 0, reverse))
            # find the turn circle
            v_diff = v_right - v_left
            v_sum = v_right + v_left
            ccw = (v_left < v_right)
            if debug and logger:
                logger.debug('v_diff: {} v_sum: {} ccw: {}'.format(
                    v_diff, v_sum, ccw))
            if v_right == 0 and v_left != 0:
                # rotation about right wheel
                if debug and logger:
                    logger.debug('R1W-Right')
                turn_radius = axle_track_m
                offset_turn_radius = axle_track_m / \
                    (-2 if ccw ^ reverse else 2)
                if debug and logger:
                    logger.debug('one speed zero - rotation about wheel')
            elif v_left == 0 and v_right != 0:
                # rotation about left wheel
                if debug and logger:
                    logger.debug('R1W-Left')
                turn_radius = axle_track_m
                offset_turn_radius = axle_track_m / \
                    (2 if ccw ^ reverse else -2)
                if debug and logger:
                    logger.debug('one speed zero - rotation about wheel')
            elif v_left * v_right < 0:
                # rotation about centre
                if debug and logger:
                    logger.debug('R2W')
                turn_radius = axle_track_m / 2
                offset_turn_radius = 0
                if debug and logger:
                    logger.debug('speeds opposite - rotation about centre')
            else:
                # drive straight
                if debug and logger:
                    logger.debug('Straight')
                turn_radius = abs((axle_track_m * v_sum) / (2 * v_diff))
                offset_turn_radius = turn_radius
            if debug and logger:
                logger.debug('turn_radius: {:.2f}'.format(turn_radius))

            # find turn circle centre
            dx = cos(t1) * offset_turn_radius
            dy = sin(t1) * offset_turn_radius
            if ccw ^ reverse:
                cx = x1 - dx
                cy = y1 - dy
            else:
                cx = x1 + dx
                cy = y1 + dy
            if debug and logger:
                logger.debug(
                    'turn circle centre: ({:.2f}, {:.2f})'.format(cx, cy))
    except Exception as e:
        msg = 'Error in get_turn_circle_from_relative_velocities: ' + str(e)
        if logger:
            logger.error(msg)
        else:
            print(msg)
    return (cx, cy), turn_radius, ccw


def get_turn_circle_sector_angle(turn_radius, dir_ccw, left_speed, right_speed, duration_s, debug=False, logger=None):
    alpha_rad = 0
    try:
        # sector angle
        if turn_radius > 0:
            tyre_travel = abs(max(left_speed, right_speed,
                              key=lambda x: abs(x))) * duration_s  # metres
            turn_circle_circumference = 2 * pi * turn_radius
            sector_portion = tyre_travel / turn_circle_circumference
            alpha_rad = 2 * pi * sector_portion * (1 if dir_ccw else -1)
            if debug and logger:
                logger.debug('sector_portion: {:.2f} sector angle: {:.0f}'.format(
                    sector_portion, degrees(alpha_rad)))
    except Exception as e:
        msg = 'Error in get_turn_circle_sector_angle: ' + str(e)
        if logger:
            logger.error(msg)
        else:
            print(msg)
    return alpha_rad


def calc_new_pose(x_0, y_0, theta_0, speed_left_percent, speed_right_percent, duration_ms, axle_track_m, velocity_full_speed_mps, debug=False, logger=None):
    new_x_m = None
    new_y_m = None
    new_t_adj_rad = None
    try:
        # duration in seconds
        duration_s = duration_ms / 1000
        # scale speeds into velocities
        v_left = velocity_full_speed_mps * speed_left_percent / \
            100  # scale percentage to fraction
        v_right = velocity_full_speed_mps * speed_right_percent / 100
        (cx, cy), turn_radius, ccw = get_turn_circle_from_relative_velocities(
            x_0, y_0, theta_0, v_left, v_right, axle_track_m)
        alpha_rad = get_turn_circle_sector_angle(
            turn_radius, ccw, v_left, v_right, duration_s)
        # landing location point
        new_x_m, new_y_m = getPointRotatedCounterClockwise(
            x_0, y_0, alpha_rad, cx, cy)
        new_t_adj_rad = sum_angles(theta_0, alpha_rad)
    except Exception as e:
        msg = 'Error in calc_new_pose: ' + str(e)
        if logger:
            logger.error(msg)
        else:
            print(msg)
    return new_x_m, new_y_m, round(new_t_adj_rad, 4)


def getPointRotatedCounterClockwise(x, y, t, cx, cy):
    x1_offset = x - cx
    y1_offset = y - cy
    cos_delta = cos(-t)
    sin_delta = sin(-t)
    delta_x = (x1_offset * cos_delta) + (y1_offset * sin_delta)
    delta_y = (x1_offset * sin_delta) - (y1_offset * cos_delta)
    new_x = cx + delta_x
    new_y = cy - delta_y
    return new_x, new_y


def sum_angles(t1_rad, t2_rad):
    t_sum = (t1_rad + t2_rad) % (2 * pi)
    if t_sum < 0:
        t_sum += (2 * pi)
    return t_sum
