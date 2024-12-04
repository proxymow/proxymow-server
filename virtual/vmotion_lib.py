import time
import threading
import random
import virtual.vmachine as vmachine
from time import sleep
from math import radians, degrees, floor
from virtual.shared_utils import calc_new_pose
from virtual.vlogs import trace_virtual

start_time = time.time()

# define IO Mapping
# name             board label
left_in1 = 0  # D3
left_in2 = 2  # D4
right_in1 = 15  # D8
right_in2 = 12  # D6
cutter1 = 1  # TX
cutter2 = 3  # TX2

PWM_FREQ = 1024
ADC_ENABLED = True  # True for random values, False for discharging
MIN_STEP_DUR_MS = 250
REALISM_ENABLED = False  # Random Realism True | False
PSEUDO_REALISM_ENABLED = False  # Repeatable Realism True | False
PSEUDO_RAND_SEQ = [0, 5, 0, 4, 0, 3, 0, 2]
MAX_RAND_CYCLES = 4
pseudo_rand_index = 0
num_rand_cycles = MAX_RAND_CYCLES
random_occurrence = -1
ROTATE_BLOCKED_REALISM = False  # randomly prevent rotation
MIN_SPEED_TO_MOVE_PC = 35  # 20, use 80 to test escalation
MIN_DURATION_TO_MOVE_MS = 0  # 100
LOAD_FACTOR = 0.85  # use 1.0 to disable
BLOCKAGE_DURATION_SECS = 10
left_pwm = None
right_pwm = None
adc = None

act_timer = None
last_cmd = -1
left_speed_delta = 0
right_speed_delta = 0
relative_duration_ms = 0
axle_track_m = tyre_velocity_mps = 0
mower_xm = mower_ym = mower_t_rad = 0

overrun_speed_factor = 1.25
underrun_speed_factor = 0.75
rotation_blocked = False
blockage_occured_at = -1


# simulate battery discharge
battery_charge = 512

# add pin names to outputs list
out_pin_names = ['left_in1', 'left_in2',
                 'right_in1', 'right_in2', 'cutter1', 'cutter2']
out_pin_numbers = [left_in1, left_in2, right_in1, right_in2, cutter1, cutter2]
out_pins = {}
cutter_state_bytes = b'\x00\x00'

# control functions


def init():
    global left_pwm, right_pwm
    global adc
    global act_timer
    # make all pins outputs
    for i in range(0, len(out_pin_names)):
        name = out_pin_names[i]
        num = out_pin_numbers[i]
        pin = vmachine.Pin(num, vmachine.Pin.OUT)
        out_pins[name] = pin

    left_pwm = vmachine.PWM(out_pins["left_in1"])
    left_pwm.freq(PWM_FREQ)
    right_pwm = vmachine.PWM(out_pins["right_in1"])
    right_pwm.freq(PWM_FREQ)

    adc = vmachine.ADC(0)

    # create timers
    act_timer = threading.Timer(0, None)  # sweep timer
    trace_virtual('timers created')

    # turn off cutters
    cutter(0, 0)
    cutter(1, 0)


def stop():
    # Emergency Stop
    cutter(0, -1)
    deactivate(None, [left_pwm, right_pwm])
    trace_virtual('Emergency Stop Activated!')
    
def set_priority_essid(_essid):
    # Enrol in hotspot - dummy
    return 0

def close():
    pass


