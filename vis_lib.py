import logging
import io
from io import BytesIO
import sys
import base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage import transform as tf
from skimage import filters
from skimage.morphology import closing
from skimage.measure import find_contours
from shapely.geometry.polygon import Polygon
from copy import deepcopy

import geom_lib
import contour_lib as cl
import utilities
from infill_sharpener import Projection
import constants
import poses
from viewport import Viewport, merge_adjacent_viewports
from diagram_lib import plot_projection_img
from dashed_image_draw import DashedImageDraw
from timesheet import Timesheet, Timesheet2


def matrices_from_quad_points(
    calib_percentages,
    calib_width_m,
    calib_length_m,
    x_offset_m,
    y_offset_m,
    lawn_width_m,
    lawn_length_m,
    lawn_border_m,
    img_height_px,
    img_width_px,
    logger=None,
    debug=False
):

    # derive the matrices:
    #     M: that maps 4 lawn corner calibration points in raw image
    #        to the top-down arena image (lawn + border)
    #     N: the inverse of M
    #     L: that maps pixel coordinates to world arena metres (cartesian)
    #     K: the inverse of L
    #
    #     system is cartesian y ascending up
    #     orientation is Clockwise from Bottom-Left:
    #     1      2
    #     0      3

    M = N = H = K = None

    try:

        arena_width_m = lawn_width_m + (2 * lawn_border_m)
        arena_length_m = lawn_length_m + (2 * lawn_border_m)

        ordering = ['cartesian left bottom/pixel left top',
                    'cartesian left top/pixel left bottom',
                    'cartesian right top/pixel right bottom',
                    'cartesian right bottom/pixel right top']

        net_left_bottom_m = 0, 0
        net_left_top_m = 0, calib_length_m
        net_right_top_m = calib_width_m, calib_length_m
        net_right_bottom_m = calib_width_m, 0
        calib_corners_m = np.float32(
            [net_left_bottom_m, net_left_top_m, net_right_top_m, net_right_bottom_m])

        # find the temporary calibration net matrix
        # this will just be used to find the locations of the lawn and arena corners in camera image
        P = find_coeffs(calib_corners_m, calib_percentages)

        # obtain the inverse
        Q = np.linalg.inv(P)

        # define lawn relative to calibration net
        rel_lawn_left_bottom_m = 0, 0
        rel_lawn_left_top_m = 0, lawn_length_m
        rel_lawn_right_top_m = lawn_width_m, lawn_length_m
        rel_lawn_right_bottom_m = lawn_width_m, 0
        rel_lawn_corners_m = np.float32([rel_lawn_left_bottom_m, rel_lawn_left_top_m,
                                        rel_lawn_right_top_m, rel_lawn_right_bottom_m]) - [x_offset_m, y_offset_m]

        # use reverse matrix lookup to find lawn corners relative to calibration net in camera view
        lawn_corners_pc = []
        for p in rel_lawn_corners_m:
            tgt_pt_px = translate_pixel_point(p, Q, dp=3)
            lawn_corners_pc.append(tgt_pt_px)
            if debug:
                logger.debug('relative lawn {0:<11}m => {1:<11}%'.format(
                    str(p), str(tgt_pt_px)))

        # define arena relative to lawn
        rel_arena_left_bottom_m = rel_lawn_corners_m[0][0] - \
            lawn_border_m, rel_lawn_corners_m[0][1] - lawn_border_m
        rel_arena_left_top_m = rel_lawn_corners_m[1][0] - \
            lawn_border_m, rel_lawn_corners_m[1][1] + lawn_border_m
        rel_arena_right_top_m = rel_lawn_corners_m[2][0] + \
            lawn_border_m, rel_lawn_corners_m[2][1] + lawn_border_m
        rel_arena_right_bottom_m = rel_lawn_corners_m[3][0] + \
            lawn_border_m, rel_lawn_corners_m[3][1] - lawn_border_m
        rel_arena_corners_m = np.float32(
            [rel_arena_left_bottom_m, rel_arena_left_top_m, rel_arena_right_top_m, rel_arena_right_bottom_m])

        # use reverse matrix lookup to find arena corners
        arena_corners_pc = []
        for p in rel_arena_corners_m:
            tgt_pt_px = translate_pixel_point(p, Q, dp=3)
            arena_corners_pc.append(tgt_pt_px)
            if debug:
                logger.debug('relative arena {0:<11}m => {1:<11}%'.format(
                    str(p), str(tgt_pt_px)))

        # convert cartesian camera arena corner percentages to non-cartesian pixels
        arena_corners_px_cart = arena_corners_pc * \
            np.array([img_width_px / 100, img_height_px / 100])
        arena_corners_px = [(round(corner_px_cart[0]), round(
            img_height_px - corner_px_cart[1])) for corner_px_cart in arena_corners_px_cart]

        if debug:
            for n in range(4):
                logger.debug('arena_corners_pc calib_percentages => arena corners pc: {}% => {}% => {}px {}'.format(
                    calib_percentages[n],
                    arena_corners_pc[n],
                    arena_corners_px[n],
                    ordering[n]
                )
                )

        # use absolute arena corners to calculate final matrix
        abs_arena_left_bottom_m = 0, 0
        abs_arena_left_top_m = 0, arena_length_m
        abs_arena_right_top_m = arena_width_m, arena_length_m
        abs_arena_right_bottom_m = arena_width_m, 0
        abs_arena_corners_m = np.float32(
            [abs_arena_left_bottom_m, abs_arena_left_top_m, abs_arena_right_top_m, abs_arena_right_bottom_m])

        # compute world_metres <<<=== image matrix (non-cartesian)
        H = find_coeffs(abs_arena_corners_m, arena_corners_px)

        # construct pixel mapping camera arena => top down arena image
        topdown_arena_corners_pc = [(0, 100), (0, 0), (100, 0), (100, 100)]
        topdown_arena_corners_px = [
            (x * img_width_px / 100, y * img_height_px / 100) for x, y in topdown_arena_corners_pc]
        # compute the camera <<<=== arena top-down matrix
        M = find_coeffs(topdown_arena_corners_px, arena_corners_px)

        if debug:
            logger.debug('arena width: {0:.2f}m arena length: {1:.2f}m arena border: {2:.2f}m'.format(
                arena_width_m,
                arena_length_m,
                lawn_border_m
            )
            )
            logger.debug('calibration zone width: {0:.2f}m zone length: {1:.2f}m arena border: {2:.2f}m'.format(
                calib_width_m,
                calib_length_m,
                lawn_border_m
            )
            )
            for n in range(4):
                logger.debug('calib metres => pixels: {}m => {}px {}'.format(
                    abs_arena_corners_m[n], arena_corners_px[n], ordering[n]))

        # compute the top-down matrix => camera inverse matrix
        # skimage requires this for its warpPerspective function
        N = np.linalg.inv(M)
        K = np.linalg.inv(H)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in matrices_from_quad_points: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    return M, N, H, K


