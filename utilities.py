import time
import sys
import os
import psutil
from datetime import datetime
import numpy as np
import logging
import math
from types import ModuleType, FunctionType
from gc import get_referents
from destination import Attitude
from ping3 import ping

np.seterr(all='raise')

LOCATION_CSV_HEADER = 'date/time, ssid, mssid, rid, x1[m], y1[m], x2[m], y2[m], x[m], y[m],'\
                        ' theta[degrees], progress[%], span[m], cutter stray[%],'\
                        ' battery[%], loaded[%], confidence[%], essid, rssi'

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
                if debug:
                    patt_logger.debug(
                        'including node ({:.2f}m, {:.2f}m) whose inter-node-distance: {:.3f} >= {:.3f}'.format(
                            x_m,
                            y_m,
                            inter_node_dist,
                            min_internode_dist_m
                            )
                        )
                j += 1
            else:
                patt_logger.warning(
                    'skipping node ({:.2f}m, {:.2f}m) whose inter-node-distance: {:.3f} < {:.3f}'.format(
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
    
def ping_server(host):
    
    r = ping(host)
    result = r is not None and r is not False
    return result