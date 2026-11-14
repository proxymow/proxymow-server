import sys
import io
import re
import time
import datetime
import numpy as np
from PIL import Image, ImageDraw
from math import radians, degrees, atan2, sqrt, sin, cos
import base64
from io import BytesIO

from infill_sharpener import Projection
import contour_lib as cl
import utilities as ut

def plot_contour_entry_as_projection(host, entry, hide_conf, logger):
    try:
        # lookup the expected number of vertices
        target_num_vertices = host.config['mower.target_num_vertices']

        # lookup shape rotation angle
        rotation_ccw_deg = host.config['mower.target_rotation_ccw_deg']

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

        try:
            img_bytes = base64.b64decode(img_cont_line)
            decoded_rgb_img = Image.open(BytesIO(img_bytes))
            decoded_grey_img = decoded_rgb_img.convert('L')
            img_cnt_as_npa = np.array(decoded_grey_img)
        except:
            img_cnt_as_list = eval(img_cont_line)
            img_cnt_as_npa = np.array(img_cnt_as_list).astype(np.uint8)

        try:
            img_bytes = base64.b64decode(thr_cont_line)
            decoded_rgb_img = Image.open(BytesIO(img_bytes))
            decoded_grey_img = decoded_rgb_img.convert('L')
            thr_cnt_as_npa = np.array(decoded_grey_img)
        except:
            thr_cnt_as_list = eval(thr_cont_line)
            thr_cnt_as_npa = np.array(thr_cnt_as_list).astype(np.uint8)

        tgt = Projection(
            lssid,
            lcid,
            dat_cnt_as_npa,
            target_num_vertices,
            -rotation_ccw_deg,
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
                logger.error('Error overlaying contour: ' + str(dat_cnt_as_npa) +
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

        # ---------------------------------------------------------
        # Image/layout dimensions
        #
        # Equivalent to the previous 12 x 9 inch figure at
        # approximately 100 dpi.
        #
        # Layout:
        #
        #   +-------------------+-----------------------+
        #   | Display Image     |                       |
        #   |                   |                       |
        #   +-------------------+     Projection        |
        #   | Analysis Image    |                       |
        #   |                   |                       |
        #   +-------------------+-----------------------+
        # ---------------------------------------------------------

        img_width = 1024
        img_height = 3 * img_width // 4

        left_width = img_width // 2
        right_width = img_width - left_width
        top_height = img_height // 2
        bottom_height = img_height - top_height

        # Small border corresponding approximately to
        # bbox_inches='tight', pad_inches=0.2
        margin = 30

        # Create final image
        canvas = Image.new(
            'RGB',
            (img_width, img_height),
            'white'
        )

        draw = ImageDraw.Draw(canvas)

        # ---------------------------------------------------------
        # Fonts
        # ---------------------------------------------------------

        font_title = ut.load_sans_serif_font(16)
        font_projection = ut.load_sans_serif_font(12)

        # ---------------------------------------------------------
        # Draw an image into a panel
        # ---------------------------------------------------------

        def draw_image_panel(
                source,
                panel_left,
                panel_top,
                panel_width,
                panel_height,
                title,
                grayscale=False):

            # panel title
            draw.text(
                (
                    panel_left + margin,
                    panel_top + 5
                ),
                title,
                fill='black',
                font=font_title
            )

            if source is None:
                return

            try:

                # Convert numpy/PIL source to PIL image
                if isinstance(source, Image.Image):
                    image = source.copy()
                else:
                    image = Image.fromarray(source)

                if grayscale:
                    image = image.convert('L')
                    image = image.convert('RGB')
                else:
                    image = image.convert('RGB')

                # Available area below title
                available_width = panel_width - 2 * margin
                available_height = panel_height - 35 - margin

                if available_width <= 0 or available_height <= 0:
                    return

                # Preserve original aspect ratio
                image.thumbnail(
                    (
                        available_width,
                        available_height
                    ),
                    Image.Resampling.NEAREST
                )

                # Centre in panel
                x = (
                    panel_left +
                    (panel_width - image.width) // 2
                )

                y = (
                    panel_top +
                    30 +
                    (available_height - image.height) // 2
                )

                canvas.paste(
                    image,
                    (x, y)
                )

            except Exception as ex:

                err_line = sys.exc_info()[-1].tb_lineno

                if logger:
                    logger.error(
                        'Error drawing image panel: ' +
                        str(ex) +
                        ' on line ' +
                        str(err_line)
                    )

        # ---------------------------------------------------------
        # Display image
        # ---------------------------------------------------------

        draw_image_panel(
            disp_img,
            0,
            0,
            left_width,
            top_height,
            'Display Image',
            grayscale=False
        )

        # ---------------------------------------------------------
        # Analysis image
        # ---------------------------------------------------------

        draw_image_panel(
            src_arr_img,
            0,
            top_height,
            left_width,
            bottom_height,
            'Analysis Image',
            grayscale=True
        )

        # ---------------------------------------------------------
        # Projection panel
        # ---------------------------------------------------------

        proj_left = left_width
        proj_top = 0
        proj_width = right_width
        proj_height = img_height

        # Projection drawing area
        plot_left = proj_left + margin
        plot_right = proj_left + proj_width - margin
        plot_top = proj_top + 35
        plot_bottom = proj_top + proj_height - margin

        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        # ---------------------------------------------------------
        # Projection coordinate system
        #
        # Match the previous:
        #
        #   ax2.margins(0.2, 0.2)
        #   equal aspect
        #   standardised to +/- 0.25m
        #
        # The actual standardised range is 0.5m x 0.5m.
        # ---------------------------------------------------------

        half_std_dim = 0.25

        # First estimate the projection centre from the
        # contour/geometry.
        #
        # This corresponds to getting the Matplotlib axis limits
        # after Projection.plot() and then finding their midpoint.

        all_points = []

        try:

            if proj.c_raw_in is not None:
                all_points.extend(
                    [
                        (float(p[0]), float(p[1]))
                        for p in proj.c_raw_in
                    ]
                )

            if proj.c_ch is not None:
                all_points.extend(
                    [
                        (float(p[0]), float(p[1]))
                        for p in proj.c_ch
                    ]
                )

            for name in (
                'tip',
                'tail',
                'v1',
                'v2',
                'v3',
                'v4',
                'v5'
            ):
                value = getattr(proj, name, None)

                if value is not None:
                    all_points.append(
                        (
                            float(value[0]),
                            float(value[1])
                        )
                    )

            if proj.centroid_x is not None:
                all_points.append(
                    (
                        float(proj.centroid_x),
                        float(proj.centroid_y)
                    )
                )

            if proj.cx is not None:
                all_points.append(
                    (
                        float(proj.cx),
                        float(proj.cy)
                    )
                )

            if proj.bbcx is not None:
                all_points.append(
                    (
                        float(proj.bbcx),
                        float(proj.bbcy)
                    )
                )

        except Exception:
            all_points = []

        if all_points:

            xs = [p[0] for p in all_points]
            ys = [p[1] for p in all_points]

            x_low = min(xs)
            x_high = max(xs)
            y_low = min(ys)
            y_high = max(ys)

            # Approximation of ax2.margins(0.2, 0.2)
            x_range = x_high - x_low
            y_range = y_high - y_low

            if x_range <= 0:
                x_range = 0.01

            if y_range <= 0:
                y_range = 0.01

            x_low -= x_range * 0.2
            x_high += x_range * 0.2
            y_low -= y_range * 0.2
            y_high += y_range * 0.2

            mid_x = (x_low + x_high) / 2
            mid_y = (y_low + y_high) / 2

        else:

            mid_x = 0.0
            mid_y = 0.0

        # ---------------------------------------------------------
        # Standard projection range
        # ---------------------------------------------------------

        x_low = mid_x - half_std_dim
        x_high = mid_x + half_std_dim

        y_low = mid_y - half_std_dim
        y_high = mid_y + half_std_dim

        # ---------------------------------------------------------
        # projection grid
        # ---------------------------------------------------------

        grid_step = 0.05
        grid_colour = '#d0d0d0'
        label_colour = 'black'

        # Use equal X/Y scaling so the grid squares remain square
        scale = min(
            plot_width / (x_high - x_low),
            plot_height / (y_high - y_low)
        )

        plot_cx = (plot_left + plot_right) / 2
        plot_cy = (plot_top + plot_bottom) / 2

        data_cx = (x_low + x_high) / 2
        data_cy = (y_low + y_high) / 2


        def to_pixel(x, y):

            px = plot_cx + (x - data_cx) * scale
            py = plot_cy - (y - data_cy) * scale

            return (
                int(round(px)),
                int(round(py))
            )


        # ---------------------------------------------------------
        # vertical grid lines + X labels
        # ---------------------------------------------------------

        first_x_index = int(np.floor(x_low / grid_step))
        last_x_index = int(np.ceil(x_high / grid_step))

        for i in range(first_x_index, last_x_index + 1):

            x = i * grid_step

            px, _ = to_pixel(x, data_cy)

            if px < plot_left or px > plot_right:
                continue

            draw.line(
                (
                    px,
                    plot_top,
                    px,
                    plot_bottom
                ),
                fill=grid_colour,
                width=1
            )

            draw.text(
                (
                    px,
                    plot_bottom + 3
                ),
                f'{x:.2f}',
                fill=label_colour,
                font=font_projection,
                anchor='ma'
            )


        # ---------------------------------------------------------
        # horizontal grid lines + Y labels
        # ---------------------------------------------------------

        first_y_index = int(np.floor(y_low / grid_step))
        last_y_index = int(np.ceil(y_high / grid_step))

        for i in range(first_y_index, last_y_index + 1):

            y = i * grid_step

            _, py = to_pixel(data_cx, y)

            if py < plot_top or py > plot_bottom:
                continue

            draw.line(
                (
                    plot_left,
                    py,
                    plot_right,
                    py
                ),
                fill=grid_colour,
                width=1
            )

            draw.text(
                (
                    plot_left - 5,
                    py
                ),
                f'{y:.2f}',
                fill=label_colour,
                font=font_projection,
                anchor='ra'
            )

        # ---------------------------------------------------------
        # Projection
        # ---------------------------------------------------------

        # use contour capture time - if available
        try:
            proj.start_time_secs = datetime.datetime.fromisoformat(
                capture_datetime).timestamp()
        except Exception:
            pass

        proj.plot(
            draw,
            to_pixel,
            font=font_projection,
            title_offset=(plot_left + 5, plot_top + 5)
        )

        # ---------------------------------------------------------
        # Projection panel border
        # ---------------------------------------------------------

        draw.rectangle(
            (
                plot_left,
                plot_top,
                plot_right,
                plot_bottom
            ),
            outline='#808080',
            width=1
        )

        # ---------------------------------------------------------
        # Save
        # ---------------------------------------------------------

        canvas.save(
            img_buf,
            format='jpeg',
            quality=90
        )

    except Exception as ex1:

        err_line = sys.exc_info()[-1].tb_lineno

        if logger:
            logger.error(
                'Error in plot projection image: ' +
                str(ex1) +
                ' on line ' +
                str(err_line)
            )

    return img_buf

def plot_excursion(excursion_log_file_path, srid=1, erid=1, crid=1,
                   arrow_length_m=0.1, logger=None):
    """
    Pillow replacement for the original Matplotlib plot_excursion().

    Returns:
        io.BytesIO containing a JPEG image.
    """

    img_buf = io.BytesIO()

    # Ensure arrow has some length - zero may be passed in from Null Mower
    arrow_length_m = max(0.1, arrow_length_m)

    img_width = 800
    img_height = 600

    # RGB colours.  Alpha is supplied separately when required.
    cmap = [
        (255, 0, 0),        # red
        (255, 165, 0),      # orange
        (255, 255, 0),      # yellow
        (0, 128, 0),        # green
        (0, 0, 255),        # blue
        (75, 0, 130),       # indigo
        (238, 130, 238)     # violet
    ]

    x1_m = y1_m = x2_m = y2_m = -1

    pose_index = 0
    locations = {}

    # ------------------------------------------------------------------
    # Read location log
    # ------------------------------------------------------------------

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

                except ValueError:
                    # Pass over headings
                    pass

                except Exception as ex1:

                    err_line = sys.exc_info()[-1].tb_lineno

                    if logger:
                        logger.error(
                            'Error in stages loop: ' +
                            str(ex1) +
                            ' on line ' +
                            str(err_line)
                        )

        # ------------------------------------------------------------------
        # No routes
        # ------------------------------------------------------------------

        if len(locations) == 0:

            info_img = Image.new(
                'RGB',
                (400, 300),
                'white'
            )

            info_draw = ImageDraw.Draw(info_img)

            info_draw.text(
                (10, 10),
                'No Routes Found',
                fill='red'
            )

            info_img.save(img_buf, 'png')

            return img_buf

        # ------------------------------------------------------------------
        # First pass
        #
        # Read all geometry and calculate the equivalent of:
        #
        #     ax.autoscale(tight=True)
        #
        # before creating the image.
        # ------------------------------------------------------------------

        max_path_distances = []
        mean_path_differences = []

        stage_data = []

        plot_x = []
        plot_y = []

        for rid in locations:

            sel_loc_cells = locations[rid][0]

            x1_m = float(sel_loc_cells[4])
            y1_m = float(sel_loc_cells[5])

            x2_m = float(sel_loc_cells[6])
            y2_m = float(sel_loc_cells[7])

            # Recalculate navigation terms
            path_length_m = (
                sqrt(
                    (x2_m - x1_m) ** 2 +
                    (y2_m - y1_m) ** 2
                )
                if x1_m != -1 else 0
            )

            path_angle_rad = atan2(
                y2_m - y1_m,
                x2_m - x1_m
            )

            path_angle_deg = degrees(path_angle_rad)

            tgt_radius_m = 0.075

            if logger:

                logger.debug(
                    'Arrow Length {}m'.format(
                        arrow_length_m
                    )
                )

                logger.debug(
                    'Stage starting at ({}, {})'.format(
                        x1_m,
                        y1_m
                    )
                )

                logger.debug(
                    'Stage finishing at ({}, {})'.format(
                        x2_m,
                        y2_m
                    )
                )

                logger.debug(
                    'Path Length {}m'.format(
                        path_length_m
                    )
                )

                logger.debug(
                    'Path Angle {}deg'.format(
                        path_angle_deg
                    )
                )

            # Add the start and finish to the bounding box.
            plot_x.extend([x1_m, x2_m])
            plot_y.extend([y1_m, y2_m])

            # Target circles
            plot_x.extend([
                x2_m - tgt_radius_m * 2,
                x2_m + tgt_radius_m * 2
            ])

            plot_y.extend([
                y2_m - tgt_radius_m * 2,
                y2_m + tgt_radius_m * 2
            ])

            # The path arc is centred on the start position.
            # Its radius is path_length_m.
            if rid % 2 == 1:

                plot_x.extend([
                    x1_m - path_length_m,
                    x1_m + path_length_m
                ])

                plot_y.extend([
                    y1_m - path_length_m,
                    y1_m + path_length_m
                ])

            # --------------------------------------------------------------
            # Read poses
            # --------------------------------------------------------------

            prev_mssid = -1

            max_path_distance = 0
            tot_path_distance = 0
            num_locs = 0

            poses = []

            path_denominator = sqrt(
                (x2_m - x1_m) ** 2 +
                (y2_m - y1_m) ** 2
            )

            for sel_loc_cells in locations[rid]:

                num_locs += 1

                track_loop_start = time.time()

                mssid = int(sel_loc_cells[2])

                x_m = float(sel_loc_cells[8])
                y_m = float(sel_loc_cells[9])

                t_deg = float(sel_loc_cells[10])
                t_rad = radians(t_deg)

                # ----------------------------------------------------------
                # Perpendicular distance to track path
                # ----------------------------------------------------------

                if path_denominator != 0:

                    d = (
                        (
                            (x2_m - x1_m) * (y1_m - y_m)
                            -
                            (x1_m - x_m) * (y2_m - y1_m)
                        )
                        / path_denominator
                    )

                else:
                    d = 0

                tot_path_distance += abs(d)

                max_path_distance = max(
                    abs(d),
                    max_path_distance
                )

                if logger:

                    logger.debug(
                        'Max Distance to Path: {:.2f}m'.format(
                            max_path_distance
                        )
                    )

                # ----------------------------------------------------------
                # Check for motion
                # ----------------------------------------------------------

                if prev_mssid == mssid:
                    in_motion = True
                else:
                    in_motion = False

                prev_mssid = mssid

                # ----------------------------------------------------------
                # Arrow geometry
                # ----------------------------------------------------------

                arw_start = (
                    x_m + arrow_length_m * sin(t_rad),
                    y_m - arrow_length_m * cos(t_rad)
                )

                arw_finish = (
                    x_m - arrow_length_m * sin(t_rad),
                    y_m + arrow_length_m * cos(t_rad)
                )

                if logger:

                    logger.debug(
                        'Arrow {}'.format(
                            (arw_start, arw_finish)
                        )
                    )

                    logger.debug(
                        'track loop elapsed: {:.3f} secs'.format(
                            time.time() - track_loop_start
                        )
                    )

                poses.append(
                    (
                        x_m,
                        y_m,
                        arw_start,
                        arw_finish,
                        in_motion
                    )
                )

                # Include arrow ends in the plot bounds.
                plot_x.extend([
                    arw_start[0],
                    arw_finish[0]
                ])

                plot_y.extend([
                    arw_start[1],
                    arw_finish[1]
                ])

                pose_index += 1

            max_path_distances.append(
                round(max_path_distance, 3)
            )

            mean_path_distance = (
                tot_path_distance / num_locs
                if num_locs
                else 0
            )

            mean_path_differences.append(
                round(mean_path_distance, 3)
            )

            stage_data.append(
                (
                    rid,
                    x1_m,
                    y1_m,
                    x2_m,
                    y2_m,
                    path_length_m,
                    path_angle_deg,
                    poses
                )
            )

        # ------------------------------------------------------------------
        # Calculate limits.
        #
        # Equivalent to the original Matplotlib:
        #
        #     ax.autoscale(tight=True)
        #     x_range = max(..., 2.0)
        #     y_range = max(..., 2.0)
        #     equal aspect ratio
        # ------------------------------------------------------------------

        x_lim_min = min(plot_x)
        x_lim_max = max(plot_x)

        y_lim_min = min(plot_y)
        y_lim_max = max(plot_y)

        x_range_m = max(
            x_lim_max - x_lim_min,
            2.0
        )

        y_range_m = max(
            y_lim_max - y_lim_min,
            2.0
        )

        x_mid_m = (x_lim_min + x_lim_max) / 2
        y_mid_m = (y_lim_min + y_lim_max) / 2

        if x_range_m > y_range_m:

            plot_range_m = x_range_m

        else:

            plot_range_m = y_range_m

        x_lim_min = x_mid_m - plot_range_m / 2
        x_lim_max = x_mid_m + plot_range_m / 2

        y_lim_min = y_mid_m - plot_range_m / 2
        y_lim_max = y_mid_m + plot_range_m / 2

        # ------------------------------------------------------------------
        # World -> image transformation
        # ------------------------------------------------------------------

        border_px = 40

        usable_width = img_width - 2 * border_px
        usable_height = img_height - 2 * border_px

        scale = min(
            usable_width / plot_range_m,
            usable_height / plot_range_m
        )

        plot_px_size = plot_range_m * scale

        offset_x = (
            (img_width - plot_px_size) / 2
            - x_lim_min * scale
        )

        offset_y = (
            (img_height - plot_px_size) / 2
            + y_lim_max * scale
        )

        def world_to_pixel(x, y):
            return (
                int(round(x * scale + offset_x)),
                int(round(offset_y - y * scale))
            )

        # ------------------------------------------------------------------
        # Create image
        # ------------------------------------------------------------------

        img = Image.new(
            'RGB',
            (img_width, img_height),
            'white'
        )

        draw = ImageDraw.Draw(img)

        # ------------------------------------------------------------------
        # Grid
        #
        # Matplotlib's grid is grey. Use 1 metre spacing.
        # ------------------------------------------------------------------

        grid_spacing = 1.0

        x_grid_start = int(
            np.floor(x_lim_min / grid_spacing)
        )

        x_grid_end = int(
            np.ceil(x_lim_max / grid_spacing)
        )

        y_grid_start = int(
            np.floor(y_lim_min / grid_spacing)
        )

        y_grid_end = int(
            np.ceil(y_lim_max / grid_spacing)
        )

        grid_colour = (176, 176, 176)

        for gx in range(
            x_grid_start,
            x_grid_end + 1
        ):

            x = gx * grid_spacing

            draw.line(
                [
                    world_to_pixel(x, y_lim_min),
                    world_to_pixel(x, y_lim_max)
                ],
                fill=grid_colour,
                width=1
            )

        for gy in range(
            y_grid_start,
            y_grid_end + 1
        ):

            y = gy * grid_spacing

            draw.line(
                [
                    world_to_pixel(x_lim_min, y),
                    world_to_pixel(x_lim_max, y)
                ],
                fill=grid_colour,
                width=1
            )

        # ------------------------------------------------------------------
        # Translucent moving arrows are drawn onto ONE overlay.
        #
        # This is deliberately created once, rather than once per arrow.
        # ------------------------------------------------------------------

        motion_overlay = Image.new(
            'RGBA',
            img.size,
            (0, 0, 0, 0)
        )

        motion_draw = ImageDraw.Draw(motion_overlay)

        # Matplotlib alpha=0.25 is approximately 64/255.
        motion_alpha = 64

        # ------------------------------------------------------------------
        # Helper to draw an arrow
        # ------------------------------------------------------------------

        def draw_arrow(target_draw,
                       p_start,
                       p_finish,
                       colour,
                       alpha=255):

            arrow_colour = (
                colour[0],
                colour[1],
                colour[2],
                alpha
            )

            # Main shaft
            target_draw.line(
                [p_start, p_finish],
                fill=arrow_colour,
                width=2
            )

            # --------------------------------------------------------------
            # Approximate FancyArrowPatch "-|>" arrowhead.
            # --------------------------------------------------------------

            dx = p_finish[0] - p_start[0]
            dy = p_finish[1] - p_start[1]

            length_px = sqrt(
                dx * dx +
                dy * dy
            )

            if length_px <= 0:
                return

            ux = dx / length_px
            uy = dy / length_px

            # Similar visual size to mutation_scale=10.
            head_length = 7
            head_width = 4

            left = (
                p_finish[0]
                - ux * head_length
                + uy * head_width,

                p_finish[1]
                - uy * head_length
                - ux * head_width
            )

            right = (
                p_finish[0]
                - ux * head_length
                - uy * head_width,

                p_finish[1]
                - uy * head_length
                + ux * head_width
            )

            target_draw.polygon(
                [
                    p_finish,
                    left,
                    right
                ],
                fill=arrow_colour
            )

        # ------------------------------------------------------------------
        # Draw stages
        # ------------------------------------------------------------------

        pose_index = 0

        for (
            rid,
            x1_m,
            y1_m,
            x2_m,
            y2_m,
            path_length_m,
            path_angle_deg,
            poses
        ) in stage_data:

            # --------------------------------------------------------------
            # Start point
            # --------------------------------------------------------------

            sx, sy = world_to_pixel(
                x1_m,
                y1_m
            )

            start_radius_px = 6

            draw.ellipse(
                (
                    sx - start_radius_px,
                    sy - start_radius_px,
                    sx + start_radius_px,
                    sy + start_radius_px
                ),
                fill=(0, 0, 0)
            )

            # --------------------------------------------------------------
            # Target inner circle
            # --------------------------------------------------------------

            tx, ty = world_to_pixel(
                x2_m,
                y2_m
            )

            inner_radius_px = max(
                1,
                int(round(tgt_radius_m * scale))
            )

            draw.ellipse(
                (
                    tx - inner_radius_px,
                    ty - inner_radius_px,
                    tx + inner_radius_px,
                    ty + inner_radius_px
                ),
                outline=(0, 0, 0),
                width=1
            )

            # --------------------------------------------------------------
            # Outer target circle and path arc
            # --------------------------------------------------------------

            if rid % 2 == 1:

                outer_radius_px = max(
                    1,
                    int(round(tgt_radius_m * 2 * scale))
                )

                draw.ellipse(
                    (
                        tx - outer_radius_px,
                        ty - outer_radius_px,
                        tx + outer_radius_px,
                        ty + outer_radius_px
                    ),
                    outline=(0, 0, 0),
                    width=1
                )

                # ----------------------------------------------------------
                # Dashed path arc.
                #
                # The original Matplotlib arc is:
                #
                #   centre = start
                #   radius = path_length
                #   rotation = path_angle_deg
                #   theta1 = -20
                #   theta2 = +20
                # ----------------------------------------------------------

                dash_count = 9

                for i in range(dash_count):

                    a1 = (
                        path_angle_deg
                        - 20
                        + i * 40 / dash_count
                    )

                    a2 = (
                        path_angle_deg
                        - 20
                        + (i + 0.55) * 40 / dash_count
                    )

                    p1 = world_to_pixel(
                        x1_m + path_length_m * cos(radians(a1)),
                        y1_m + path_length_m * sin(radians(a1))
                    )

                    p2 = world_to_pixel(
                        x1_m + path_length_m * cos(radians(a2)),
                        y1_m + path_length_m * sin(radians(a2))
                    )

                    draw.line(
                        [p1, p2],
                        fill=(0, 0, 0),
                        width=1
                    )

            # --------------------------------------------------------------
            # Pose arrows
            # --------------------------------------------------------------

            for (
                x_m,
                y_m,
                arw_start,
                arw_finish,
                in_motion
            ) in poses:

                colour = cmap[pose_index % 7]

                p_start = world_to_pixel(
                    arw_start[0],
                    arw_start[1]
                )

                p_finish = world_to_pixel(
                    arw_finish[0],
                    arw_finish[1]
                )

                if in_motion:

                    # Draw all translucent arrows onto the same overlay.
                    draw_arrow(
                        motion_draw,
                        p_start,
                        p_finish,
                        colour,
                        motion_alpha
                    )

                else:

                    # Stationary arrows go directly onto the RGB image.
                    draw_arrow(
                        draw,
                        p_start,
                        p_finish,
                        colour,
                        255
                    )

                pose_index += 1

        # ------------------------------------------------------------------
        # Composite ALL translucent arrows once.
        # ------------------------------------------------------------------

        img = Image.alpha_composite(
            img.convert('RGBA'),
            motion_overlay
        ).convert('RGB')

        draw = ImageDraw.Draw(img)

        # ------------------------------------------------------------------
        # Title
        # ------------------------------------------------------------------

        if srid == erid:

            title = (
                'Stage {} from ({}, {}) to ({}, {}) '
                'Max Stray: {}m Mean Stray: {}m'
            ).format(
                srid,
                x1_m,
                y1_m,
                x2_m,
                y2_m,
                max_path_distances,
                mean_path_differences
            )

        else:

            title = (
                'Stages {} to {} of {} '
                'Max Stray: {}m Mean Stray: {}m'
            ).format(
                srid,
                erid,
                crid,
                max_path_distances,
                mean_path_differences
            )

        # ------------------------------------------------------------------
        # Title at top of image.
        # ------------------------------------------------------------------

        draw.text(
            (10, 8),
            title,
            fill=(0, 0, 0)
        )

        # ------------------------------------------------------------------
        # Return JPEG in the same BytesIO style as the original.
        # ------------------------------------------------------------------

        img.save(
            img_buf,
            format='JPEG'
        )

    except Exception as ex3:

        err_line = sys.exc_info()[-1].tb_lineno

        if logger:

            logger.error(
                'Error in stages: ' +
                str(ex3) +
                ' on line ' +
                str(err_line)
            )

    return img_buf