def get_polygons_from_pc(
        polygon_pts_pc,
        arena_width_m,
        arena_length_m,
        growth_factor_pc,
        min_seg_length_pc,
        data_mapper,
        logger=None,
        debug=False
):
    dense_polygon_grown_pts_m = []
    img_polygon_pts_px = []
    try:
        # convert percentages to metres and close polygon
        polygon_pts_m = [(pt.x * arena_width_m / 100, pt.y *
                          arena_length_m / 100) for pt in polygon_pts_pc]
        # create shapely polygon
        polygon_m = Polygon(polygon_pts_m)
        # grow polygon by factor
        growth_factor = growth_factor_pc / 100
        growth_dist_m = growth_factor * arena_width_m

        # cap style square and join style mitre
        polygon_grown_m = polygon_m.buffer(growth_dist_m, cap_style=3, join_style=2)

        # restrict grown polygon to arena dimensions
        polygon_restricted_pts_m = [(max(min(pt[0], arena_width_m), 0), max(
            min(pt[1], arena_length_m), 0)) for pt in polygon_grown_m.exterior.coords]

        # step through pairs of points adding intermediates if necessary...
        min_seg_length_m = min_seg_length_pc * \
            max(arena_width_m, arena_length_m) / 100
        dense_polygon_grown_pts_m = []
        for line_start, line_finish in zip(polygon_restricted_pts_m, polygon_restricted_pts_m[1:]):
            extra_pts = geom_lib.get_evenly_spaced_points_on_line(
                *line_start, *line_finish, min_seg_length_m)
            dense_polygon_grown_pts_m.append(line_start)
            dense_polygon_grown_pts_m.extend(extra_pts)
        dense_polygon_grown_pts_m.append(line_finish)

        # split into x and y lists
        polygon_grown_pts_xm = [
            x for (x, _y) in list(dense_polygon_grown_pts_m)]
        polygon_grown_pts_ym = [
            y for (x, y) in list(dense_polygon_grown_pts_m)]

        # reverse transform metres => pixels
        img_cam_pts_px = data_mapper.reverse_coordinates(
            polygon_grown_pts_xm, polygon_grown_pts_ym)

        # restrict img_cam_pts to valid camera pixels
        # if x is -1 point could not be interpolated - so exclude
        valid_index = img_cam_pts_px[0] >= 0
        restricted_img_cam_pts_px = (
            img_cam_pts_px[0][valid_index], img_cam_pts_px[1][valid_index])

        # recombine, round, flatten and int
        img_polygon_pts_px = np.dstack((np.round(restricted_img_cam_pts_px[0]), np.round(
            restricted_img_cam_pts_px[1]))).flatten().astype(int).tolist()

        if debug and logger:
            logger.debug('polygon_pts_m: ' + str(polygon_pts_m))
            logger.debug('polygon_m: ' + str(polygon_m))
            logger.debug('polygon_grown_m: ' + str(polygon_grown_m))
            logger.debug('polygon_restricted_pts_m: ' +
                         str(polygon_restricted_pts_m))
            logger.debug('polygon_grown_pts_m x: ' +
                         str(polygon_grown_pts_xm) + ' y: ' + str(polygon_grown_pts_ym))
            logger.debug('img_cam_pts_px: ' + str(img_cam_pts_px))
            logger.debug('img_polygon_pts_px: ' + str(img_polygon_pts_px))
            logger.debug('restricted_img_polygon_pts_px: ' +
                         str(restricted_img_cam_pts_px))

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in get_polygons_from_pc: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    return dense_polygon_grown_pts_m, img_polygon_pts_px