def activate(pwms, speeds_percent, duration_ms, axle_track_m, velocity_full_speed_mps, debug=False):

    global mower_xm, mower_ym, mower_t_rad
    global left_speed_delta, right_speed_delta, relative_duration_ms
    global pseudo_rand_index, random_occurrence, num_rand_cycles

    trace_virtual(
        '--------------------------------------------------------------------------')

    global act_timer
    global battery_charge
    act_timer.cancel()
    trace_virtual('Activate Timer Cancelled')
    try:
        # here you block the main thread until the timer is completely stopped
        act_timer.join()
    except:
        pass
    trace_virtual('Activate Timer Joined Alive: {}'.format(
        act_timer.is_alive()))
    deactivate(None, [left_pwm, right_pwm])

    # reset relative deltas
    left_speed_delta = 0
    right_speed_delta = 0
    relative_duration_ms = 0

    if len(pwms) == 2:
        left_dir_fwd = out_pins["left_in1"].state < out_pins["left_in2"].state
        right_dir_fwd = out_pins["right_in1"].state < out_pins["right_in2"].state
        speed_left_percent = speeds_percent[0]
        speed_right_percent = speeds_percent[1]
    else:
        speed_left_percent = speeds_percent[0]
        speed_right_percent = speeds_percent[0]

    msg = 'activating left_dir_fwd: ' + str(left_dir_fwd) + ' right_dir_fwd: ' + str(right_dir_fwd) + ' speed_left_percent: ' + str(
        speed_left_percent) + ' speed_right_percent: ' + str(speed_right_percent) + ' duration: ' + str(duration_ms)
    trace_virtual(msg)

    mower_t_deg = degrees(mower_t_rad)
    msg = 'x[m]: {0} y[m]: {1} t[deg]: {2}'.format(
        mower_xm, mower_ym, mower_t_deg)
    trace_virtual(msg)

    # check battery - if its below 50% we're going nowhere!
    if battery_charge < 400:
        msg = 'Virtual Mower Battery Flat - no motion possible'
        trace_virtual(msg)
    else:

        # discharge the battery?
        if not ADC_ENABLED:
            battery_charge -= (duration_ms *
                               (speed_left_percent + speed_right_percent)) / 200000

        # post an initial position to satisfy AM
        initial_dur_ms = 0
        if initial_dur_ms > 0:
            _x_m, _y_m, _t_rad = partial_action(
                initial_dur_ms,
                axle_track_m,
                velocity_full_speed_mps,
                speed_left_percent,
                speed_right_percent,
                mower_xm,
                mower_ym,
                mower_t_rad,
                True
            )

        if ROTATE_BLOCKED_REALISM and (speed_left_percent ^ speed_right_percent) < 0:
            if rotation_blocked:
                # already blocked
                pass
            else:
                block_likely = likely(100)  # never
                if block_likely:
                    rotation_blocked = True
                    speed_left_percent = 0
                    speed_right_percent = 0
        else:
            # clear down
            rotation_blocked = False

        # load factor
        speed_left_percent *= LOAD_FACTOR
        speed_right_percent *= LOAD_FACTOR

        if REALISM_ENABLED or PSEUDO_REALISM_ENABLED:
            if REALISM_ENABLED:
                num_rand_cycles = -MAX_RAND_CYCLES
                random_occurrence = random.randint(
                    1, 14)  # full range is (1, 7)
            elif PSEUDO_REALISM_ENABLED:
                num_rand_cycles = MAX_RAND_CYCLES
                random_occurrence = PSEUDO_RAND_SEQ[pseudo_rand_index]
                pseudo_rand_index = (pseudo_rand_index +
                                     1) % len(PSEUDO_RAND_SEQ)

            msg = 'Activate Realism {}[{}] {} cycles Expected Movement Parameters: left_speed: {}% right_speed: {}% duration: {}ms full speed velocity: {:.2f}m/s'.format(
                random_occurrence,
                pseudo_rand_index,
                num_rand_cycles,
                speed_left_percent,
                speed_right_percent,
                duration_ms,
                velocity_full_speed_mps
            )
            if debug:
                trace_virtual('\t' + msg)

        # divide remaining duration into discrete steps
        rem_duration_ms = duration_ms - initial_dur_ms
        step_count = max(floor(rem_duration_ms / MIN_STEP_DUR_MS), 1)
        partial_dur_s = rem_duration_ms / (1000 * step_count)
        msg = 'activate step_count {0} partial_dur_s {1}'.format(
            step_count, partial_dur_s)
        trace_virtual(msg)

        trace_virtual('Activate Timer Starting... {} {} {}'.format(
            speed_left_percent, speed_right_percent, partial_dur_s*1000))

        act_timer = threading.Timer(
            partial_dur_s,
            task,
            args=(
                step_count,
                partial_dur_s,
                axle_track_m,
                velocity_full_speed_mps,
                speed_left_percent,
                speed_right_percent,
                mower_xm,
                mower_ym,
                mower_t_rad
            )
        )
        act_timer.start()

    return get_telemetry()


