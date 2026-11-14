import logging
import time
import io
import sys
import numpy as np
from PIL import Image, ImageDraw
from skimage import transform as tf
from skimage import filters
from skimage.morphology import closing
from skimage.measure import find_contours
from skimage.draw.draw import polygon
from shapely.geometry.polygon import Polygon
from shapely import affinity
from _collections import deque

import geom_lib as gl
import contour_lib as cl
import utilities as ut
from infill_sharpener import Projection
import constants
import poses
from viewport import Viewport, merge_adjacent_viewports
from diagram_lib import plot_projection_img
from dashed_image_draw import DashedImageDraw
from timesheet import Timesheet
from whittler import Whittler


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
                logger.debug('relative lawn {:<11}m => {:<11}%'.format(
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
                logger.debug('relative arena {:<11}m => {:<11}%'.format(
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
            logger.debug('arena width: {:.2f}m arena length: {:.2f}m arena border: {:.2f}m'.format(
                arena_width_m,
                arena_length_m,
                lawn_border_m
            )
            )
            logger.debug('calibration zone width: {:.2f}m zone length: {:.2f}m arena border: {:.2f}m'.format(
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
            extra_pts = gl.get_evenly_spaced_points_on_line(
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


def render_projection_row(proj, logger):

    try:

        thumb_tmplt = '''
            <div style="text-align: center;">
                <img src="data:image/jpeg;charset=utf-8;base64,{}" alt="Thumbnail" />
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
            '{}.{}'.format(proj.ssid, proj.index),
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
                               proj.conf_pc, '{:.0f}%'.format(proj.conf_pc))
        ]

    except Exception as ex:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in Render Projection Row: ' +
                     str(ex) + 'on line: ' + str(err_line))

    return html_row

def get_contour_source_array(
    host,
    index,
    img_arr,
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
                'get_contour_source_array incoming arr: {}'.format(img_arr.shape))

        if img_arr.shape == (0, 0):
            fence_masked_arr = None
        else:
            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                pre_img = Image.fromarray(img_arr)
                pre_img.convert('RGB').save(tmp_folder_path + '{}-filters-incoming.jpg'.format(
                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            if pre_filter and constants.BLUR_SIGMA > 0:
                blurred_arr = filters.gaussian(
                    img_arr, sigma=constants.BLUR_SIGMA, preserve_range=True).astype(np.uint8)
                if logger is not None:
                    logger.info(
                        'get_contour_source_array blur pre-filter complete')
                if debug_image_level >= 4 or abs(debug_image_level) == 4:
                    post_img = Image.fromarray(blurred_arr)
                    post_img.convert('RGB').save(tmp_folder_path + '{}-post-blur.jpg'.format(
                        index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)
            else:
                blurred_arr = img_arr

            # sobel edge filter
            edge_filtered_arr = filters.sobel(blurred_arr)
            if logger is not None:
                logger.info(
                    'get_contour_source_array sobel edge detection complete')
            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                post_img = Image.fromarray(
                    (edge_filtered_arr * 255).astype(np.uint8))
                post_img.save(tmp_folder_path + '{}-sobel-edge-detect.jpg'.format(
                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            contour_source_arr = edge_filtered_arr

            if post_close and constants.CLOSING_FOOTPRINT is not None:
                fp = constants.CLOSING_FOOTPRINT
                closed_edge_filtered_arr = closing(contour_source_arr, fp)
                contour_source_arr = closed_edge_filtered_arr
                if debug_image_level >= 4 or abs(debug_image_level) == 4:
                    post_img = Image.fromarray(
                        (closed_edge_filtered_arr * 255).astype(np.uint8))
                    post_img.save(tmp_folder_path + '{}-closed-edge-detect.jpg'.format(
                        index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

            if logger is not None:
                logger.info('get_contour_source_array gray image filtered')

            # mask beyond fence?
            if constants.FENCE_MASKING_MODE > 0:
                try:
                    if vp.isnull:
                        if logger is not None:
                            logger.debug('get_contour_source_array fence masking zoom_scale_factor: {}'.format(
                                zoom_scale_factor)
                            )
                        if zoom_scale_factor > 1:

                            # create drawing surface and draw the fence anti-polygons to mask

                            # prepare array
                            fence_masked_arr = (contour_source_arr * 255).astype(np.uint8)

                            # obtain image
                            # efficient zero-copy solution
                            contour_source_img = Image.frombuffer("L", fence_masked_arr.shape[::-1], fence_masked_arr, "raw", "L", 0, 1)

                            contour_source_img.readonly = False  # Forces Pillow to mutate the actual NumPy memory buffer

                            # obtain drawing surface on the image
                            contour_source_draw = ImageDraw.Draw(contour_source_img)

                            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                                contour_source_img.save(tmp_folder_path + '{}-zoomed-pre-fence-mask.jpg'.format(
                                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

                            # draw zoomed fence anti-polygons
                            zoomed_fence_polygon = affinity.scale(
                                host.fencezone_polygon,
                                xfact=1/zoom_scale_factor,
                                yfact=1/zoom_scale_factor,
                                origin=(0, 0)
                            )
                            # fill with a value that is visible but not detectable
                            draw_anti_polygons(contour_source_draw, zoomed_fence_polygon, fill_colour='#111111')

                            if debug_image_level >= 4 or abs(debug_image_level) == 4:
                                zm_fence_img = Image.fromarray(fence_masked_arr)
                                zm_fence_img.save(tmp_folder_path + '{}-zoomed-post-fence-mask.jpg'.format(
                                    index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY)

                        else:

                            fence_masked_arr = contour_source_arr # hi-res, masking performed later

                    else:

                        fence_masked_arr = contour_source_arr # initialise

                        if constants.FENCE_MASKING_MODE == 2:
                            # get the intersection of the viewport polygon and the fence polygon
                            img_width_px = host.config['optical.width']
                            img_height_px = host.config['optical.height']
                            img_shape = (img_height_px, img_width_px)
                            vp_polygon = vp.as_polygon(img_shape)

                            # use dark zone polygon to mask intruding viewport
                            dark_polygon = host.outer_darkzone_polygon
                            if dark_polygon.contains(vp_polygon):
                                if logger is not None:
                                    logger.debug('get_contour_source_array fence masking Dark Zone Contains Viewport - do nothing')
                            elif vp_polygon.intersects(dark_polygon):
                                if logger is not None:
                                    logger.debug('get_contour_source_array fence masking Viewport Intersects Dark Zone - calculating mask indices...')

                                # get the polygon for vp inside zone
                                itsx_polygon = dark_polygon.intersection(vp_polygon)
                                if logger is not None:
                                    logger.debug('get_contour_source_array fence masking itsx_polygon: {}'.format(
                                        itsx_polygon.geom_type))

                                # get the polygon for vp outside zone
                                diff_polygon = vp_polygon.difference(itsx_polygon)
                                if logger:
                                    logger.debug('get_contour_source_array fence masking diff_polygon: {}'.format(
                                        diff_polygon.geom_type))

                                # convert polygon to local-to-viewport
                                for poly in gl.yield_polygons(diff_polygon):
                                    diff_pts = poly.exterior.coords
                                    row_coords = [p[1] for p in diff_pts]
                                    col_coords = [p[0] for p in diff_pts]
                                    rr, cc = polygon(row_coords, col_coords, shape=img_shape)
                                    # get viewport origin as percentage of whole image
                                    vox = vp.origin[1]
                                    voy = vp.origin[0]
                                    # get viewport origin in global pixels
                                    vox_px = (vox * img_width_px / 100)
                                    voy_px = (voy * img_height_px / 100)
                                    # calculate local indices that will reference sub-array
                                    sub_arr_rows, sub_arr_cols = contour_source_arr.shape
                                    srr = np.clip(rr - voy_px, 0, sub_arr_rows - 1).astype(int)
                                    scc = np.clip(cc - vox_px, 0, sub_arr_cols - 1).astype(int)
                                    # mask with a value that is visible but not detectable
                                    fence_masked_arr[srr, scc] = 11/255
                        elif logger:
                            logger.debug('Viewport Does Not Intersect Dark Zone - do nothing')
                except ValueError as ve:
                    err_line = sys.exc_info()[-1].tb_lineno
                    fence_masked_arr = contour_source_arr  # not needed
                    if logger is not None:
                        logger.warning(
                            'get_contour_source_array {} on line {} fence masking NOT applied'.format(ve, err_line)
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
            else:
                fence_masked_arr = contour_source_arr

            try:
                if debug_image_level >= 1 or abs(debug_image_level) == 1:
                    fence_masked_img = Image.fromarray(fence_masked_arr)
                    fence_masked_img.save(
                        tmp_folder_path + '{}-pipeline-output.jpg'.format(index), optimize=True, quality=constants.DEBUG_IMAGE_QUALITY
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
        logger.debug('grid_intersections_camera: lawn width: {}m lawn length: {}m lawn border: {}m {}'.format(
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

        # Full Scene zoom in
        sub_shape = (int(img_arr.shape[0] / zoom_scale_factor),
                     int(img_arr.shape[1] / zoom_scale_factor))
        dbg_ratio = zoom_scale_factor / 2
        dbg_shape = (int(img_arr.shape[0] / dbg_ratio),
                     int(img_arr.shape[1] / dbg_ratio))

        # down-sample using skimage
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
            host,
            sid,
            raw_img_arr,
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
            logger.debug('Number of raw prospect contours: {}'.format(
                len(prospect_cnts)))
        timesheet.add('lores contours found')

        # log point counts
        if logger and debug_level > 0:
            logger.debug('pre-filter prospect point counts: {}'.format(
                [len(p) for p in prospect_cnts]))

        min_pt_count = constants.LORES_CONTOUR_MINIMUM_POINT_COUNT
        filtered_prospect_contours = [
            c for c in prospect_cnts if
                constants.LORES_CONTOUR_MAXIMUM_POINT_COUNT >= len(c) >= min_pt_count
        ]

        # log point counts
        if logger and debug_level > 0:
            logger.debug('post-filter prospect point counts: {}'.format(
                [len(p) for p in filtered_prospect_contours]))

        # log clipped prospects
        for q, p in enumerate(filtered_prospect_contours):
            if logger:
                logger.debug('clipped prospect?: {} from {}'.format(
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
            sm_font = ut.load_sans_serif_font(12)
            # overlay original prospects in blue
            overlay_viewports(prosp_vps, lores_draw,
                              dbg_shape, 'blue', sm_font)

        merge_adjacent_viewports(prosp_vps)
        if logger and debug_level > 0:
            logger.debug(
                'Number of merged prospect viewports: {}'.format(len(prosp_vps)))

        # annotate merged prospects lo-res
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            sm_font = ut.load_sans_serif_font(12)
            # overlay merged prospects in magenta
            overlay_viewports(prosp_vps, lores_draw,
                              dbg_shape, 'magenta', sm_font)

        timesheet.add('lores viewports merged')

        # enlarge qualifying viewports as lo-res prospecting is crude and clips
        prospect_vps = []
        for vp in prosp_vps:
            vp.resize(2.0)
            if logger and debug_level > 0:
                logger.debug(
                    'Checking prospect viewport footprint: fp {:.3f}% <= {:.3f}%'.format(
                        vp.footprint, constants.MAXIMUM_VIEWPORT_FOOTPRINT
                        )
                    )
            if vp.footprint is None or vp.footprint <= constants.MAXIMUM_VIEWPORT_FOOTPRINT:
                if logger and debug_level > 0:
                    logger.debug('Qualifying prospect viewport: footprint {:.3f}%'.format(vp.footprint))
                prospect_vps.append(vp)

        if logger and debug_level > 0:
            logger.debug(
                'Number of qualifying enlarged prospect viewports: {}'.format(len(prospect_vps)))
        timesheet.add('lores viewports filtered and enlarged')

        timesheet.add('lores prospect viewports obtained')

        viewport_count = len(prospect_vps)
        if logger is not None:
            logger.info(
                'get_prospect_list viewport count: {}'.format(viewport_count))

        # annotate prospects lo-res
        if debug_image_level >= 1 or abs(debug_image_level) == 1:
            # overlay contours in orange
            cl.overlay_contours(filtered_prospect_contours, lores_draw,
                                (dbg_ratio, dbg_ratio), 'orange', sm_font)
            # overlay filtered prospects
            overlay_viewports(prospect_vps, lores_draw,
                              dbg_shape, 'yellow', sm_font)
            lores_img.save(host.tmp_folder_path + '{}-lores.jpg'.format(sid))

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

def get_contours_from_viewport(host, vp, img_arr, debug_image_level, timesheet, logger):
    sub_array = img_arr[vp.slicer(img_arr.shape)].copy()
    vp.display_sub_array = sub_array

    # filter and closing
    prep_img_arr = get_contour_source_array(
        host,
        '{}'.format(vp.index),
        sub_array,
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

    local_contours, _local_margins, _local_edginess = vp.find_contours(
        prep_img_arr, logger)
    timesheet.add('find contours')
    return local_contours

def add_contour_to_log(host, img_arr, logger, j, ivp, c_unwarped_undistorted):
    in_motion = host.drive['path'] is not None
    empty_buffer = len(host.contours_buffer) < host.contours_buffer_min_len
    if constants.ENABLE_CONTOUR_LOGGING and ((in_motion and not host.drive_pause) or empty_buffer):
        # assemble message into a single line - so it stays together
        # we may be able to allow full size images as they are lo-res
        logger.debug('about to assemble contour entry...')
        cestart = time.time()
        msg, counts = ut.make_contour_entry(
            ivp.display_sub_array,
            ivp.analysis_sub_array,
            c_unwarped_undistorted,
            '{}'.format(ivp.index),
            j,
            ivp,
            img_arr.shape,
            True)
        logger.debug('contour entry assembled in {:.3f}secs'.format(time.time() - cestart))
        msg_length = len(msg)
        buf_max_len = host.contours_buffer.maxlen
        est_memory_reqd_mb = msg_length * buf_max_len / 1000000
        logger.info('contour buffer[{}] single entry length: {}{} bytes estimated  usage: {:.2f} mB'.format(
                buf_max_len,
                msg_length,
                counts,
                msg_length * buf_max_len / 1e6))
        if (buf_max_len > host.contours_buffer_min_len and
            len(host.contours_buffer) > 1 and
            est_memory_reqd_mb > constants.CONTOUR_LOGGING_BUFFER_CAP_MB):
            optimised_slot_count = int(constants.CONTOUR_LOGGING_BUFFER_CAP_MB * 1e6 // msg_length)
            logger.warning('contour buffer likely to exceed cap - reducing slots to {}...'.format(optimised_slot_count))
            new_buf_max_len = max(host.contours_buffer_min_len, optimised_slot_count)
            host.contours_buffer = deque(host.contours_buffer, new_buf_max_len)
            logger.info('new estimated contour buffer[{}] usage: {:.2f} mB'.format(
                    new_buf_max_len,
                    len(msg) * buf_max_len / 1e6))
        contour_logger = logging.getLogger('contours')
        contour_logger.info(msg)

        # add to buffer
        host.contours_buffer.append(msg)

def post_projection(host, img_arr, debug_level, logger, j, ivp, c_unwarped_undistorted):
    tgt = None
    try:
        # lookup the expected number of vertices and shape rotation
        target_num_vertices = host.config['mower.target_num_vertices']
        rotation_ccw_deg = host.config['mower.target_rotation_ccw_deg']
        tgt = Projection(
            '{}-{}'.format(ivp.index, j),
            j,
            c_unwarped_undistorted,
            target_num_vertices,
            -rotation_ccw_deg,
            hide_confidence=False,
            logger=logger,
            debug=(debug_level > 3)
        )
        tgt.assess(host.score_props)
        # track thumbnails for contour analysis, and viewport for coarse location
        sub_array = img_arr[ivp.slicer(img_arr.shape)].copy()
        tgt.cont_img_arr = sub_array
        tgt.cont_img_b64 = ut.convert_array_to_base64(sub_array, (48, 48))
        if tgt.conf_pc >= constants.SCORE_THRESHOLD:
            ivp.local_projections.append(tgt)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error posting projection: ' + str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)
    return tgt

def get_vp_from_contour_index(vp_prospect_list, ci, logger=None):
    '''
        |    vp0 (3)|    vp1(2) |    vp2(1) |
        | c0 c1 c2      c3 c4        c6     |
    '''
    try:
        vp_idx = 0
        vp = vp_prospect_list[vp_idx]
        sum_of_contours = len(vp.local_contours)
        while ci >= sum_of_contours:
            vp_idx += 1
            vp = vp_prospect_list[vp_idx]
            sum_of_contours += len(vp.local_contours)
    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error looking up index: ' + str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    return vp

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
    timesheet = Timesheet('Probe Prospect List')

    prospect_viewports = vp_prospect_list
    filtered_projections = []
    pose = None

    whittler = Whittler()

    try:

        for vp in vp_prospect_list:
            vp.local_projections = [] # clear in anticipation

            vp.local_contours = get_contours_from_viewport(
                host,
                vp,
                img_arr,
                debug_image_level,
                timesheet,
                logger
            )

            if logger and debug_level > 0:
                logger.debug('Number of contours found {} Point Counts: {}'.format(
                    len(vp.local_contours), [len(c) for c in vp.local_contours]))

            # Sift contours using basic tools, before Whittling

            # best filtering methodology
            min_pt_count = constants.HIRES_CONTOUR_MINIMUM_POINT_COUNT
            # update list in-place
            vp.local_contours[:] = [c for c in vp.local_contours if len(c) > min_pt_count]

            # de-duplicate contour list in-place, by removing inner
            cl.dedupe_contour_list(vp.local_contours, constants.CONTOUR_DEDUPE_MAX_GAP, 0, logger=logger, debug=False)

        timesheet.add('de-duped sifted contours posted')

        # assemble all global contours
        vp_offset_mult = np.array(img_arr.shape) / 100
        global_contours = [
             c + (vp.origin * vp_offset_mult) for vp in vp_prospect_list if vp is not None for c in vp.local_contours]
        timesheet.add('global contours assembled')

        # annotate
        if debug_image_level >= 2 or abs(debug_image_level) == 2:
            hires_img = Image.fromarray(img_arr).convert('RGB')
            hires_draw = ImageDraw.Draw(hires_img)
            sm_font = ut.load_sans_serif_font(12)
            # overlay global contours in orange
            cl.overlay_contours(
                global_contours, hires_draw, (1, 1), 'orange', sm_font)
            hires_img.save(host.tmp_folder_path + 'hires.jpg')

        if logger and debug_level > 0:
            logger.debug('Number of filtered global contours: {} Point Counts: {}'.format(
                len(global_contours), [len(c) for c in global_contours]))

        whittler.process(global_contours, img_arr)
        if logger: logger.debug('\n' + str(whittler) + '\n')
        timesheet.add('contours whittled')

        # complete further processing on accepted whittled contours only
        for j, ci in enumerate(whittler.accepted_index):

            cont = global_contours[ci]

            # identify viewport
            ivp = get_vp_from_contour_index(vp_prospect_list, ci)

            # apply sobel compensation
            comp_cont = cl.sobel_compensation(cont)

            # use mapper to undistort & unwarp contour to metres...
            c_unwarped_undistorted = host.data_mapper.transform_contour(
                comp_cont)  # y,x order in, x,y out

            # add to log? will only log contours during excursions...
            add_contour_to_log(host, img_arr, logger, j, ivp, c_unwarped_undistorted)

            # create and post projection on viewport
            proj = post_projection(host, img_arr, debug_level, logger, j, ivp, c_unwarped_undistorted)

            if logger and debug_level > 0:
                logger.debug(str(proj.timesheet))

            # assemble projections - without pre-filtering
            filtered_projections.append(proj)

            if ((debug_image_level >= 5 or abs(debug_image_level) == 5) or
                    ((debug_image_level >= 6 or abs(debug_image_level) == 6) and
                        proj.conf_pc > constants.SCORE_THRESHOLD)):

                # initialise response
                img_buf = io.BytesIO()

                # overlay contour
                disp_img = Image.fromarray(ivp.display_sub_array).convert('RGB')
                disp_draw = ImageDraw.Draw(disp_img)
                cl.overlay_contours(
                    ivp.local_contours, disp_draw, (1, 1), 'orange', None)

                plot_projection_img(
                    proj, ivp.index, ivp.analysis_sub_array, disp_img, img_buf, logger)

                # save debug plot image
                plot_img = Image.open(img_buf)
                plot_img.save(host.tmp_folder_path +
                              '{}-{}-proj.jpg'.format(ivp.index, j))


        timesheet.add('{} projection(s) assembled'.format(len(whittler.accepted_index)))

        # sort projections
        filtered_projections.sort(key=lambda p: p.conf_pc, reverse=True)
        if logger and debug_level > 0:
            logger.debug('Sorted projection(s): {}'.format(
                [f.conf_pc for f in filtered_projections]))

        timesheet.add('projections sorted')

        # the highest scoring projection
        best_projection = filtered_projections[0] if len(
            filtered_projections) > 0 and filtered_projections[0].conf_pc > constants.SCORE_THRESHOLD else None

        timesheet.add('best projection identified')

        if best_projection is not None and best_projection.valid:

            # let Pose apply offsetting
            pose = poses.Pose.from_tip_tail(
                best_projection.tip, best_projection.tail, ssid=sid)
            if logger and debug_level > 0:
                logger.debug('Best projection: {}'.format(best_projection))
            if logger and debug_level > 0:
                logger.debug('Best projection pose from tip tail: {}'.format(
                    pose.as_concise_str()))

        else:
            pose = None

        timesheet.add('pose calculated')

        # check here for Null Pose, and use extrapolation if possible
        if (
            pose is None and
            constants.RNF_MITIGATION and
            host.snapshot_buffer.latest_extrap_pose() is not None
        ):
            pose = host.snapshot_buffer.latest_extrap_pose()
            host.extrapolation_incidents += 1
            logger.info('RNF MITIGATION, Pose is None so using extrapolation {}... {} incidents'.format(
                host.snapshot_buffer.latest_extrap_pose().as_concise_str(),
                host.extrapolation_incidents)
            )

        timesheet.add('extrapolation considered')

        if logger and debug_level >= 0:
            logger.debug(timesheet)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        err_msg = 'Error in probe_prospect_list: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(err_msg)
        else:
            print(err_msg)

    return prospect_viewports, global_contours, filtered_projections, pose, whittler

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
    min_intensity = np.min(sobel_zarr).astype(float)
    max_intensity = np.max(sobel_zarr).astype(float)
    threshold = (min_intensity + max_intensity) / 2
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

def draw_anti_polygons(img_draw, polygon, fill_colour='black', debug=False, logger=None):
    try:
        if debug:
            all_pts = list(polygon.exterior.coords)
            img_draw.polygon(all_pts, outline='white', width=2)
        img_width_px, img_height_px = img_draw.im.size
        anti_polygons = gl.make_antipolygons(polygon, img_width_px, img_height_px)
        for anti_polygon in anti_polygons:
            for pure_poly in gl.yield_polygons(anti_polygon):
                poly_pts = list(pure_poly.exterior.coords)
                img_draw.polygon(poly_pts, fill=fill_colour, width=1)
    except Exception as apx:
        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in anti-polygon overlay: {} on line {}'.format(apx, err_line)
        if logger:
            logger.log_error(msg)
        else:
            print(msg)