def get_fence_mask_surface(
        img_width_px,
        img_height_px,
        polygon_pts_px,
        font,
        like_arr=None,
        debug=False,
        logger=None
):

    try:

        x_mid_px = img_width_px / 2
        y_mid_px = img_height_px / 2

        if like_arr is None:
            mask_img = Image.new('L', (img_width_px, img_height_px))
        else:
            mask_img = Image.new('L', (like_arr.shape[1], like_arr.shape[0]))

        draw_on_mask = ImageDraw.Draw(mask_img)

        draw_on_mask.polygon(polygon_pts_px, outline=200, fill=200)

        if debug:
            # circle  and number all points
            it = iter(polygon_pts_px)
            rad = 3
            for n, pt in enumerate(zip(it, it)):
                draw_on_mask.ellipse(
                    (pt[0] - rad, pt[1] - rad, pt[0] + rad, pt[1] + rad), fill=255)
                quadrant = 2 * (pt[0] < x_mid_px) + (pt[1] < y_mid_px)
                if n % 4 == 0:
                    if quadrant == 0:
                        draw_on_mask.text(
                            (pt[0] - 40, pt[1] - 40), str(n) + ' ' + str(quadrant), fill=255, font=font)
                    elif quadrant == 1:
                        draw_on_mask.text(
                            (pt[0] + 40, pt[1] + 40), str(n) + ' ' + str(quadrant), fill=255, font=font)
                    elif quadrant == 2:
                        draw_on_mask.text(
                            (pt[0] - 40, pt[1] + 40), str(n) + ' ' + str(quadrant), fill=255, font=font)
                    elif quadrant == 3:
                        draw_on_mask.text(
                            (pt[0] - 40, pt[1] + 40), str(n) + ' ' + str(quadrant), fill=255, font=font)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in get_fence_mask_surface: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    return mask_img


def find_coeffs(source_coords, target_coords):
    # find coefficients between 2 rectangles
    matrix = []
    for s, t in zip(source_coords, target_coords):
        matrix.append([t[0], t[1], 1, 0, 0, 0, -s[0] * t[0], -s[0] * t[1]])
        matrix.append([0, 0, 0, t[0], t[1], 1, -s[1] * t[0], -s[1] * t[1]])
    A = np.matrix(matrix, dtype=float)
    B = np.array(source_coords).reshape(8)
    res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
    res = np.array(res).reshape(8)
    res = np.append(res, 1.0).reshape(3, 3)
    return res


def translate_pixel_point(pt, matrix, dp=3, debug=False):
    dottable = ((pt[0],), (pt[1],), (1,))
    res = np.dot(matrix, dottable)
    if debug:
        print('translate_pixel_point numpy dot product:', res)
    res = res / res[2]
    if debug:
        print('translate_pixel_point numpy de-projected:', res)
    return (np.round(res[0][0], dp), np.round(res[1][0], dp))


def render_contour_hdr():
    return [
        'thumbnail',
        'ident',
        'x',
        'y',
        'span',
        'area',
        'isoscelicity',
        'solidity',
        'fitness',
        'confidence[%]'
    ]


def render_contour_row(proj, logger):

    try:

        thumb_tmplt = '''
            <div style="text-align: center;">
                <img src="data:image/jpeg;charset=utf-8;base64,{0}" alt="Thumbnail" />
            </div>'''

        meter_tmplt = '''
            <meter id="cont-widg-{0}"
               min="{1}" max="{2}"
               low="{3}" high="{4}" optimum="{5}"
               value="{6}" title="{7}">{7}
            </meter>
            '''
        _icon_tmplt = '''
            <img src="/icons/{0}.png" style="margin:auto;display:block;"/>
            '''

        html_row = [
            thumb_tmplt.format(proj.cont_img_b64),
            '{0}.{1}'.format(proj.ssid, proj.index),
            round(proj.cx, 2) if 'cx' in vars(
                proj) and proj.cx is not None else -1,
            round(proj.cy, 2) if 'cy' in vars(
                proj) and proj.cy is not None else -1,

            #                 id-suffix, min, max, low, high, optimum, value, title
            meter_tmplt.format('span', 0, 20, 7, 14, 20,
                               proj.span_score, proj.span_info),
            meter_tmplt.format('area', 0, 10, 3, 7, 10,
                               proj.area_score, proj.area_info),
            meter_tmplt.format('isoscelicity', 0, 20, 7, 14, 20,
                               proj.isoscelicity_score, proj.isoscelicity_info),
            meter_tmplt.format('solidity', 0, 20, 7, 14, 20,
                               proj.solidity_score, proj.solidity_info),
            meter_tmplt.format('fitness', 0, 20, 7, 14, 20,
                               proj.fitness_score, proj.fitness_info),
            meter_tmplt.format('conf', 0, 100, 33, 66, 80,
                               proj.conf_pc, '{0:.0f}%'.format(proj.conf_pc))
        ]

    except Exception as ex:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in Render Contour Row: ' +
                     str(ex) + 'on line: ' + str(err_line))

    return html_row