def task(
        step_count,
        partial_dur_s,
        axle_track_m,
        velocity_full_speed_mps,
        speed_left_percent,
        speed_right_percent,
        x_m,
        y_m,
        t_rad
):

    global act_timer
    trace_virtual(
        'Task - Activate Timer Alive {}'.format(act_timer.is_alive()))

    x_m, y_m, t_rad = partial_action(
        partial_dur_s * 1000,
        axle_track_m,
        velocity_full_speed_mps,
        speed_left_percent,
        speed_right_percent,
        x_m,
        y_m,
        t_rad,
        True
    )

    step_count -= 1
    if step_count == 0:
        trace_virtual('Task Finished')
    else:
        if left_speed_delta != 0 and relative_duration_ms > 0:
            trace_virtual('Task Intermediate {0} ({1}+{2}%, {3}%)'.format(
                step_count, speed_left_percent, left_speed_delta, speed_right_percent))
        elif right_speed_delta != 0 and relative_duration_ms > 0:
            trace_virtual('Task Intermediate {0} ({1}%, {2}+{3}%)'.format(
                step_count, speed_left_percent, speed_right_percent, right_speed_delta))
        else:
            trace_virtual('Task Intermediate {0} ({1}%, {2}%)'.format(
                step_count, speed_left_percent, speed_right_percent))

        act_timer = threading.Timer(
            partial_dur_s,
            task,
            args=(
                step_count,
                partial_dur_s,
                axle_track_m,
                velocity_full_speed_mps,
                speed_left_percent,
                speed_right_percent,
                x_m,
                y_m,
                t_rad
            )
        )
        act_timer.start()


def deactivate(_t, pwms):
    # log('deactivating')
    for pwm in pwms:
        pwm.duty(0)


