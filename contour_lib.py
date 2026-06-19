import sys
import random
import numpy as np
import cmath
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

def dedupe_contour_list(cnts, max_gap, idx=0, logger=None, debug=True):
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
        out_bbox_min = np.min(outer, axis=0)
        out_top, out_left = out_bbox_min
        out_bbox_max = np.max(outer, axis=0)
        out_bottom, out_right = out_bbox_max
        in_bbox_min = np.min(inner, axis=0)
        in_top, in_left = in_bbox_min
        in_bbox_max = np.max(inner, axis=0)
        in_bottom, in_right = in_bbox_max
        
        top_gap = int(in_top - out_top)
        left_gap = int(in_left - out_left)
        bottom_gap = int(out_bottom - in_bottom)
        right_gap = int(out_right - in_right)
        all_gaps = [top_gap, left_gap, bottom_gap, right_gap]
        if logger and debug:
            logger.debug('dedupe_contour_list all gaps: {} {}'.format(idx, all_gaps))
        small_gaps = [0 < g < max_gap for g in all_gaps]
        if logger and debug:
            logger.debug('dedupe_contour_list small gaps: {} {}'.format(idx, small_gaps))
        edges_contained = int(np.count_nonzero(small_gaps))
        if logger and debug:
            logger.debug('dedupe_contour_list edges contained: {} {}'.format(idx, edges_contained))
        contained = edges_contained >= 3
            
        if logger and debug:
            logger.debug(
                'dedupe_contour_list contained: {0}'.format(contained))
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
        dedupe_contour_list(cnts, max_gap, idx, logger, debug)


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

            # clustering - not essential but informative and expensive
            if debug:
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
    comp_cont = cont_in
    origin = np.min(cont_in, axis=0)
    height, width = np.ptp(cont_in, axis=0)
    if height > 0 and width > 0:
        scale = (cont_in - origin)
        comp_cont = (scale * [(height - shrink_by) /
                     height, (width - shrink_by) / width]) + [origin + shift_by]
    return comp_cont

def fitness(c_in, vertices):
    
    # reduce size?
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

def radius(c):
    height, width = np.ptp(c, axis=0)
    return (height + width) / 4

def area(c):
    # Shoelace formula implementation
    return 0.5 * np.abs(np.dot(c[:,0], np.roll(c[:,1], 1)) - 
                        np.dot(c[:,1], np.roll(c[:,0], 1)))

def perimeter(c):
    '''
        Calculates perimeter by summing distance between points.
        Assumes contour is shaped correctly (n, 2)
    '''
    
    # Calculate distances between sequential points (x2-x1)^2 + (y2-y1)^2
    # Shift array to align point i with point i+1
    diffs = np.diff(c, axis=0, append=c[0:1])
    
    # Euclidean distance: sqrt(dx^2 + dy^2)
    distances = np.sqrt(np.sum(diffs**2, axis=1))
    
    # Sum all distances
    return np.sum(distances)

def circularity(c, logger=None, debug=True):
    '''
        circularity defined as:
            how close perimeter to area ratio matches 2 / r
    '''
    r = radius(c)
    p = perimeter(c)
    a = area(c)
    two_over_radius = 2 / r
    par = p / a
    circ = two_over_radius / par 
    if debug and logger:
        logger.debug(
            ('circularity - radius: {:.3f} ' + 
            'area: {:.3f} ' +
            'perimeter: {:.3f} ' + 
            'two_over_radius: {:.3f} <==> ' +
            'par: {:.3f} => ' +
            'circularity: {:.3f}').format(r, a, p, two_over_radius, par, circ)
        )
    return circ
    
def edginess(c, threshold=1.0, min_pt_cnt=6):
    '''
        Calculate edginess as ratio:
            points on straight lines /
                total points
    '''
    pt_count = len(c)
    init_span = 2
    start_idx = 0
    finish_idx = init_span

    lines = []
    num_pts_on_lines = 0
    
    while finish_idx < pt_count:
        x = c[start_idx:finish_idx, 0]
        y = c[start_idx:finish_idx, 1]
    
        A = np.vstack([x, np.ones(len(x))]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
        
        line_vals = slope * x + intercept
        err = np.mean((y - line_vals) ** 2) * 1e6
        
        if err < threshold:
            finish_idx += 1
        else:
            # capture line?
            length = finish_idx - start_idx
            if length >= min_pt_cnt:
                lines.append(c[start_idx:finish_idx-1])
                num_pts_on_lines += length
            start_idx = finish_idx
            finish_idx += init_span

    # calculate edginess
    e = num_pts_on_lines / pt_count
    
    return e

def aspect_ratio(c):
    height, width = np.ptp(c, axis=0)
    return min(height, width) / max(height, width)

def radial_deviation(c, logger=None, debug=True):
    '''
        calculate standard deviation of radials
    '''

    # find centre
    cy, cx = (np.max(c, axis=0) + np.min(c, axis=0)) / 2

    radials = np.hypot(c[:, 0] - cy, c[:, 1] - cx)
    if debug and logger:
        logger.debug('radials: {}'.format(radials))
    sd = np.std(radials)
    if debug and logger:
        logger.debug('std dev: {}'.format(sd))
    score = sd / np.max(radials)
    if debug and logger:
        logger.debug('score: {}'.format(score))
    
    return score

def center_of_mass(c):
    # calculate center of mass of a closed polygon
    x = c[:,0]
    y = c[:,1]
    g = (x[:-1]*y[1:] - x[1:]*y[:-1])
    A = 0.5*g.sum()
    cx = ((x[:-1] + x[1:])*g).sum()
    cy = ((y[:-1] + y[1:])*g).sum()
    return 1./(6*A)*np.array([cx,cy])

def is_P_InSegment_P0P1(P, P0,P1):
    p0 = P0[0]- P[0], P0[1]- P[1]
    p1 = P1[0]- P[0], P1[1]- P[1]


    det = (p0[0]*p1[1] - p1[0]*p0[1])
    prod = (p0[0]*p1[0] + p0[1]*p1[1])
    
    return (det == 0 and prod < 0) or (p0[0] == 0 and p0[1] == 0) or (p1[0] == 0 and p1[1] == 0)


def is_inside_polygon(P: tuple, Vertices: list, validBorder=False) -> bool:


    sum_ = complex(0,0)


    for i in range(1, len(Vertices) + 1):
        v0, v1 = Vertices[i-1] , Vertices[i%len(Vertices)]


        if is_P_InSegment_P0P1(P,v0,v1):
            return validBorder


        sum_ += cmath.log( (complex(*v1) - complex(*P)) / (complex(*v0) - complex(*P)) )

    # return abs(sum_) > 1
    return sum_