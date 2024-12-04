import sys
import random
import numpy as np
from scipy import stats
from math import ceil

import geom_lib as gl


def reduce_contour_points(c_in, max_point_count, auto_step=False):
    '''
        take every nth point of contour to get desired count
    '''
    actual_point_count = len(c_in)
    if max_point_count > 0 and actual_point_count > max_point_count:
        if auto_step:
            step = ceil(actual_point_count / max_point_count)
            spaced_index = np.arange(0, actual_point_count - 1, step)
        else:
            spaced_index = np.linspace(
                0, actual_point_count - 1, num=max_point_count, dtype=int)
        c_spaced = c_in[spaced_index]
    else:
        c_spaced = c_in

    return c_spaced


def overlay_contours(contours, draw, scale, fill_col, font=None):
    for n, contour in enumerate(contours):
        # convert to flat list for plotting
        flat_points = list(
            np.flip(np.array(contour * [scale[1], scale[0]]).flatten().astype(int)))
        # sketch outline
        draw.point(flat_points, fill=fill_col)
        if font is not None:
            draw.text((max(flat_points[:2]) + random.randint(10, 100), max(flat_points[1::2]) + random.randint(10, 100)), '{0}:{1}'.format(
                n, len(contour)), fill=fill_col, font=font)

def dedupe_contour_list(cnts, idx=0, logger=None, debug=True):
    '''
        assumes cnts list is ordered outer to inner
        removes inner contour(1):
            if inside previous co-incident outer(0)
    '''
    if idx >= len(cnts) - 1:
        # finished
        if logger and debug:
            logger.debug('dedupe_contour_list finished idx: {0} cnts: {1}'.format(
                idx, [len(c) for c in cnts]))
        return
    else:
        if logger and debug:
            logger.debug('dedupe_contour_list idx: {0} cnts: {1}'.format(
                idx, [len(c) for c in cnts]))
        outer = cnts[idx]
        inner = cnts[idx + 1]
        outer_pnt_cnt = len(outer)
        inner_pnt_cnt = len(inner)
        if logger and debug:
            logger.debug('dedupe_contour_list outer: {0} inner: {1}'.format(
                outer_pnt_cnt, inner_pnt_cnt))
        # inner.centre between outer.limits
        inner_centroid = np.mean(inner, axis=0)
        if logger and debug:
            logger.debug(
                'dedupe_contour_list inner centroid: {0}'.format(inner_centroid))
        outer_centroid = np.mean(outer, axis=0)
        if logger and debug:
            logger.debug(
                'dedupe_contour_list outer centroid: {0}'.format(outer_centroid))
        coincidence_u = np.linalg.norm(inner_centroid - outer_centroid)
        if logger and debug:
            logger.debug(
                'dedupe_contour_list coincidence: {0:.2f} units'.format(coincidence_u))
        outer_diagonal_u = np.linalg.norm(
            np.max(outer, axis=0) - np.min(outer, axis=0))
        if logger and debug:
            logger.debug(
                'dedupe_contour_list outer diagonal: {0:.2f} units'.format(outer_diagonal_u))
        coincidence_ratio = coincidence_u / outer_diagonal_u
        if logger and debug:
            logger.debug(
                'dedupe_contour_list coincidence ratio: {0:.2f}'.format(coincidence_ratio))
        coincident = coincidence_ratio < 0.1
        if logger and debug:
            logger.debug(
                'dedupe_contour_list coincident: {0}'.format(coincident))
        bbox_min = np.min(outer, axis=0)
        bbox_max = np.max(outer, axis=0)
        contained = np.all((bbox_min < inner_centroid) &
                           (inner_centroid < bbox_max))
        if logger and debug:
            logger.debug(
                'dedupe_contour_list contained: {0}'.format(contained))
        # if coincident:
        if contained:
            if logger and debug:
                logger.debug(
                    'dedupe_contour_list removing: {0}'.format(len(cnts[idx + 1])))
            cnts.pop(idx + 1)
            # keep same pointer
        else:
            # advance pointer
            if logger and debug:
                logger.debug(
                    'dedupe_contour_list advancing pointer to: {0}'.format(idx + 1))
            idx += 1
        dedupe_contour_list(cnts, idx, logger, debug)