def partial_action(duration_ms, axle_track_m, velocity_full_speed_mps, speed_left_percent, speed_right_percent, x_m, y_m, t_rad, debug=False):
    global mower_xm, mower_ym, mower_t_rad
    global left_speed_delta, right_speed_delta, relative_duration_ms
    global random_occurrence, num_rand_cycles, pseudo_rand_index, blockage_occured_at

    do_action = True

    # relative deltas
    if relative_duration_ms > 0:
        speed_left_percent += left_speed_delta
        speed_right_percent += right_speed_delta
        relative_duration_ms -= MIN_STEP_DUR_MS
        if debug:
            trace_virtual('applied relative deltas: +{} => {}, +{} => {} relative dur: {}ms'.format(
                left_speed_delta,
                speed_left_percent,
                right_speed_delta,
                speed_right_percent,
                relative_duration_ms
            )
            )

    if (REALISM_ENABLED or PSEUDO_REALISM_ENABLED):
        if num_rand_cycles >= 0:
            num_rand_cycles -= 1
        else:
            if REALISM_ENABLED:
                # full range is (1, 7) (1, 50) is tame
                random_occurrence = random.randint(1, 14)
                num_rand_cycles = abs(num_rand_cycles)
            elif PSEUDO_REALISM_ENABLED:
                random_occurrence = PSEUDO_RAND_SEQ[pseudo_rand_index]
                pseudo_rand_index = (pseudo_rand_index +
                                     1) % len(PSEUDO_RAND_SEQ)

        msg = 'Partial Realism {}[{}] {} cycles Expected Movement Parameters: left_speed: {:.0f}% right_speed: {:.0f}% duration: {:.0f}ms full speed velocity: {:.2f}m/s'.format(
            random_occurrence,
            pseudo_rand_index,
            num_rand_cycles,
            speed_left_percent,
            speed_right_percent,
            duration_ms,
            velocity_full_speed_mps
        )
        if debug:
            trace_virtual('\t' + msg)

        if duration_ms < MIN_DURATION_TO_MOVE_MS:
            msg = '*** Realism - Duration below minimum, ignoring move'
            if debug:
                trace_virtual('\t' + msg)
            duration_ms = 0

        if abs(speed_left_percent) > 0 and abs(speed_left_percent) < MIN_SPEED_TO_MOVE_PC:
            msg = '*** Realism - Left Speed below minimum, setting both to zero'
            if debug:
                trace_virtual('\t' + msg)
            speed_left_percent = 0
            speed_right_percent = 0

        if abs(speed_right_percent) > 0 and abs(speed_right_percent) < MIN_SPEED_TO_MOVE_PC:
            msg = '*** Realism - Right Speed below minimum, setting both to zero'
            if debug:
                trace_virtual('\t' + msg)
            speed_left_percent = 0
            speed_right_percent = 0

        if random_occurrence == 2 and (speed_left_percent > 0 and speed_right_percent > 0):
            msg = '*** Realism - driving overrun (downhill), increasing full speed velocity'
            if debug:
                trace_virtual('\t' + msg)
            velocity_full_speed_mps *= overrun_speed_factor

        elif random_occurrence == 3 and (speed_left_percent > 0 and speed_right_percent > 0):
            msg = '*** Realism - driving underrun (uphill), decreasing full speed velocity'
            if debug:
                trace_virtual('\t' + msg)
            velocity_full_speed_mps /= overrun_speed_factor

        elif random_occurrence == 4 and speed_left_percent > 0:
            msg = '*** Realism - driving left wheel slip, decreasing left speed'
            if debug:
                trace_virtual('\t' + msg)
            speed_left_percent *= underrun_speed_factor

        elif random_occurrence == 5 and speed_right_percent > 0:
            msg = '*** Realism - driving right wheel slip, decreasing right speed'
            if debug:
                trace_virtual('\t' + msg)
            speed_right_percent *= underrun_speed_factor

        if blockage_occured_at > 0:
            # back moving?
            if (time.time() - blockage_occured_at) > BLOCKAGE_DURATION_SECS:
                msg = '*** Realism - blockage, zero both speeds cancelled'
                if debug:
                    trace_virtual('\t' + msg)
                blockage_occured_at = -1
            else:
                msg = '*** Realism - blockage, zero both speeds for extended period'
                if debug:
                    trace_virtual('\t' + msg)
                speed_right_percent = speed_left_percent = 0

        elif random_occurrence == 6:
            msg = '*** Realism - blockage, zero both speeds triggered'
            if debug:
                trace_virtual('\t' + msg)
            blockage_occured_at = time.time()

    if do_action:
        # calculate change in pose due to each wheel's speed and duration
        msg = 'Actual Movement Parameters: left_speed: {}% right_speed: {}% duration: {:.0f}ms full speed velocity: {:.2f}m/s'.format(
            speed_left_percent,
            speed_right_percent,
            duration_ms,
            velocity_full_speed_mps
        )
        if debug:
            trace_virtual('\t' + msg)

        new_x_m, new_y_m, new_theta_rad = calc_new_pose(
            x_m,
            y_m,
            t_rad,
            speed_left_percent,
            speed_right_percent,
            duration_ms,
            axle_track_m,
            velocity_full_speed_mps
            # debug
        )
        new_theta_deg = degrees(new_theta_rad)
        msg = 'Angle[degrees]:' + \
            str(round(degrees(t_rad), 2)) + ' => ' + str(round(new_theta_deg))
        if debug:
            trace_virtual('\t' + msg)
        msg = 'Position: (' + str(x_m) + ', ' + str(y_m) + ') => (' + \
            str(round(new_x_m, 2)) + ', ' + str(round(new_y_m, 2)) + ')'
        if debug:
            trace_virtual('\t' + msg)
        sleep_secs = 0
        msg = 'effectively sleeping for: ' + str(sleep_secs)
        if debug:
            trace_virtual('\t' + msg)

        sleep(sleep_secs)

        # write back and save pose
        msg = 'VMotion partial - setting virtual mower position x_m: ' + \
            str(round(new_x_m, 2)) + ' y_m: ' + str(round(new_y_m, 2)) + \
            ' theta: ' + str(round(new_theta_deg)) + ' degrees'
        if debug:
            trace_virtual('\t' + msg)
        mower_xm, mower_ym, mower_t_rad = new_x_m, new_y_m, new_theta_rad

        return new_x_m, new_y_m, new_theta_rad


