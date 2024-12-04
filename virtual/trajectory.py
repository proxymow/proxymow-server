from math import degrees, sin, cos, pi
from virtual.vlogs import trace_virtual

def calc_new_pose(x_0, y_0, theta_0, speed_left_percent, speed_right_percent, duration_ms, axle_track_m, velocity_full_speed_mps, debug=False):

    # duration in seconds
    duration_s = duration_ms / 1000

    # scale speeds into velocities
    v_left = velocity_full_speed_mps * speed_left_percent / \
        100  # scale percentage to fraction
    v_right = velocity_full_speed_mps * speed_right_percent / 100
    theta_0_deg = degrees(theta_0)
    msg = 'Start at: (' + str(x_0) + ', ' + str(y_0) + ') ' + str(theta_0_deg)
    if debug:
        trace_virtual(msg)

    if abs(speed_left_percent - speed_right_percent) < 1.0e-6:  # basically going straight
        x_delta_m = duration_s * sin(theta_0) * v_left
        # going straight with same speed
        y_delta_m = duration_s * -cos(theta_0) * v_left
        new_x_m = x_0 - x_delta_m
        new_y_m = y_0 - y_delta_m
        new_t_adj_rad = theta_0
        msg = 'Straight Angle [degrees]:' + \
            str(new_t_adj_rad) + ' => ' + str(round(degrees(new_t_adj_rad)))
        msg += '\nStraight Position: (' + str(new_x_m) + ', ' + str(
            new_y_m) + ') => (' + str(round(new_x_m, 2)) + ', ' + str(round(new_y_m, 2)) + ')'
        if debug:
            trace_virtual(msg)
    else:
        v_diff = v_right - v_left
        msg = 'v_diff: ' + str(round(v_diff, 2))
        if debug:
            trace_virtual(msg)
        v_sum = v_right + v_left
        msg = 'v_sum: ' + str(round(v_sum, 2))
        if debug:
            trace_virtual(msg)

        # clockwise or counter-clockwise?
        # if both wheels travel fwd, ccw is right going faster
        # if both wheels travel backward, ccw is left going faster
        # if left goes fwd and right backwards, clockwise
        # if right goes fwd and left backwards, ccw
        ccw = (v_left > 0 and v_right > 0 and v_right > v_left) or \
            (v_left < 0 and v_right < 0 and v_left > v_right) or \
            (v_right > 0 and v_left < 0)
        msg = 'Turn Motion Counter-Clockwise: ' + str(ccw)
        if debug:
            trace_virtual(msg)

        delta_t = v_diff * duration_s / axle_track_m
        delta_t_deg = degrees(delta_t)
        msg = 'delta_t: ' + str(delta_t_deg)
        if debug:
            trace_virtual(msg)
        turn_radius = abs((axle_track_m * v_sum) / (2 * v_diff))
        msg = 'turn_radius: ' + str(turn_radius)
        if debug:
            trace_virtual(msg)

        # turn circle centre
        # calculate the correct angle for perpendicular to centre
        angle_to_centre = (2 * pi) - theta_0  # rotation ccw
        if ccw:
            cx = x_0 + (turn_radius * cos(angle_to_centre + pi))
            cy = y_0 - (turn_radius * sin(angle_to_centre + pi))
        else:
            cx = x_0 + (turn_radius * cos(angle_to_centre))
            cy = y_0 - (turn_radius * sin(angle_to_centre))

        msg = 'turn circle centre: (' + str(round(cx, 2)) + \
            ', ' + str(round(cy, 2)) + ')'
        if debug:
            trace_virtual(msg)

        # sector angle
        if abs(v_left) != abs(v_right):
            # this doesn't work for negative velocities
            tyre_travel = max(v_left, v_right) * duration_s  # metres
            turn_circle_circumference = 2 * pi * turn_radius
            sector_portion = tyre_travel / turn_circle_circumference
            alpha_rad = 2 * pi * sector_portion * (-1 if ccw else 1)
            msg = 'sector_portion: ' + \
                str(round(sector_portion, 2)) + ' sector angle: ' + \
                str(round(degrees(alpha_rad)))
            if debug:
                trace_virtual(msg)
            # landing location point
            # local implementation of library function getRotatedPoint()

            x1_offset = x_0 - cx
            y1_offset = y_0 - cy
            cos_delta = cos(alpha_rad)
            sin_delta = sin(alpha_rad)
            delta_x = (x1_offset * cos_delta) + (y1_offset * sin_delta)
            delta_y = (x1_offset * sin_delta) - (y1_offset * cos_delta)

            new_x_m = cx + delta_x
            new_y_m = cy - delta_y
            new_t = theta_0 - alpha_rad
        else:
            delta_x = turn_radius * (sin(delta_t + theta_0) - sin(theta_0))
            delta_y = turn_radius * (cos(delta_t + theta_0) - cos(theta_0))
            new_x_m = x_0 + delta_x
            new_y_m = y_0 + delta_y  # would be y - delta in normal cartesian coordinates!
            new_t = theta_0 + delta_t

        if new_t < 0:
            new_t_adj_rad = (2 * pi) + new_t
        elif new_t >= (2 * pi):
            new_t_adj_rad = new_t - (2 * pi)
        else:
            new_t_adj_rad = new_t

    return new_x_m, new_y_m, new_t_adj_rad