def morph_contour_to_polygon(contour, num_vertices, max_iterations=10, debug=True, logger=None):
    '''
        reduce number of vertices in contour to n
    '''
    morph_props = {}
    clusters = {}

    try:
        i = 1
        while len(contour) > num_vertices and i <= max_iterations:
            if debug and logger:
                logger.debug('loop c_out: {0}'.format(
                    np.round(contour, 2).tolist()))
            contour, morph_props = reduce(
                contour, clusters, debug=debug, logger=logger)
            morph_props['num_iterations'] = i
            i += 1
    except Exception as e:

        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in morph_contour_to_polygon: ' + \
            str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    return contour, morph_props


def reduce(c_in, clusters, debug=True, logger=None):
    '''
        reduce number of vertices in c_in by 1
    '''
    legal_edge_idxs = None
    intersections = None
    smallest_appendage_area_idx = central_edge_idx = -1
    num_pts = len(c_in)

    try:
        # first find all triplets of 3 edges, 4 points
        c2 = np.roll(c_in, -1, axis=0)
        c3 = np.roll(c_in, -2, axis=0)
        c4 = np.roll(c_in, -3, axis=0)
        if debug and logger:
            logger.debug('{}\n{}\n{}\n{}'.format(
                np.round(c_in, 2).tolist(),
                np.round(c2, 2).tolist(),
                np.round(c3, 2).tolist(),
                np.round(c4, 2).tolist()
            )
            )

        # find the centroid - it will be useful to calculate angle of the infill triangle
        centroid = np.mean(c_in, axis=0)

        # find the point where leading and trailing edges meet
        intersections = gl.line_intersect(c_in, c2, c3, c4)
        if debug and logger:
            logger.debug('intersections: {0}'.format(intersections))

        # find the midpoint of the central edge
        central_midpoints = np.mean([c2, c3], axis=0)
        if debug and logger:
            logger.debug('central_midpoints: {0}'.format(central_midpoints))

        # find the width of the proposed appendage
        appendage_area_width = np.linalg.norm(c3 - c2, axis=1)
        if debug and logger:
            logger.debug('appendage_area_width: {0}'.format(
                appendage_area_width))

        # find the height of the proposed appendage
        appendage_area_height = np.linalg.norm(
            intersections - central_midpoints, axis=1)
        if debug and logger:
            logger.debug('appendage_area_height: {0}'.format(
                appendage_area_height))

        # find the area of the reclaimed area rectangle
        appendage_area = appendage_area_width * appendage_area_height / 2
        if debug and logger:
            logger.debug('appendage_area: {0}'.format(
                np.round(appendage_area, 2)))

        # find index of smallest legal appendage area
        try:
            smallest_appendage_area_idx = np.nanargmin(appendage_area)
            smallest_appendage_area = appendage_area[smallest_appendage_area_idx]
            if debug and logger:
                logger.debug('smallest_appendage_area_idx: {0} area: {1}'.format(
                    smallest_appendage_area_idx, smallest_appendage_area))

            # central edge index is one beyond
            central_edge_idx = (smallest_appendage_area_idx + 1) % num_pts
            if debug and logger:
                logger.debug('central_edge_idx: {0}'.format(central_edge_idx))

            # move central edge start point to projected intersection
            c_in[central_edge_idx] = intersections[smallest_appendage_area_idx]
            if debug and logger:
                logger.debug('contour with moved point: {0}'.format(
                    np.round(c_in, 3).tolist()))

            # remove the central edge finish point
            c_in = np.delete(c_in, (central_edge_idx + 1) % num_pts, axis=0)
            if debug and logger:
                logger.debug('contour with deleted point: {0}'.format(
                    np.round(c_in, 3).tolist()))

            # add the area to one of the clusters of infills, keyed on angle
            midpoint = central_midpoints[smallest_appendage_area_idx]
            # numpy arctan2 takes a y, x vector
            midpoint_angle = np.rint(np.mod(np.rad2deg(np.arctan2(
                midpoint[1] - centroid[1], midpoint[0] - centroid[0]) - np.pi / 2), 360))  # 0..360 ccw
            if debug and logger:
                logger.debug(
                    'infill midpoint angle: {0}'.format(midpoint_angle))

            # check existing cluster keys to find nearest
            assigned = False
            if debug and logger:
                logger.debug('infill cluster keys: {0}'.format(
                    np.rint(list(clusters.keys()))))
            for k in list(clusters.keys()):
                if debug and logger:
                    logger.debug('infill checking midpoint: {0} against mean angle: {1}'.format(
                        midpoint_angle, k))
                angular_distance_to_midpoint = int(
                    abs(gl.diff_angles(k, midpoint_angle, fmt=1)))
                if debug and logger:
                    logger.debug('infill angular_distance_to_midpoint: {0}'.format(
                        angular_distance_to_midpoint))
                # angular distance is half sector bandpass
                if angular_distance_to_midpoint < 30 and not assigned:  # t degree cluster key sectors
                    # create new entry
                    new_angles = clusters[k][0] + [midpoint_angle]
                    new_areas = clusters[k][1] + [smallest_appendage_area]
                    # recalculate mean
                    new_angle_mean = stats.circmean(new_angles, high=360)
                    # add new entry
                    clusters[new_angle_mean] = (new_angles, new_areas)
                    # remove old entry
                    del clusters[k]
                    assigned = True
            if not assigned:
                # add new cluster
                clusters[midpoint_angle] = (
                    [midpoint_angle], [smallest_appendage_area])
                if debug and logger:
                    logger.debug(
                        'infill cluster new key added: {0}'.format(midpoint_angle))

        except ValueError:
            smallest_appendage_area_idx = central_edge_idx = -1
            if debug and logger:
                logger.warning('smallest_appendage_area - no areas qualify')

    except Exception as e:

        err_line = sys.exc_info()[-1].tb_lineno
        msg = 'Error in reduce: ' + str(e) + ' on line ' + str(err_line)
        if logger:
            logger.error(msg)
        else:
            print(msg)

    props_dict = {'legal_edge_idxs': legal_edge_idxs,
                  'intersections': intersections,
                  'appendage_area': appendage_area,
                  'central_edge_idx': central_edge_idx,
                  'clusters': clusters
                  }

    return c_in, props_dict