def sweep(left_speed_in, right_speed_in, duration_in, last_cmd_in=-2):

    # all incoming parameters are floats
    global left_pwm, right_pwm, last_cmd
    global left_speed_delta, right_speed_delta, relative_duration_ms

    last_cmd = int(last_cmd_in)

    if duration_in < 0:
        # special relative in-flight command
        trace_virtual('sweep relative')
        left_speed_delta = left_speed_in
        right_speed_delta = right_speed_in
        relative_duration_ms = abs(duration_in)
    else:
        left_speed = float(left_speed_in)
        right_speed = float(right_speed_in)
        duration = duration_in

        # e.g. sweep(-100%..100%, -100%..100%, dur[secs])
        if left_speed >= 0:
            out_pins["left_in1"].value(0)
            out_pins["left_in2"].value(1)
        else:
            out_pins["left_in1"].value(1)
            out_pins["left_in2"].value(0)
        if right_speed >= 0:
            out_pins["right_in1"].value(0)
            out_pins["right_in2"].value(1)
        else:
            out_pins["right_in1"].value(1)
            out_pins["right_in2"].value(0)

        # and capture telemetry during loading
        activate([left_pwm, right_pwm], [left_speed, right_speed], int(
            duration), axle_track_m, tyre_velocity_mps, debug=True)

    return 4

def readadc(_):
    if ADC_ENABLED:
        analog = adc.read()
    else:
        analog = battery_charge
    return analog


def get_telemetry():
    # assemble string of telemetry values
    tmplt = '{{"analogs": {}, "cutter1": {}, "cutter2": {}, "ssid": "{}", "rssi": {}, "dist": {}, "free-mb": {}, "last-update": {}, "last-cmd": {}}}'
    batt = readadc(None)
    cutter_state = int.from_bytes(cutter_state_bytes, 'big') // 256

    return tmplt.format(
        [batt, batt - 10, -1],
        cutter_state & 1,
        (cutter_state & 2) >> 1,
        'vssid',
        -25,
        5,
        100,
        (time.time() - start_time) * 1000,
        last_cmd
    )

def cutter(addr_in, mode):
    '''
        addr may be a binary address (mode -1)
        or a channel index (modes 0 & 1) 
    '''
    global cutter_state_bytes
    trace_virtual('Cutter addr:{} mode:{} intmode:{} type:{}'.format(
        addr_in, mode, int(mode), type(mode)))
    cur_state = int.from_bytes(cutter_state_bytes, 'big') // 256
    addr = int(addr_in)
    mask = 2**addr
    if mode > 0.5:
        # independent channel set mode
        trace_virtual('Cutter {} ON'.format(addr + 1))
        addr = cur_state | mask
    elif mode >= 0.0:
        # independent channel clear mode
        trace_virtual('Cutter {} OFF'.format(addr + 1))
        addr = cur_state & ~mask

    addr_byte_array = (addr, 0)  # (address, timer)
    addr_bytes = bytes(addr_byte_array)
    try:
        trace_virtual('Cutter address bytes {} Writing...'.format(addr_bytes))
        cutter_state_bytes = addr_bytes
    except Exception:
        trace_virtual('Cutter address {} Write Failed'.format(addr))
    return 3

def get_pose():
    # assemble pose string
    return '{0},{1},{2}'.format(mower_xm, mower_ym, degrees(mower_t_rad))

def set_pose(xm_in, ym_in, thetadeg_in, axle_track_m_in=None, tyre_velocity_mps_in=None):
    global mower_xm, mower_ym, mower_t_rad, axle_track_m, tyre_velocity_mps
    global pseudo_rand_index
    # update pose
    if axle_track_m_in is not None:
        axle_track_m = axle_track_m_in
    if tyre_velocity_mps_in is not None:
        tyre_velocity_mps = tyre_velocity_mps_in
    mower_xm, mower_ym, mower_t_rad = xm_in, ym_in, radians(thetadeg_in)
    # reset pseudo random index
    pseudo_rand_index = 0
    return 0


def likely(likelihood_pc):
    return random.random() <= (likelihood_pc / 100)
