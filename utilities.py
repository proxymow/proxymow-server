import platform
import time
import sys
import os
import re
import psutil
import tracemalloc
from datetime import datetime, timedelta
import numpy as np
import logging
import math
from types import ModuleType, FunctionType
from io import BytesIO
from gc import get_referents
from ping3 import ping
from PIL import Image, ImageFont
import base64
import subprocess

from destination import Attitude

np.seterr(all='raise')

LOCATION_CSV_HEADER = 'date/time, ssid, mssid, rid, x1[m], y1[m], x2[m], y2[m], x[m], y[m],'\
                        ' theta[degrees], progress[%], span[m], cutter stray[m],'\
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
    pattern = re.compile(r'\s+')
    encode_images = True
    meta_str = '{}, {}, {}, {}, {}'.format(
        datetime.now().isoformat(),
        ssid,
        i,
        '{1:.0f}x{0:.0f}'.format(
            *np.rint(np.array(viewport.origin) * resolution / 100)),
        '{1}x{0}'.format(*resolution)
    )
    cont_img_str = '[]'
    thr_img_str = '[]'
    if (viewport is not None and not viewport.isnull) or incl_fullsize:
        if cont_img_arr is not None:
            if encode_images:
                cont_img_str = convert_array_to_base64(cont_img_arr)
            else:
                cont_img_str = str(cont_img_arr.tolist())
        if cont_thr_arr is not None:
            if encode_images:
                thr_img_str = convert_array_to_base64(cont_thr_arr)
            else:
                thr_img_str = str((cont_thr_arr * 255).astype(np.uint8).tolist())
    cont_str = str(np.round(contour, 3).tolist())
    msg_str = '|'.join([meta_str, cont_img_str, thr_img_str, cont_str])
    stripped_msg = re.sub(pattern, '', msg_str)
    return stripped_msg, [len(meta_str), len(cont_img_str), len(thr_img_str), len(cont_str)]


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
                        'i: {} j: {} inter node distance: {}'.format(i, j, inter_node_dist))
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

def get_mem_diagnostics():

    # 1. Get system-level memory usage (RSS)
    process = psutil.Process(os.getpid())
    rss_memory = process.memory_info().rss  # Total memory OS allocated to process

    # 2. Get Python-level tracked memory
    current, _peak = tracemalloc.get_traced_memory()

    # 3. Calculate the untracked overhead (often indicates fragmentation)
    fragmentation_overhead = rss_memory - current

    result = {}
    result['OS Resident Set Size (RSS) MB'] = rss_memory / 1024 / 1024
    result['Python Tracked Memory MB'] = current / 1024 / 1024
    result['Estimated Overhead/Frag MB'] = fragmentation_overhead / 1024 / 1024

    return result

def get_mem_usage():
    mem = psutil.virtual_memory()
    total_mb = mem.total / (1024 ** 2)
    available_mb = mem.available / (1024 ** 2)
    if mem.percent > 85 or available_mb < 50:
        status = 'CRITICAL'
    elif mem.percent > 70:
        status = 'CONCERNING'
    else:
        status = 'HEALTHY'
    cma_stats = ['0', '0']
    linux = (platform.system() == 'Linux')
    if linux:
        try:
            cma_details = subprocess.run(['grep Cma /proc/meminfo'], stdout=subprocess.PIPE, shell=True)
            cma_usage_str = str(cma_details.stdout)
            cma_stats = re.findall(r'\d+', cma_usage_str)
            if len(cma_stats) == 0:
                raise Exception('Not Available')
        except:
            pass

    total_cma, free_cma = int(cma_stats[0]), int(cma_stats[1])

    return total_mb, available_mb, total_cma, free_cma, status

def get_mem_stats():
    memory_usage, memory_avail, total_cma, free_cma, status = get_mem_usage()
    mem_diag = get_mem_diagnostics()
    tmplt = ' Mem Used: {:.1f}MB Available: {:.1f}MB Rating: {} Free CMA: {:.1f}/{:.1f}MB'
    tmplt += ' RSS: {:.1f}MB Python Tracked: {:.1f}MB Est Frag: {:.1f}MB'
    mem_stats = tmplt.format(
        memory_usage,
        memory_avail,
        status,
        free_cma/1000,
        total_cma/1000,
        *mem_diag.values()
        )
    return mem_stats