def get_contour_source_array(
    index,
    img_arr,
    fence_mask_array,
    vp,
    zoom_scale_factor,
    debug_image_level,
    tmp_folder_path,
    logger,
    pre_filter=True,
    post_close=True
):
    '''
        determine best binary array for mining contours
    '''
    try:
        if logger is not None:
            logger.info(
                'get_contour_source_array incoming arr: {0}'.format(img_arr.shape))

        if img_arr.shape == (0, 0):
            fence_masked_arr = None
        else:

            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                pre_img = Image.fromarray(img_arr)
                pre_img.convert('RGB').save(tmp_folder_path + '{0}-filters-incoming.jpg'.format(
                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            if pre_filter and constants.BLUR_SIGMA > 0:
                blurred_arr = filters.gaussian(
                    img_arr, sigma=constants.BLUR_SIGMA, preserve_range=True).astype(np.uint8)
                if logger is not None:
                    logger.info(
                        'get_contour_source_array blur pre-filter complete')
                if debug_image_level >= 4 or abs(debug_image_level) == 4:
                    post_img = Image.fromarray(blurred_arr)
                    post_img.convert('RGB').save(tmp_folder_path + '{0}-post-blur.jpg'.format(
                        index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
            else:
                blurred_arr = img_arr

            # sobel edge filter
            edge_filtered_arr = filters.sobel(blurred_arr)  # blurred_arr
            if logger is not None:
                logger.info(
                    'get_contour_source_array sobel edge detection complete')
            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                post_img = Image.fromarray(
                    (edge_filtered_arr * 255).astype(np.uint8))
                post_img.save(tmp_folder_path + '{0}-sobel-edge-detect.jpg'.format(
                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            contour_source_arr = edge_filtered_arr

            if post_close and constants.CLOSING_FOOTPRINT is not None:
                fp = constants.CLOSING_FOOTPRINT
                closed_edge_filtered_arr = closing(contour_source_arr, fp)
                contour_source_arr = closed_edge_filtered_arr
                if debug_image_level >= 4 or abs(debug_image_level) == 4:
                    post_img = Image.fromarray(
                        (closed_edge_filtered_arr * 255).astype(np.uint8))
                    post_img.save(tmp_folder_path + '{0}-closed-edge-detect.jpg'.format(
                        index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            if logger is not None:
                logger.info('get_contour_source_array gray image filtered')

            # mask beyond fence?
            if constants.FENCE_MASKING:
                try:
                    if vp.isnull:
                        if logger is not None:
                            logger.debug('get_contour_source_array fence masking zoom_scale_factor: {}'.format(
                                zoom_scale_factor)
                            )
                        if zoom_scale_factor > 1:
                            sub_samp_fence_arr = fence_mask_array[::
                                                                  zoom_scale_factor, ::zoom_scale_factor]
                            if logger is not None:
                                logger.debug('get_contour_source_array fence masking contour_source_arr.shape: {0} sub_samp_fence_arr: {1}'.format(
                                    contour_source_arr.shape,
                                    sub_samp_fence_arr.shape)
                                )
                            fence_masked_arr = contour_source_arr * sub_samp_fence_arr
                            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                                sub_samp_fence_img = Image.fromarray(
                                    sub_samp_fence_arr)
                                sub_samp_fence_img.save(tmp_folder_path + '{0}-sub_samp_fence.jpg'.format(
                                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
                        else:
                            fence_masked_arr = contour_source_arr * fence_mask_array  # full size
                    else:
                        fma = fence_mask_array[vp.slicer(fence_mask_array.shape)]
                        if logger is not None:
                            logger.debug('get_contour_source_array fence masking fence_mask_array: {} {}'.format(
                                contour_source_arr.shape, fma.shape)
                            )
                        fence_masked_arr = contour_source_arr * fma
                except ValueError:
                    err_line = sys.exc_info()[-1].tb_lineno
                    fence_masked_arr = contour_source_arr  # not needed
                    if logger is not None:
                        logger.warning(
                            'get_contour_source_array fence masking NOT applied {}'.format(err_line)
                        )

                except Exception as ex1:
                    fence_masked_arr = contour_source_arr  # error
                    if logger is not None:
                        err_line = sys.exc_info()[-1].tb_lineno
                        logger.error(
                            'get_contour_source_array fence masking error: {} on line {}'.format(
                                ex1,
                                err_line
                            )
                        )

                if logger is not None:
                    logger.info('get_contour_source_array fence_masked_arr shape {0} after fence masking'.format(
                        fence_masked_arr.shape
                    )
                    )
            else:
                fence_masked_arr = contour_source_arr

            try:
                fence_masked_img = Image.fromarray(
                    (fence_masked_arr * 255).astype(np.uint8), 'L')
                if debug_image_level >= 1 or abs(debug_image_level) == 1:
                    fence_masked_img.save(
                        tmp_folder_path + '{0}-pipeline-output.jpg'.format(index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY
                    )
            except Exception:
                pass

    except Exception as ex2:
        err_line = sys.exc_info()[-1].tb_lineno
        if logger is not None:
            err_msg = 'Error in get_contour_source_array: ' + \
                str(ex2) + ' on line: ' + str(err_line)
            logger.error(err_msg)
        else:
            print(err_msg)

    return fence_masked_arr


def rgb_to_gray(rgb):
    return np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140])


def warp_colour(img_arr, coord_map, preserve_scale=True, preserve_datatype=True):
    if coord_map is None:
        out_arr = img_arr
    else:
        if img_arr.ndim == 3:
            rows, cols, chans = img_arr.shape
            r_arr = tf.warp(
                img_arr[:, :, 0], inverse_map=coord_map, output_shape=(rows, cols))
            g_arr = tf.warp(
                img_arr[:, :, 1], inverse_map=coord_map, output_shape=(rows, cols))
            b_arr = tf.warp(
                img_arr[:, :, 2], inverse_map=coord_map, output_shape=(rows, cols))
            if chans == 4:
                a_arr = tf.warp(
                    img_arr[:, :, 3], inverse_map=coord_map, output_shape=(rows, cols))
                out_arr = np.dstack([r_arr, g_arr, b_arr, a_arr])
            else:
                out_arr = np.dstack([r_arr, g_arr, b_arr])
        else:
            # grayscale
            rows, cols = img_arr.shape
            out_arr = tf.warp(img_arr, inverse_map=coord_map,
                              output_shape=(rows, cols))
        if preserve_scale:
            out_arr = out_arr * np.iinfo(img_arr.dtype).max
        if preserve_datatype:
            out_arr = out_arr.astype(img_arr.dtype)
    return out_arr


def grid_intersections_lawn(lawn_width_m, lawn_length_m):

    x = np.arange(lawn_width_m)
    if x[-1] != lawn_width_m:
        x = np.append(x, lawn_width_m)
    y = np.arange(lawn_length_m)
    if y[-1] != lawn_length_m:
        y = np.append(y, lawn_length_m)
    xx, yy = np.meshgrid(x, y)
    c = np.stack([xx, yy], axis=2)
    return c


def grid_intersections_camera(lawn_width_m, lawn_length_m, border_m, mapper, logger=None, debug=False):
    if logger and debug:
        logger.debug('grid_intersections_camera: lawn width: {0}m lawn length: {1}m lawn border: {2}m {3}'.format(
            lawn_width_m, lawn_length_m, border_m, mapper.cache_key))
    c_m = grid_intersections_lawn(lawn_width_m, lawn_length_m)
    offset_c_m = c_m + (border_m, border_m)
    cam_c_px = mapper.reverse_coordinates(
        offset_c_m[:, :, 0], offset_c_m[:, :, 1])
    grid_px = np.stack([cam_c_px[0], cam_c_px[1]], axis=2)
    cam_c_px_ints = np.round(grid_px).astype(int)
    return cam_c_px_ints


def overlay_viewports(viewports, draw, shape, fill_col, font):
    for i, fp in enumerate(viewports):
        poly_lines = fp.xyxy_polylines(shape)
        for poly_line in poly_lines:
            draw.dashed_line(poly_line, dash=(4, 4), fill=fill_col, width=1)
        draw.text(fp.bottom_right[::-1] * np.array(shape)
                  [::-1] / 100, str(i), fill=fill_col, font=font)


def get_prospect_list(
    host,
    img_arr,
    zoom_scale_factor,
    viewport,
    debug_image_level,
    debug_level,
    logger,
    sid
):
    '''
        get list of lo-res prospect viewports
    '''
    try:

        # find contours
        timesheet = Timesheet('Get Prospect List')
        fence_mask_arr = np.asarray(host.fence_mask_img, bool)

        # Full Scene zoom in
        sub_shape = (int(img_arr.shape[0] / zoom_scale_factor),
                     int(img_arr.shape[1] / zoom_scale_factor))
        dbg_ratio = zoom_scale_factor / 2
        dbg_shape = (int(img_arr.shape[0] / dbg_ratio),
                     int(img_arr.shape[1] / dbg_ratio))

        # down-sample using scikit
        raw_img_arr = tf.resize(
            img_arr, sub_shape, preserve_range=True, anti_aliasing=True).astype(np.uint8)
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            dbg_img_arr = tf.resize(
                img_arr, dbg_shape, preserve_range=True, anti_aliasing=True)
            lores_img = Image.fromarray(
                dbg_img_arr.astype(np.uint8)).convert('RGB')
            lores_draw = DashedImageDraw(lores_img)

        # no filter or closing
        prep_img_arr = get_contour_source_array(
            sid,
            raw_img_arr,
            fence_mask_arr,
            viewport,
            zoom_scale_factor,
            debug_image_level,
            host.tmp_folder_path,
            logger,
            pre_filter=False,
            post_close=False
        )
        timesheet.add('full scene prepared')

        # find multiple contours in array
        prospect_cnts, margins, _edginess = viewport.find_contours(
            prep_img_arr, logger)
        if logger and debug_level > 0:
            logger.debug('Number of raw prospect contours: {0}'.format(
                len(prospect_cnts)))
        timesheet.add('lores contours found')

        # log point counts
        if logger and debug_level > 0:
            logger.debug('pre-filter prospect point counts: {0}'.format(
                [len(p) for p in prospect_cnts]))

        # best filtering methodology available
        # mid-range * threshold, or lower
        count_threshold = constants.CONTOUR_POINT_COUNT_THRESHOLD
        prospect_counts = [len(c) for c in prospect_cnts]
        mid_range_count = (max(prospect_counts, default=0) + min(prospect_counts, default=0)) * count_threshold
        min_pt_count = max(mid_range_count, constants.LORES_CONTOUR_MINIMUM_POINT_COUNT)
        filtered_prospect_contours = [c for c in prospect_cnts if len(c) > min_pt_count]
        
        # log point counts
        if logger and debug_level > 0:
            logger.debug('post-filter prospect point counts: {0}'.format(
                [len(p) for p in filtered_prospect_contours]))

        # log clipped prospects
        for q, p in enumerate(filtered_prospect_contours):
            if logger:
                logger.debug('clipped prospect?: {0} from {1}'.format(
                    any([m == 0 for m in margins[q]]), [int(m) for m in margins[q]]))
        if logger and debug_level > 0:
            logger.debug('Number of filtered prospect contours [len > {}]: {}'.format(
                min_pt_count, len(filtered_prospect_contours)))
        timesheet.add('prospects filtered')

        # convert prospect contours => universal viewports
        prosp_vps = []
        for pid, c in enumerate(filtered_prospect_contours):
            vp = Viewport.from_contour(c, sub_shape, index='{}-{}'.format(sid, pid))
            if vp.footprint is None or vp.footprint <= constants.MAXIMUM_VIEWPORT_FOOTPRINT:
                prosp_vps.append(vp)
                if logger and debug_level > 0:
                    logger.debug('Appending prospect viewport: fp {:.3f}%'.format(vp.footprint))
            else:
                if logger and debug_level > 0:
                    logger.debug('Not appending prospect viewport: fp {:.3f}%'.format(vp.footprint))
            
        if logger and debug_level > 0:
            logger.debug(
                'Number of prospect viewports: {}'.format(len(prosp_vps)))
        
        # annotate prospects lo-res
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            sm_font = ImageFont.truetype(host.font_path, 12)
            # overlay original prospects in blue
            overlay_viewports(prosp_vps, lores_draw,
                              dbg_shape, 'blue', sm_font)

        merge_adjacent_viewports(prosp_vps)
        if logger and debug_level > 0:
            logger.debug(
                'Number of merged prospect viewports: {}'.format(len(prosp_vps)))

        # annotate merged prospects lo-res
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            sm_font = ImageFont.truetype(host.font_path, 12)
            # overlay merged prospects in magenta
            overlay_viewports(prosp_vps, lores_draw,
                              dbg_shape, 'magenta', sm_font)

        timesheet.add('lores viewports merged')

        # enlarge qualifying viewports as lo-res prospecting is crude and clips
        prospect_vps = []
        for vp in prosp_vps:
            vp.resize(2.0)
            if (vp.footprint is None or vp.footprint <= constants.MAXIMUM_VIEWPORT_FOOTPRINT):
                if logger and debug_level > 0:
                    logger.debug('Qualifying prospect viewport: fp {:.3f}%'.format(vp.footprint))
                prospect_vps.append(vp)
                
        if logger and debug_level > 0:
            logger.debug(
                'Number of qualifying enlarged prospect viewports: {}'.format(len(prospect_vps)))
        timesheet.add('lores viewports filtered and enlarged')

        timesheet.add('lores prospect viewports obtained')

        viewport_count = len(prospect_vps)
        if logger is not None:
            logger.info(
                'get_prospect_list viewport count: {0}'.format(viewport_count))

        # annotate prospects lo-res
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            # overlay contours in orange
            cl.overlay_contours(filtered_prospect_contours, lores_draw,
                                (dbg_ratio, dbg_ratio), 'orange', sm_font)
            # overlay filtered prospects
            overlay_viewports(prospect_vps, lores_draw,
                              dbg_shape, 'yellow', sm_font)
            lores_img.save(host.tmp_folder_path + '{0}-lores.jpg'.format(sid))

        timesheet.add('lores prospect debug annotations')
        if logger and debug_level > 2:
            logger.debug(timesheet)

        return prospect_vps

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        err_msg = 'Error in get_prospect_list: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(err_msg)
        else:
            print(err_msg)


def probe_prospect_list(
    host,
    sid,
    vp_prospect_list,
    img_arr,
    debug_image_level,
    debug_level,
    logger
):
    '''
        loop through the incoming list of prospect viewports
        and find contours in the hi-res image
    '''
    timesheet = Timesheet2('Probe Prospect List')
    try:
        fence_mask_arr = np.asarray(host.fence_mask_img, bool)
        prospect_viewports = []
        for _pid, vp in enumerate(vp_prospect_list):
            timesheet.restart()
            sub_array = img_arr[vp.slicer(img_arr.shape)]
            vp.display_sub_array = sub_array

            # filter and closing
            prep_img_arr = get_contour_source_array(
                '{0}'.format(vp.index),
                sub_array,
                fence_mask_arr,
                vp,
                1,
                debug_image_level,
                host.tmp_folder_path,
                logger,
                pre_filter=True,
                post_close=True
            )
            vp.analysis_sub_array = prep_img_arr
            timesheet.add('contour source')

            local_contours, local_margins, local_edginess = vp.find_contours(
                prep_img_arr, logger)
            timesheet.add('find contours')

            if logger and debug_level > 0:
                logger.debug('local point counts: {0}'.format(
                    [len(c) for c in local_contours]))

            # best filtering methodology available
            # mid-range * threshold, or lower
            count_threshold = constants.CONTOUR_POINT_COUNT_THRESHOLD
            local_counts = [len(c) for c in local_contours]
            mid_range_count = (max(local_counts, default=0) + min(local_counts, default=0)) * count_threshold
            min_pt_count = max(mid_range_count, constants.HIRES_CONTOUR_MINIMUM_POINT_COUNT)
            filtered_local_contours = [c for c in local_contours if len(c) > min_pt_count]

            
            if logger and debug_level > 0:
                logger.debug('Number of filtered local contours [len > {}]: {}'.format(
                    min_pt_count, len(filtered_local_contours)))

            if logger and debug_level > 0:
                logger.debug('probe: {0} pre-de-dupe contour count: {1} {2}'.format(
                    vp.index, len(filtered_local_contours), [len(c) for c in filtered_local_contours]))

            # de-duplicate contour list in-place, by removing inner
            cl.dedupe_contour_list(
                filtered_local_contours, 0, logger=logger, debug=False)
            timesheet.add('contours de-duped')

            vp.local_contours = filtered_local_contours
            vp.local_margins = local_margins
            vp.local_edginess = local_edginess
            if logger and debug_level > 0:
                logger.debug('probe: {0} post-de-dupe contour count: {1} {2}'.format(
                    vp.index, len(filtered_local_contours), [len(c) for c in filtered_local_contours]))

            # global contour offset
            offset = np.array(vp.origin) * np.array(img_arr.shape) / 100

            # annotate
            if debug_image_level >= 2 or abs(debug_image_level) == 2:
                hires_img = Image.fromarray(img_arr).convert('RGB')
                hires_draw = ImageDraw.Draw(hires_img)
                sm_font = ImageFont.truetype(host.font_path, 12)
                # overlay global contours in orange
                global_contours = [c + offset for c in local_contours]
                cl.overlay_contours(
                    global_contours, hires_draw, (1, 1), 'orange', sm_font)
                hires_img.save(host.tmp_folder_path +
                               '{0}-hires.jpg'.format(vp.index))

            vp.local_projections = []
            for j, cont in enumerate(vp.local_contours):

                if len(cont) < constants.HIRES_CONTOUR_MINIMUM_POINT_COUNT:
                    # keep local projections synchronised with contours
                    vp.local_projections.append(None)
                else:
                    # we need global contours
                    global_cont = cont + offset

                    # apply sobel compensation
                    comp_cont = cl.sobel_compensation(global_cont)

                    # use mapper to undistort & unwarp contour to metres...
                    c_unwarped_undistorted = host.data_mapper.transform_contour(
                        comp_cont)  # yx order in, xy out

                    # add to log? will only log contours during excursions...
                    in_motion = host.drive['path'] is not None
                    exceeded_rnf_count = False
                    empty_buffer = len(host.contours_buffer) < 5
                    if constants.ENABLE_CONTOUR_LOGGING and ((in_motion and not exceeded_rnf_count and not host.drive_pause) or empty_buffer):
                        # assemble message into a single line - so it stays together
                        # we may be able to allow full size images as they are lo-res
                        msg = utilities.make_contour_entry(
                            sub_array,
                            prep_img_arr,
                            c_unwarped_undistorted,
                            '{0}'.format(vp.index),
                            j,
                            vp,
                            img_arr.shape,
                            True
                        )
                        if debug_level > 3:
                            logger.info('fcc contour single entry length: {0} bytes estimated buffer usage: {1:.2f} mB'.format(
                                len(msg),
                                len(msg) * host.contours_buffer.maxlen / 1000000
                            )
                            )
                        contour_logger = logging.getLogger('contours')
                        contour_logger.info(msg)
                        # add to buffer
                        host.contours_buffer.append(msg)

                    tgt = Projection(
                        '{0}-{1}'.format(vp.index, j),
                        j,
                        c_unwarped_undistorted,
                        hide_confidence=False,
                        logger=logger,
                        debug=(debug_level > 3)
                    )
                    tgt.assess(host.score_props)

                    # track thumbnails for contour analysis, and viewport for coarse location
                    tgt.cont_img_arr = sub_array
                    b64_buffer = BytesIO()
                    b64_img_raw = Image.fromarray(sub_array)
                    b64_img = b64_img_raw.resize((48, 48))
                    b64_img.convert('RGB').save(b64_buffer, format="JPEG")
                    b64_bytes = base64.b64encode(b64_buffer.getvalue())
                    tgt.cont_img_b64 = b64_bytes.decode()    # convert bytes to string

                    # pre-filter
                    if tgt.conf_pc > constants.SCORE_THRESHOLD:
                        vp.local_projections.append(tgt)
                    
                    if logger and debug_level > 1:
                        logger.debug(tgt.timesheet)

                    if ((debug_image_level >= 5 or abs(debug_image_level) == 5) or
                            ((debug_image_level >= 6 or abs(debug_image_level) == 6) and tgt.conf_pc > constants.SCORE_THRESHOLD)):

                        # initialise response
                        img_buf = io.BytesIO()

                        # overlay contour
                        disp_img = Image.fromarray(sub_array).convert('RGB')
                        disp_draw = ImageDraw.Draw(disp_img)
                        cl.overlay_contours(
                            [cont], disp_draw, (1, 1), 'orange', None)

                        plot_projection_img(
                            tgt, vp.index, prep_img_arr, disp_img, img_buf, logger)

                        # save debug plot image
                        plot_img = Image.open(img_buf)
                        plot_img.save(host.tmp_folder_path +
                                      '{0}-{1}-proj.jpg'.format(vp.index, j))

            prospect_viewports.append(deepcopy(vp))

        # assemble all global contours - at reduced point count
        all_big_contours = [
            c + offset for vp in vp_prospect_list if vp is not None for c in vp.local_contours]
        all_contours = [cl.reduce_contour_points(
            c, 24) for c in all_big_contours]
        if logger and debug_level > 0:
            logger.debug('Assembled {0} contour(s) into all_contours: {1}'.format(
                len(all_contours),
                [len(c) for c in all_contours]
            ))

        # assemble filtered global contour dictionary index i => len(c)
        filtered_contour_index = {i: len(c) for i, c in enumerate(
            all_big_contours) if len(c) > constants.HIRES_CONTOUR_MINIMUM_POINT_COUNT}

        # assemble projections
        filtered_projections = [
            p for vp in vp_prospect_list if vp is not None for p in vp.local_projections if p is not None]
        if logger and debug_level > 0:
            logger.debug('Assembled {0} projection(s) into filtered_projections: {1}'.format(
                len(filtered_projections),
                [f.conf_pc for f in filtered_projections]
            )
            )

        # sort projections
        filtered_projections.sort(key=lambda p: p.conf_pc, reverse=True)
        if logger and debug_level > 0:
            logger.debug('Sorted projection(s): {0}'.format(
                [f.conf_pc for f in filtered_projections]))

        # the highest scoring projection
        best_projection = filtered_projections[0] if len(
            filtered_projections) > 0 and filtered_projections[0].conf_pc > constants.SCORE_THRESHOLD else None

        if best_projection is not None and best_projection.valid:

            # let Pose apply offsetting
            pose = poses.Pose.from_tip_tail(
                best_projection.v1, best_projection.tail, best_projection.heading, ssid=sid)
            if logger and debug_level > 0:
                logger.debug('Best projection: {0}'.format(best_projection))
            if logger and debug_level > 0:
                logger.debug('Best projection pose from tip tail: {0}'.format(
                    pose.as_concise_str()))

        else:
            pose = None

        # check here for Null Pose, and use extrapolation if possible
        if (
            pose is None and
            constants.RNF_MITIGATION and
            host.snapshot_buffer.latest_extrap_pose() is not None
        ):
            pose = host.snapshot_buffer.latest_extrap_pose()
            host.extrapolation_incidents += 1
            logger.info('fcc RNF MITIGATION, Pose is None so using extrapolation {}... {} incidents'.format(
                host.snapshot_buffer.latest_extrap_pose().as_concise_str(),
                host.extrapolation_incidents)
            )

        if logger and debug_level >= 0:
            logger.debug(timesheet)

        return prospect_viewports, all_contours, filtered_contour_index, filtered_projections, pose

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        err_msg = 'Error in probe_prospect_list: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(err_msg)
        else:
            print(err_msg)


def lores_contours(analysis_array, zoom_scale_factor=4, min_pt_count=10, debug=False, logger=None):

    right_sizables = -1
    if debug and logger:
        logger.debug(
            'count lo-res contours incoming array shape: {}'.format(analysis_array.shape))
    # reduce analysis array resolution
    analysis_zarr = analysis_array[::zoom_scale_factor, ::zoom_scale_factor]
    if debug and logger:
        logger.debug(
            'count lo-res contours lo-res array shape: {}'.format(analysis_zarr.shape))
    # calculate perimeter
    perim = (analysis_zarr.shape[0] + analysis_zarr.shape[1]) * 2
    perim_80pc = perim * 0.8
    sobel_zarr = filters.sobel(analysis_zarr)
    # use simplest find contours
    max_intensity = np.max(sobel_zarr).astype(float)
    threshold = max_intensity / 2
    if threshold < constants.MINIMUM_CONTOUR_THRESHOLD:
        logger.debug('Lores Contours - skip as threshold is below constant minimum {:.3f} < {:.3f}'.format(
            threshold,
            constants.MINIMUM_CONTOUR_THRESHOLD
        )
        )
    else:
        conts = find_contours(sobel_zarr, threshold)
        if debug and logger:
            logger.debug(
                'count all lo-res contours: {} - {}'.format(len(conts), [len(c) for c in conts]))
        right_sizables = [len(c) for c in conts if len(
            c) > min_pt_count and len(c) < perim_80pc]
        right_sizable_count = sum(1 for c in right_sizables)
        if debug and logger:
            logger.debug(
                'count right sizable lo-res contours: {} - {}'.format(right_sizable_count, right_sizables))

    return right_sizables
