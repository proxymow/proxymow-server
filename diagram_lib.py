import sys
import io
import re
import datetime
import numpy as np
from PIL import Image, ImageDraw
from math import radians, degrees, atan2, sqrt
import copy
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
import poses
from infill_sharpener import Projection
import contour_lib as cl


def plot_excursion(excursion_log_file_path, srid=1, erid=1, crid=1, arrow_length_m=0.1, logger=None, annotate=False):

    # initialise response
    img_buf = io.BytesIO()

    # ensure arrow has some length - zero may be passed in from Null Mower
    arrow_length_m = max(0.1, arrow_length_m)

    # plot the excursion
    fig = Figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.grid(True)
    cmap = ['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet']
    x1_m = y1_m = x2_m = y2_m = -1
    pose_index = 0
    locations = {}
    # add the target line and mower pose from location log
    try:
        with open(excursion_log_file_path, 'r', errors="ignore") as f:
            while True:
                try:
                    loc_line = f.readline()
                    if not loc_line:
                        break
                    loc_cells = loc_line.split(",")
                    lrid = int(loc_cells[3])
                    if lrid > erid:
                        break
                    elif srid <= lrid <= erid:
                        if lrid in locations:
                            locations[lrid].append(loc_cells)
                        else:
                            locations[lrid] = [loc_cells]
                except ValueError as _ex0:
                    err_line = sys.exc_info()[-1].tb_lineno
                    # pass over headings
                except Exception as ex1:
                    err_line = sys.exc_info()[-1].tb_lineno
                    if logger:
                        logger.error('Error in stages loop: ' +
                                     str(ex1) + ' on line ' + str(err_line))

        if len(locations.keys()) == 0:
            info_img = Image.new('RGBA', (400, 300), '#00000000')
            info_draw = ImageDraw.Draw(info_img)
            info_draw.text((10, 10), 'No Routes Found',
                           fill='red', font_size=12)
            info_img.save(img_buf, 'png')

        try:
            max_path_distances = []
            mean_path_differences = []
            for rid in locations.keys():
                sel_loc_cells = locations[rid][0]

                x1_m = float(sel_loc_cells[4])
                y1_m = float(sel_loc_cells[5])
                x2_m = float(sel_loc_cells[6])
                y2_m = float(sel_loc_cells[7])

                # re-calculate navigation user-terms
                path_length_m = sqrt((x2_m - x1_m)**2 +
                                     (y2_m - y1_m)**2) if x1_m != -1 else 0
                path_angle_rad = atan2((y2_m - y1_m), (x2_m - x1_m))
                path_angle_deg = degrees(path_angle_rad)
                tgt_radius_m = 0.075

                if logger:
                    logger.debug('Arrow Length {0}m'.format(arrow_length_m))
                    logger.debug(
                        'Stage starting at ({0}, {1})'.format(x1_m, y1_m))
                    logger.debug(
                        'Stage finishing at ({0}, {1})'.format(x2_m, y2_m))
                    logger.debug('Path Length {0}m'.format(path_length_m))
                    logger.debug('Path Angle {0}deg'.format(path_angle_deg))

                # draw start point - black
                ax.plot([x1_m], [y1_m], marker='o', color='k',
                        linestyle='None', fillstyle='full', markersize=10)
                # draw finish point target as concentric circles - green
                inner_circle = mpatches.Circle(
                    (x2_m, y2_m), tgt_radius_m, fill=False)
                outer_circle = mpatches.Circle(
                    (x2_m, y2_m), tgt_radius_m * 2, fill=False)
                path_arc = mpatches.Arc(
                    (x1_m, y1_m), path_length_m * 2, path_length_m * 2, path_angle_deg, -20, 20, linestyle='--')
                ax.add_patch(inner_circle)
                # only draw outer target and arc for edge nodes 1, 3, 5, etc
                if rid % 2 == 1:
                    ax.add_patch(outer_circle)
                    ax.add_patch(path_arc)
                prev_mssid = -1
                max_path_distance = 0
                tot_path_distance = 0
                num_locs = 0
                for sel_loc_cells in locations[rid]:
                    num_locs += 1
                    ssid = int(sel_loc_cells[1])
                    mssid = int(sel_loc_cells[2])
                    x_m = float(sel_loc_cells[8])
                    y_m = float(sel_loc_cells[9])
                    t_deg = float(sel_loc_cells[10])
                    t_rad = radians(t_deg)
                    pose = poses.Pose(x_m, y_m, t_rad)
                    if logger:
                        logger.debug('Posing at {0}'.format(
                            pose.as_concise_str()))

                    # perpendicular distance to track path line
                    d = ((x2_m - x1_m) * (y1_m - y_m) - (x1_m - x_m) * (y2_m -
                         y1_m)) / sqrt((x2_m - x1_m)**2 + (y2_m - y1_m)**2)
                    tot_path_distance += abs(d)
                    max_path_distance = max(abs(d), max_path_distance)
                    if logger:
                        logger.debug(
                            'Max Distance to Path: {0:.2f}m'.format(max_path_distance))

                    # check for motion...
                    if prev_mssid == mssid:
                        in_motion = True
                    else:
                        in_motion = False

                    prev_mssid = mssid

                    # draw pose - color sequence
                    arw_start, arw_finish = pose.as_arrow(arrow_length_m)
                    if logger:
                        logger.debug('Arrow {0}'.format(
                            (arw_start, arw_finish)))
                    if in_motion:
                        arrow = mpatches.FancyArrowPatch(
                            arw_start, arw_finish, mutation_scale=10, fill=False, color=cmap[pose_index % 7], alpha=0.25)
                    else:
                        arrow = mpatches.FancyArrowPatch(
                            arw_start, arw_finish, mutation_scale=10, fill=True, color=cmap[pose_index % 7], alpha=1.0)

                    ax.add_patch(copy.copy(arrow))
                    if annotate:
                        if pose_index % 2 == 0:
                            ax.annotate(str(ssid) + ' ' + str(lrid) +
                                        ' ' + pose.as_concise_str(), (arw_start))
                        else:
                            ax.annotate(str(ssid) + ' ' + str(lrid) +
                                        ' ' + pose.as_concise_str(), (arw_finish))
                    pose_index += 1
                max_path_distances.append(round(max_path_distance, 3))
                mean_path_distance = tot_path_distance / num_locs
                mean_path_differences.append(round(mean_path_distance, 3))
        except Exception as ex2:
            err_line = sys.exc_info()[-1].tb_lineno
            if logger:
                logger.error('Error in stages: ' + str(ex2) +
                             ' on line ' + str(err_line))
        # add title
        if srid == erid:
            fig.suptitle('Stage {} from ({}, {}) to ({}, {}) Max Stray: {}m Mean Stray: {}m'.format(
                srid, x1_m, y1_m, x2_m, y2_m, max_path_distances, mean_path_differences))
        else:
            fig.suptitle('Stages {} to {} of {} Max Stray: {}m Mean Stray: {}m'.format(
                srid, erid, crid, max_path_distances, mean_path_differences))

        # set scale and fix aspect ratio
        ax.autoscale(tight=True)
        x_lim_min, x_lim_max = ax.get_xlim()
        y_lim_min, y_lim_max = ax.get_ylim()
        x_range_m = max(x_lim_max - x_lim_min, 2.0)  # Minimum of 1m
        y_range_m = max(y_lim_max - y_lim_min, 2.0)
        x_mid_m = np.mean([x_lim_min, x_lim_max])
        y_mid_m = np.mean([y_lim_min, y_lim_max])
        if x_range_m > y_range_m:
            ax.set_ylim(y_mid_m - x_range_m / 2, y_mid_m + x_range_m / 2)
            ax.set_xlim(x_mid_m - x_range_m / 2, x_mid_m + x_range_m / 2)
        else:
            ax.set_xlim(x_mid_m - y_range_m / 2, x_mid_m + y_range_m / 2)
            ax.set_ylim(y_mid_m - y_range_m / 2, y_mid_m + y_range_m / 2)

        fig.savefig(img_buf, format='jpeg')

    except Exception as ex3:
        err_line = sys.exc_info()[-1].tb_lineno
        if logger:
            logger.error('Error in stages: ' + str(ex3) +
                         ' on line ' + str(err_line))
    return img_buf

