import time
import sys
import os
import psutil
from datetime import datetime
import numpy as np
import socket
import json
import logging
import math
import threading
from types import ModuleType, FunctionType
from gc import get_referents

from destination import Attitude

np.seterr(all='raise')

RSSI_THRESHOLDS = [0, -30, -67, -70, -80, -90, -999]
RSSI_CATEGORIES = ['Unbelievable', 'Amazing',
                   'Very Good', 'O.K.', 'Not Good', 'Unusable']

LOCATION_CSV_HEADER = 'date/time, ssid, mssid, rid, x1[m], y1[m], x2[m], y2[m], x[m], y[m],'\
                        ' theta[degrees], progress[%], span[m], cutter stray[%],'\
                        ' battery[%], loaded[%], confidence[%], essid, rssi'

despatch_lock = threading.Lock()

def trace_rules(msg):
    logger = logging.getLogger('navigation')
    logger.info(msg)


def trace_location(msg):
    logger = logging.getLogger('excursion')
    logger.info(msg)


def trace_command(msg):
    logger = logging.getLogger('last-cmds')
    logger.info(msg)


def make_contour_entry(
        cont_img_arr,
        cont_thr_arr,
        contour,
        ssid,
        i,
        viewport,
        resolution,
        incl_fullsize=False
):

    # assemble message into a single line entry - so it stays together
    msg = '{0}, {1}, {2}, {3}, {4}|'.format(
        datetime.now().isoformat(),
        ssid,
        i,
        '{1:.0f}x{0:.0f}'.format(
            *np.rint(np.array(viewport.origin) * resolution / 100)),
        '{1}x{0}'.format(*resolution)
    )
    if (viewport is not None and not viewport.isnull) or incl_fullsize:
        if cont_img_arr is not None:
            msg += str(cont_img_arr.tolist())
        else:
            msg += '[]'
        msg += '|'
        if cont_thr_arr is not None:
            msg += str((cont_thr_arr * 255).astype(np.uint8).tolist())
        else:
            msg += '[]'
        msg += '|'
    else:
        msg += '[]|[]|'
    msg += str(np.round(contour, 6).tolist())
    return msg


def route_pc_to_metres(arena_width_m, arena_length_m, route_pc, min_internode_dist_m=0.1, debug=False):
    patt_logger = logging.getLogger('mow-patterns')
    j = 0
    route_m = []
    inter_node_dist = min_internode_dist_m
    for i in range(len(route_pc)):
        x_pc = route_pc[i][0]
        y_pc = route_pc[i][1]
        att = route_pc[i][2] if len(route_pc[i]) > 2 else Attitude.DEFAULT
        if debug:
            patt_logger.debug('{}: ({:.2f}%, {:.2f}%)'.format(i, x_pc, y_pc))
        if x_pc is not None and y_pc is not None:
            x_m = round(x_pc * arena_width_m / 100, 3)
            y_m = round(y_pc * arena_length_m / 100, 3)
            if debug:
                patt_logger.debug('{}: ({:.2f}m, {:.2f}m)'.format(i, x_m, y_m))
            if j > 0:
                # beyond first so we can calculate distance between points
                inter_node_dist = np.hypot(
                    x_m - route_m[j - 1][0], y_m - route_m[j - 1][1])
                if debug:
                    patt_logger.debug(
                        'i: {0} j: {1} inter node distance: {2}'.format(i, j, inter_node_dist))
            if inter_node_dist >= min_internode_dist_m:
                route_m.append((x_m, y_m, att))
                patt_logger.debug('including node ({:.2f}m, {:.2f}m) whose inter-node-distance: {:.3f} >= {:.3f}'.format(
                    x_m,
                    y_m,
                    inter_node_dist,
                    min_internode_dist_m
                )
                )
                j += 1
            else:
                patt_logger.warning('skipping node ({:.2f}m, {:.2f}m) whose inter-node-distance: {:.3f} < {:.3f}'.format(
                    x_m,
                    y_m,
                    inter_node_dist,
                    min_internode_dist_m
                )
                )
    return route_m