def sobel_compensation(cont_in, shrink_by=3, shift_by=2):
    '''
        compensate for sobel's offsetting and scaling
    '''
    origin = np.min(cont_in, axis=0)
    height, width = np.ptp(cont_in, axis=0)
    comp_cont = ((cont_in - origin) * [(height - shrink_by) /
                 height, (width - shrink_by) / width]) + [origin + shift_by]
    return comp_cont

def fitness(c_in, vertices):
    
    # reduce size for testing?
    c = reduce_contour_points(c_in, 99)
    
    centroid = np.mean(c, axis=0)
    
    dist_ratios = []
    
    # loop through the points in contour
    for p in c:
        # check each edge

        # measure perpendicular distance
        d1 = gl.distance_to_line(p[0], p[1], vertices[0][0], vertices[0][1], vertices[1][0], vertices[1][1])
        d2 = gl.distance_to_line(p[0], p[1], vertices[1][0], vertices[1][1], vertices[2][0], vertices[2][1])
        d3 = gl.distance_to_line(p[0], p[1], vertices[2][0], vertices[2][1], vertices[0][0], vertices[0][1])
        
        # measure distance to centroid
        dc = np.linalg.norm(p - centroid)
        
        # select closest edge...
        d = min(d1, d2, d3)
        
        max_dist = d + dc
        
        pt_fit = dc / max_dist
        
        dist_ratios.append(pt_fit)
        
    # calculate overall fitness
    fitness = np.mean(dist_ratios)
    
    return fitness