def plot_contour_entry_as_projection(host, entry, hide_conf, logger):
    try:

        # unpack entry
        (metadata_line, img_cont_line, thr_cont_line,
         cont_data_line) = entry.split('|')

        # initialise response
        img_buf = io.BytesIO()

        metadata_line_clean = re.sub(
            r"\s+", "", metadata_line, flags=re.UNICODE)
        (capture_datetime, lssid, lcid) = metadata_line_clean.split(',')[:3]

        dat_cnt_as_list = eval(cont_data_line)
        dat_cnt_as_npa = np.array(dat_cnt_as_list)

        img_cnt_as_list = eval(img_cont_line)
        img_cnt_as_npa = np.array(img_cnt_as_list)

        thr_cnt_as_list = eval(thr_cont_line)
        thr_cnt_as_npa = np.array(thr_cnt_as_list)

        tgt = Projection(
            lssid,
            lcid,
            dat_cnt_as_npa,
            hide_conf,
            logger=logger,
            debug=True
        )
        tgt.assess(host.score_props)

        # overlay contour?
        disp_img = None
        try:
            cont_px_xarr_yarr = np.round(host.data_mapper.reverse_coordinates(
                dat_cnt_as_npa[:, 0], dat_cnt_as_npa[:, 1])).astype(int)
            cont_px = np.dstack(np.flip(cont_px_xarr_yarr))[0] - (
                host.viewport.origin[0] * host.config['optical.height'] / 100,
                host.viewport.origin[1] * host.config['optical.width'] / 100
            )
            disp_img = Image.fromarray(img_cnt_as_npa).convert('RGB')
            disp_draw = ImageDraw.Draw(disp_img)
            cl.overlay_contours([cont_px[::3]], disp_draw, (1, 1), 'orange', None)
        except Exception as ex1:
            err_line = sys.exc_info()[-1].tb_lineno
            if logger:
                logger.error('Error overlaying contour: ' +
                             str(ex1) + ' on line ' + str(err_line))
            
        plot_projection_img(tgt, capture_datetime,
                            thr_cnt_as_npa, disp_img, img_buf, logger)
    except Exception as ex2:
        err_line = sys.exc_info()[-1].tb_lineno
        if logger:
            logger.error('Error in plot contour as projection: ' +
                         str(ex2) + ' on line ' + str(err_line))

    return img_buf