def get_kernel_pools():
    """Returns kernel pool memory or CMA stats based on the Operating System."""
    if sys.platform.startswith("win32"):
        try:
            mem = psutil.virtual_memory()
            paged_mb = getattr(mem, "paged", 0) / (1024 ** 2)
            nonpaged_mb = getattr(mem, "nonpaged", 0) / (1024 ** 2)
            return f"Kernel Pools: Paged {paged_mb:.1f}MB | Non-Paged {nonpaged_mb:.1f}MB"
        except Exception:
            return "Kernel Pools: N/A" # Fallback if windows counters fail

    else: # Linux
        cma_total, cma_free = 0, 0
        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("CmaTotal:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                cma_total = int(parts[1]) * 1024  # Extract the text item, convert to Bytes
                        elif line.startswith("CmaFree:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                cma_free = int(parts[1]) * 1024
            except Exception as e:
                print(e)
        cma_used = cma_total - cma_free
        cma_percent = (cma_used / cma_total) * 100 if cma_total > 0 else 0.0
        return f"CMA: {cma_used / (1024**2):.0f}/{cma_total / (1024**2):.0f} MB Used ({cma_percent:.1f}%)"

def get_memory_summary_string():
    """Returns a single-line memory summary, completely safe against PDH crashes."""
    # 1. Fetch baseline RAM (this rarely relies on the fragile PDH subsystem)
    mem = psutil.virtual_memory()
    ram_str = f"RAM: {mem.used / (1024**2):.0f}/{mem.total / (1024**2):.0f} MB Used ({mem.percent}%)"

    # 2. Fetch Swap Memory safely (handles PDH corruption)
    try:
        swap = psutil.swap_memory()
        swap_str = f"Swap: {swap.used / (1024**2):.0f}/{swap.total / (1024**2):.0f} MB Used ({swap.percent}%)"
    except RuntimeError:
        swap_str = "Swap: N/A (Perf Counters Corrupt)"

    # 3. Fetch OS specific metrics safely
    os_specific_str = get_kernel_pools()

    # 4. Assess
    available_mb = mem.available / (1024 ** 2)
    if mem.percent > 85 or available_mb < 50:
        status = 'CRITICAL'
    elif mem.percent > 70:
        status = 'CONCERNING'
    else:
        status = 'HEALTHY'

    return f"MEMORY | {ram_str} | {swap_str} | {os_specific_str} | {status}"

def get_uptime():
    return int(time.time() - psutil.boot_time())

def get_uptime_string():
    return timedelta(seconds=get_uptime())

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

def convert_array_to_base64(sub_array, size=None):

    # handle float normalization (0.0 - 1.0 -> 0 - 255)
    if np.issubdtype(sub_array.dtype, np.floating):
        if sub_array.max() <= 1.0:
            sub_array = (sub_array * 255).astype(np.uint8)
        else:
            sub_array = sub_array.astype(np.uint8)

    # ensure data type is strictly uint8
    elif sub_array.dtype != np.uint8:
        sub_array = sub_array.astype(np.uint8)

    # convert numpy array to PIL Image
    pil_img_in = Image.fromarray(sub_array).convert('RGB')

    # resize if necessary
    if size is None:
        pil_img = pil_img_in
    else:
        pil_img = pil_img_in.resize(size)

    # compress and save into an in-memory bytes buffer
    buffer = BytesIO()
    pil_img.save(buffer, format="JPEG", quality=80)

    # convert buffer to Base64 string
    img_string = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return img_string


def load_sans_serif_font(size: int = 16):
    '''
        Loads the system's default sans-serif font using Pillow's native lookups.
    '''
    system = sys.platform.lower()
    
    # 1. Map 'sans-serif' to the specific standard OS font filenames
    if system.startswith("win"):
        font_names = ["arial.ttf", "segoeui.ttf"]
    elif system == "darwin":  # macOS
        font_names = ["Helvetica.ttc", "Arial.ttf"]
    else:  # Linux / Unix
        font_names = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Ubuntu-R.ttf"]

    # 2. Let Pillow scan the OS font directories automatically
    for font_name in font_names:
        try:
            # Pillow automatically checks C:\Windows\Fonts, /Library/Fonts, /usr/share/fonts, etc.
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue  # Try the next fallback if the font isn't installed

    # 3. Emergency fallback if no true-type system fonts can be found
    return ImageFont.load_default()