def get_mem_usage():
    process = psutil.Process()
    '''
         aka Resident Set Size,
         this is the non-swapped physical memory a process has used.
         On UNIX it matches top RES column).
         On Windows this is an alias for wset field and it matches Mem Usage column of taskmgr.exe.
    '''
    memory_usage = process.memory_info().rss / 1E6
    memory_avail = psutil.virtual_memory().available / 1E6
    return memory_usage, memory_avail


def get_mem_stats():
    memory_usage, memory_avail = get_mem_usage()
    mem_stats = (' Mem Used: {0:.1f} MB Available: {1:.1f} MB'.format(
        memory_usage, memory_avail))
    return mem_stats


def get_safe_functions():
    # Math functions
    safe_list = ['factorial', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp',
                 'fabs', 'floor', 'fmod', 'hypot', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh']
    safe_dict = dict((k, getattr(math, k)) for k in safe_list)
    return safe_dict


def await_elapsed(start_time, finish_time):
    extra_delay_secs = finish_time - start_time
    if extra_delay_secs > 0:
        time.sleep(extra_delay_secs)
    return extra_delay_secs


def despatch_to_mower_udp(cmd, udp_socket, host, port, await_response=True, max_attempts=3):

    resp = None
    success = False
    attempt = 1
    logger = logging.getLogger('comms')
    sock_timeout = udp_socket.gettimeout()
    res = despatch_lock.acquire(timeout=sock_timeout + 1) # blocks
    if res:
        try:
            msg = 'mower comms lock acquired...'
            logger.debug(msg)
            while not success and attempt <= max_attempts and host is not None and port is not None:
                try:
                    logger.info('despatching - {0} to {1}:{2} within {3} secs'.format(
                        cmd, host, port, sock_timeout))
                    msg = bytes(cmd + '\r\n', 'utf8')
                    start = time.time()
                    bytes_sent = udp_socket.sendto(msg, (host, port))
                    if await_response:
                        data, addr = udp_socket.recvfrom(1024)
                        rtt_secs = time.time() - start
                        logger.info('sent - ' + str(bytes_sent) +
                                    ' bytes, awaiting response...')
                        if data:
                            resp = str(data, 'utf8')
                            logger.info('{0} => {1} from {2} in {3} secs'.format(
                                cmd, resp, addr, round(rtt_secs, 3)))
                            success = True
                        else:
                            logger.info('No data response received from: ' + cmd)
                    else:
                        success = True
        
                except socket.timeout as err:
                    msg = 'mower comms timeout: ' + \
                        str(err) + ' attempt: ' + str(attempt)
                    logger.warning(msg)
                    attempt += 1
                except socket.error as err:
                    err_line = sys.exc_info()[-1].tb_lineno
                    logger.error('mower socket error: ' + str(err) +
                                 ' on line ' + str(err_line))
                    break
                except Exception as err:
                    err_line = sys.exc_info()[-1].tb_lineno
                    msg = 'mower error: ' + str(err) + ' on line: ' + str(err_line)
                    logger.error(msg)
                    break
        finally:
            despatch_lock.release()
            msg = 'mower comms lock released'
            logger.debug(msg)
    else:
        # lock timeout - shouldn't happen!
        msg = 'mower comms lock timeout'
        logger.warning(msg)

    return resp


def rssi_category(rssi):
    try:
        rssi_index = next(i for i in range(len(RSSI_THRESHOLDS) - 1)
                          if RSSI_THRESHOLDS[i] >= rssi >= RSSI_THRESHOLDS[i + 1])
        cat = RSSI_CATEGORIES[rssi_index]
    except Exception:
        cat = RSSI_CATEGORIES[-1]
    return cat


def fetch_telemetry(config, udp_socket):

    try:
        logger = logging.getLogger('comms')
        telem = {}
        mower_host = config['mower.ip'] if 'mower.ip' in config else None
        mower_port = config['mower.port'] if 'mower.port' in config else None
        if mower_host is not None and mower_port is not None:
            cmd = ">get_telemetry()"
            # capture timeout so it can be restored
            def_timeout = udp_socket.gettimeout()
            udp_socket.settimeout(2)
            telem_json = despatch_to_mower_udp(
                cmd, udp_socket, mower_host, mower_port, max_attempts=1)
            udp_socket.settimeout(def_timeout)
            logger.debug(
                'telemetry json: {}'.format(telem_json))
            if telem_json is not None and telem_json != '':
                try:
                    telem = json.loads(telem_json)
                    # analogue sensors
                    # unpack raw values and match to names/factors if available
                    channel_names = config['mower.sens_name_list'].split(',')
                    channel_factors = config['mower.sens_factor_list'].split(',')
                    sensors = {}
                    for i, raw_adc in enumerate(telem['analogs']):
                        try:
                            ch_name = channel_names[i].strip()
                            if ch_name == '':
                                raise Exception()
                        except:
                            ch_name = f'Channel {i+1}'
                        try:
                            ch_factor = channel_factors[i]
                            if ch_factor.strip() == '':
                                raise Exception()
                        except:
                            ch_factor = 1.0
                        sensors[ch_name] = round(raw_adc * float(ch_factor), 3)
                        
                    telem['sensors'] = sensors
                    wifi_rssi = telem['rssi']  # dbm
                    if wifi_rssi is not None:
                        wifi_quality = rssi_category(wifi_rssi)
                        telem['wifi_quality'] = wifi_quality
                    # add last-fetch time here...
                    telem['last-fetch'] = time.time()
                except Exception as e1:
                    err_line = sys.exc_info()[-1].tb_lineno
                    logger.error('Error in fetch telemetry Json decoding: [{0}] {1}'.format(
                        telem_json, e1) + ' on line ' + str(err_line))
                    telem['wifi_quality'] = 0
            else:
                pass
                logger.warn('utilities fetch_telemetry - Mower Offline!')
        else:
            pass
            # logger.warn('utilities fetch_telemetry - No host:port!')

    except Exception as e2:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in fetch telemetry: ' +
                     str(e2) + ' on line ' + str(err_line))

    return telem