def plot_projection_img(proj, capture_datetime, src_arr_img, disp_img, img_buf, logger):

    try:
        fig = Figure(figsize=(12, 8))
        gridspec = fig.add_gridspec(2, 2)  # RowsxCols
        subplotspec0 = gridspec.new_subplotspec((0, 0), 1, 1)  # display image
        subplotspec1 = gridspec.new_subplotspec((1, 0), 1, 1)  # source image
        subplotspec2 = gridspec.new_subplotspec((0, 1), 2, 1)  # contour
        ax0 = fig.add_subplot(subplotspec0)
        ax0.title.set_text('Display Image')
        ax1 = fig.add_subplot(subplotspec1)
        ax1.title.set_text('Analysis Image')
        ax2 = fig.add_subplot(subplotspec2)

        try:
            # original image
            if disp_img is not None:
                ax0.imshow(disp_img, interpolation='none')
            if src_arr_img is not None:
                ax1.imshow(src_arr_img, cmap='gray', interpolation='none')
        except Exception as ex2:
            err_line = sys.exc_info()[-1].tb_lineno
            if logger:
                logger.error('Error in contour diagram greyscale imshow: ' +
                             str(ex2) + ' on line ' + str(err_line))

        # use contour capture time - if available
        try:
            proj.start_time_secs = datetime.datetime.fromisoformat(
                capture_datetime).timestamp()
        except Exception:
            pass
        proj.plot(ax2)
        ax2.grid()
        ax2.set_box_aspect(1)
        ax2.set_aspect('equal')
        ax2.margins(0.2, 0.2)  # default is 0.05
        # standardise plot space
        half_std_dim = 0.25  # metres
        # get axis limits
        x_low, x_high = ax2.get_xlim()
        y_low, y_high = ax2.get_ylim()
        mid_x = np.mean([x_low, x_high])
        mid_y = np.mean([y_low, y_high])
        std_x_low, std_x_high = mid_x - half_std_dim, mid_x + half_std_dim
        std_y_low, std_y_high = mid_y - half_std_dim, mid_y + half_std_dim
        ax2.set_xlim(std_x_low, std_x_high)
        ax2.set_ylim(std_y_low, std_y_high)
        fig.savefig(img_buf, format='jpeg',
                    bbox_inches='tight', pad_inches=0.2)
        fig.clear()
    except Exception as ex1:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in plot projection image: ' +
                     str(ex1) + ' on line ' + str(err_line))