def fetch_pose(config, udp_socket):

    try:
        logger = logging.getLogger('comms')
        pose = None
        mower_host = config['mower.ip'] if 'mower.ip' in config else None
        mower_port = config['mower.port'] if 'mower.port' in config else None
        if mower_host is not None and mower_port is not None:
            cmd = ">get_pose()"
            pose_str = despatch_to_mower_udp(
                cmd, udp_socket, mower_host, mower_port, max_attempts=1)
            logger.debug('fetch_pose - {0}'.format(pose_str))
            if pose_str is not None and pose_str != '':
                pose = [float(v) for v in pose_str.split(',')]
            else:
                logger.warn('utilities fetch_pose - Mower Offline!')

    except Exception as e2:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in fetch pose: ' + str(e2) +
                     ' on line ' + str(err_line))

    return pose


def tail(f, lines=1, _buffer=4098):
    '''
        Tail a file and get X lines from the end
    '''
    # place holder for the lines found
    lines_found = []

    # block counter multiplied by buffer to get the block size from the end
    block_counter = -1

    # loop until we find X lines
    while len(lines_found) < lines:
        try:
            f.seek(block_counter * _buffer, os.SEEK_END)
        except IOError:  # file is too small, or too many lines requested
            f.seek(0)
            lines_found = f.readlines()
            break

        lines_found = f.readlines()

        # decrement the block counter to get the next X bytes
        block_counter -= 1

    return ''.join(lines_found[:-lines:-1])

def getsize(obj):
    """sum size of object & members."""
    BLACKLIST = type, ModuleType, FunctionType
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size