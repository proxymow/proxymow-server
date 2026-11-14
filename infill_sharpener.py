import sys
import time
from datetime import datetime
import numpy as np
from math import degrees
import pprint

import constants
import geom_lib as gl
import contour_lib as cl
from resourcesheet import Timesheet
import utilities

class Projection:
    '''
        represents the projected vertices of a polygonal target
        derived from infill sharpening
    '''

    def __init__(
            self,
            ssid,
            index,
            c_raw_in,
            num_vertices,
            rotation_ccw_deg,
            hide_confidence=False,
            logger=None,
            debug=False
    ):
        '''
            constructor
        '''
        self.start_time_secs = time.time()
        self.elapsed_secs = -1
        self.timesheet = Timesheet('Infill-Sharpener')
        self.ssid = ssid
        self.index = index
        self.c_raw_in = c_raw_in
        self.num_vertices = num_vertices
        self.rotation_ccw_deg = rotation_ccw_deg
        self.hide_confidence = hide_confidence
        self.logger = logger
        self.debug = debug
        self.area = 0.0
        self.ch_area = 0.0
        self.span = 0
        self.isoscelicity = 0.0
        self.solidity = 0.0
        self.fitness = 0.0
        self.edginess = 0.0
        self.heading = -1
        self.pyramid = '[]'
        self.side_lengths = []
        self.conf_pc = None
        self.cx = self.cy = self.tip = self.tail = self.heading = None
        self.valid = True
        self.mem_footprint = -1

        try:
            num_pts = len(c_raw_in)
            if num_pts < 3:
                if logger:
                    logger.warning(
                        'Invalid target contour - Incoming Points {} < 3'.format(num_pts))
                raise ValueError('Invalid target contour')
            if debug and logger:
                logger.debug(
                    'target incoming contour point count: {}'.format(num_pts))
            self.timesheet.add('points counted')

            # incoming bounding-box centre
            self.bbcx, self.bbcy = np.min(
                c_raw_in, axis=0) + (np.ptp(c_raw_in, axis=0) / 2)
            if debug and logger:
                logger.debug('bounding box centre: ({:.2f}, {:.2f})'.format(
                    self.bbcx, self.bbcy))

            # incoming aspect
            height, width = np.ptp(c_raw_in, axis=0)
            if height == 0 or width == 0:
                if logger:
                    logger.warning(
                        'Invalid target contour - Zero Footprint')
                raise ValueError('Invalid target contour')

            self.aspect = min(height, width) / (max(height, width))
            if debug and logger:
                logger.debug('aspect {:.2f}'.format(self.aspect))

            # evaluate centroid
            centroid = np.mean(c_raw_in, axis=0)
            self.centroid_x, self.centroid_y = centroid
            self.timesheet.add('centroid calculated')

            # calculate perimeter
            self.perimeter = cl.perimeter(c_raw_in)
            self.timesheet.add('perimeter calculated')


            # convex hull
            '''
                Indices of points forming the vertices of the convex hull.
                For 2-D convex hulls, the vertices are in counterclockwise order.
                For other dimensions, they are in input order
            '''
            ch_obj = gl.ConvexHull(c_raw_in)
            num_pts = len(ch_obj.vertices)
            if debug and logger:
                logger.debug(
                    'convex hull vertex indices: {}'.format(ch_obj.vertices))
            self.c_ch = c_raw_in[ch_obj.vertices]
            if debug and logger:
                logger.debug('{} convex hull points: {}'.format(
                    num_pts, np.round(self.c_ch, 3).tolist()))
            self.timesheet.add('convex hull')

            # hull area
            self.ch_area = ch_obj.volume
            if debug and logger:
                logger.debug('ch area {:.2f}'.format(self.ch_area))
            self.timesheet.add('hull area calculated')

            # unidentified vertices
            morph_debug = debug and constants.DEBUG_LOCATE_LEVEL >= 4 # verbose
            vertices, morph_props = cl.morph_contour_to_polygon(
                self.c_ch, self.num_vertices, max_iterations=255, debug=morph_debug, logger=logger)
            self.pyramid = '{}|{}|{}'.format(
                len(c_raw_in),
                len(self.c_ch),
                len(vertices)
            )
            if 'clusters' in morph_props:
                morph_props_clusters = morph_props['clusters']
            else:
                if debug and logger:
                    logger.warning('no clusters dict in morph_props')
                morph_props_clusters = {}
            cluster_densities = {int(k): round(float(1000 * sum(areas) / len(areas)), 3)
                                 for (k, (_, areas)) in morph_props_clusters.items()}
            self.cluster_info = pprint.pformat(cluster_densities)
            massive_cluster_count = len(
                [cd for cd in cluster_densities.values() if cd > 3.0])
            num_clusters = len(
                [cd for cd in cluster_densities.values() if cd > 0.04])
            self.clusters = num_clusters if massive_cluster_count == 0 else 0
            if debug and logger:
                logger.debug(pprint.pformat(morph_props))
                logger.debug('cluster_info: {}'.format(self.cluster_info))
                logger.debug('clusters: {}'.format(self.clusters))
            self.timesheet.add('morph to polygon')

            # derive an index for the shortest side
            vertices_1 = np.roll(vertices, 1, axis=0)
            self.side_lengths = np.linalg.norm(vertices_1 - vertices, axis=1)
            if debug and logger:
                logger.debug('vertices: {}'.format(vertices))
                logger.debug('side lengths: {}m'.format(
                    np.round(self.side_lengths, 3)))

            # side index
            shortest_side_index = np.argmin(self.side_lengths)

            if self.num_vertices == 3:
                self.v1, self.v2, self.v3 = np.roll(vertices, 2 - shortest_side_index, axis=0)

                # universal tip
                tip = self.v1

                # hide
                self.v4 = None

            else:
                self.v1, self.v2, self.v3, self.v4 = np.roll(vertices, -shortest_side_index, axis=0)

                # universal tip
                tip = np.mean((self.v1, self.v4), axis=0)

            # universal tail
            tail = np.mean((self.v2, self.v3), axis=0)

            # reverse the target shape rotation
            #     calculate the centre (midpoint)
            centre = np.mean([tip, tail], axis=0)

            #     shift points to the origin
            shifted = [tip, tail] - centre

            # rotate
            rotated_shifted = gl.rotate_points(shifted, self.rotation_ccw_deg)

            # shift back to the original centre
            final_points = rotated_shifted + centre

            self.tip, self.tail = final_points

            if self.num_vertices == 3:
                # assess fit of original contour to triangle
                self.fitness = cl.fitness(c_raw_in, [self.v1, self.v2, self.v3])
            else:
                self.fitness = cl.fitness(c_raw_in, [self.v1, self.v2, self.v3, self.v4])
            self.timesheet.add('fitness')

            # publish contour not approximation
            self.contour = c_raw_in  # self.c_approx

            if debug and logger:
                logger.debug('tip: ({:.2f}, {:.2f})'.format(
                    self.tip[1], self.tip[0]))
                logger.debug('tail: ({:.2f}, {:.2f})'.format(
                    self.tail[1], self.tail[0]))

            # evaluate centre
            self.cx, self.cy = np.mean([self.tip, self.tail], axis=0)
            if debug and logger:
                logger.debug(
                    'simple centre: ({:.2f}, {:.2f})'.format(self.cx, self.cy))

            # calculate span
            self.span = np.linalg.norm(self.tail - self.tip)

            # evaluate heading
            self.heading = gl.get_angle_between_cartesian_points(
                *self.tail, *self.tip)
            if debug and logger:
                logger.debug('heading: {:.0f} degrees'.format(
                    degrees(self.heading)))

            self.timesheet.add('tip/tail/centres')

            if self.num_vertices == 3:
                self.isoscelicity = gl.polygon_isoscelicity(
                    [self.v1, self.v2, self.v3])
            else:
                self.isoscelicity = gl.polygon_isoscelicity(
                    [self.v1, self.v2, self.v3, self.v4])

            self.timesheet.add('isoscelicity')

            self.area = gl.triangle_area(self.v1, self.v2, self.v3)
            self.solidity = self.ch_area / self.area

            self.timesheet.add('solidity')

            # calculate elapsed time
            self.elapsed_secs = time.time() - self.start_time_secs

            # calculate memory footprint
            self.mem_footprint = utilities.getsize(self)

        except ValueError as vex:
            self.valid = False
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Warning target constructor incomplete: ' + \
                str(vex) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.warning(msg)

        except Exception as ex:
            self.valid = False
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in target constructor: ' + \
                str(ex) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)

    def __repr__(self):
        tmplt = 'Infill Sharpen {}.{}\t\t{}\n'
        tmplt += 'pyramid: {}\tsides: {}\n'
        tmplt += 'clusters: {}\n'
        tmplt += 'area: {:.3f}\t\tspan: {:.3f}\t\t\theading: {} degrees\n'
        tmplt += 'isoscelicity: {:.3f}\tsolidity: {:.3f}\tfitness: {:.3f}\n'
        tmplt += '{} ({}%)\tvalid: {}\tin {:.3f}secs using {:.3f}Mb'
        result = tmplt.format(
            self.ssid,
            self.index,
            datetime.fromtimestamp(self.start_time_secs).strftime(
                "%Y-%m-%d %H:%M:%S"),
            self.pyramid,
            np.round(self.side_lengths, 3),
            self.cluster_info,
            self.area,
            self.span,
            round(degrees(self.heading)
                  ) if self.valid and self.heading is not None else 'None',
            self.isoscelicity,
            self.solidity,
            self.fitness,
            self.assessment(True).replace('&harr;', '~'),
            self.conf_pc,
            self.valid,
            self.elapsed_secs,
            self.mem_footprint/1e6)
        return result

    def assess(self, score_props={}):

        try:
            self.max_score_product = np.prod(
                [sp[3] for sp in score_props.values() if sp[3] > 0])
            self.max_score_sum = sum(
                [sp[3] for sp in score_props.values() if sp[3] > 0])
            if self.logger:
                self.logger.info('Target Assess max_score_product: {} max_score_sum: {}'.format(
                    self.max_score_product,
                    self.max_score_sum
                    )
                )
            # scores ---

            # solidity
            key = 'solidity'
            if key in score_props and key in vars(self):

                self.solidity_score = self.get_score(
                    key, score_props, self.solidity)
                lower_scoring_range, expected, upper_scoring_range, weighting = score_props[
                    key]
                self.solidity_info = 'hull {:.3f}/tri {:.3f} = {:.3f} &harr; {:.2f} +{:.2f}/-{:.2f} scoring {}/{}'.format(
                    self.ch_area,
                    self.area,
                    self.solidity,
                    expected,
                    upper_scoring_range,
                    lower_scoring_range,
                    self.solidity_score,
                    weighting
                )
            else:
                self.solidity_score = 1
                self.solidity_info = 'unscored'

            # span
            key = 'span'
            if key in score_props and key in vars(self):
                self.span_score = self.get_score(key, score_props, self.span)
                lower_scoring_range, expected, upper_scoring_range, weighting = score_props[
                    key]
                self.span_info = '{:.3f} &harr; {:.3f} +{:.2f}/-{:.2f} scoring {}/{}'.format(
                    self.span,
                    expected,
                    upper_scoring_range,
                    lower_scoring_range,
                    self.span_score,
                    weighting
                )
            else:
                self.span_score = 1
                self.span_info = 'unscored'

            # area
            key = 'area'
            if key in score_props and key in vars(self):
                self.area_score = self.get_score(key, score_props, self.area)
                lower_scoring_range, expected, upper_scoring_range, weighting = score_props[
                    key]
                self.area_info = '{:.3f} &harr; {:.3f} +{:.2f}/-{:.2f} scoring {}/{}'.format(
                    self.area,
                    expected,
                    upper_scoring_range,
                    lower_scoring_range,
                    self.area_score,
                    weighting
                )
            else:
                self.area_score = 1
                self.area_info = 'unscored'

            # isoscelicity
            key = 'isoscelicity'
            if key in score_props and key in vars(self):
                self.isoscelicity_score = self.get_score(
                    key, score_props, self.isoscelicity)
                lower_scoring_range, expected, upper_scoring_range, weighting = score_props[
                    key]
                self.isoscelicity_info = '{:.3f} &harr; {:.3f} +{:.2f}/-{:.2f} scoring {}/{}'.format(
                    self.isoscelicity,
                    expected,
                    upper_scoring_range,
                    lower_scoring_range,
                    self.isoscelicity_score,
                    weighting
                )
            else:
                self.isoscelicity_score = 1
                self.isoscelicity_info = 'unscored'

            # fitness
            key = 'fitness'
            if key in score_props and key in vars(self):
                self.fitness_score = self.get_score(
                    key, score_props, self.fitness)
                lower_scoring_range, expected, upper_scoring_range, weighting = score_props[
                    key]
                self.fitness_info = '{:.3f} &harr; {:.3f} +{:.2f}/-{:.2f} scoring {}/{}'.format(
                    self.fitness,
                    expected,
                    upper_scoring_range,
                    lower_scoring_range,
                    self.fitness_score,
                    weighting
                )
            else:
                self.fitness_score = 1
                self.fitness_info = 'unscored'

            # score sums and products
            # convert score product to percentage confidence
            self.score_product = int((self.span_score if score_props['span'][3] > 0 else 1) *
                                     (self.area_score if score_props['area'][3] > 0 else 1) *
                                     (self.isoscelicity_score if score_props['isoscelicity'][3] > 0 else 1) *
                                     (self.solidity_score if score_props['solidity'][3] > 0 else 1) *
                                     (self.fitness_score if score_props['fitness'][3] > 0 else 1)
                                     )
            prod_conf_pc = round(self.score_product /
                                 self.max_score_product * 100, 2)

            # convert score sum to percentage confidence
            self.score_sum = self.span_score + self.area_score + \
                self.isoscelicity_score + self.solidity_score + self.fitness_score
            sum_conf_pc = round((self.score_sum / self.max_score_sum) * 100)

            # combine sign(product) * sum for overall confidence
            self.conf_pc = min(sum_conf_pc, 100) if prod_conf_pc > 0 else 0

            if self.logger:
                self.logger.info('Target Assess SP:{} + AR:{} + SD:{} + IS:{} + FT:{} = {}/{} = {}%'.format(
                    self.span_score,
                    self.area_score,
                    self.solidity_score,
                    self.isoscelicity_score,
                    self.fitness_score,
                    self.score_sum,
                    self.max_score_sum,
                    self.conf_pc
                    )
                )
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error('Error in infill sharpener assess: ' +
                              str(e) + ' on line ' + str(err_line))
            self.score_product = 0
            self.score_sum = 0
            self.conf_pc = 0

    def assessment(self, verbose=False):
        sub_total = self.span_score + self.area_score + \
            self.isoscelicity_score + self.solidity_score + self.fitness_score
        if verbose:
            result = 'span: {}\narea: {}\nisoscelicity: {}\nsolidity: {}\nfitness:{}\nsub-total: {:.0f}/{:.0f} {:.0f}%'.format(
                self.span_info,
                self.area_info,
                self.isoscelicity_info,
                self.solidity_info,
                self.fitness_info,
                sub_total,
                self.max_score_sum,
                100 * sub_total / self.max_score_sum
            )
        else:
            result = 'span: {}\narea: {}\nisoscelicity: {}\nsolidity: {}\nfitness:{}\nsub-total: {:.0f}/{:.0f} {:.0f}%'.format(
                self.span_score,
                self.area_score,
                self.isoscelicity_score,
                self.solidity_score,
                self.fitness_score,
                sub_total,
                self.max_score_sum,
                100 * sub_total / self.max_score_sum
            )
        return result

    def get_score(self, name, props, val):
        score = -1
        if name in props:
            lower_scoring_range, expected, upper_scoring_range, weighting = props[name]
            if weighting < 0:
                score = 1
            else:
                if val > expected:
                    if upper_scoring_range > 0:
                        scoring_val = val - expected
                        scoring_proportion = 1 - \
                            (scoring_val / upper_scoring_range)
                    else:
                        scoring_proportion = 1
                else:
                    scoring_val = val - (expected - lower_scoring_range)
                    scoring_proportion = scoring_val / \
                        (lower_scoring_range + 0.000001)
                bounded_scoring_proportion = np.clip(scoring_proportion, 0, 1)
                score = round(bounded_scoring_proportion * weighting)

        return score

    def plot(self, draw, to_pixel, font=None, title_offset=(5, 5)):
        """
        Draw the projection using Pillow.
    
        Parameters
        ----------
        draw:
            PIL.ImageDraw.Draw object.
    
        to_pixel:
            Function converting (x, y) projection coordinates into
            (pixel_x, pixel_y).
    
        font:
            Optional PIL ImageFont.
    
        title_offset:
            Pixel offset used for the title.
        """

        try:

            # ---------------------------------------------------------
            # helpers
            # ---------------------------------------------------------

            def point(x, y):
                return to_pixel(float(x), float(y))

            def circle(x, y, radius_px, outline, fill=None, width=1):
                px, py = point(x, y)
                box = (
                    px - radius_px,
                    py - radius_px,
                    px + radius_px,
                    py + radius_px
                )
                draw.ellipse(
                    box,
                    outline=outline,
                    fill=fill,
                    width=width
                )

            def marker(x, y, radius_px, edge, fill):
                circle(
                    x,
                    y,
                    radius_px,
                    outline=edge,
                    fill=fill,
                    width=1
                )

            def line(points, fill, width=1):
                draw.line(
                    [point(x, y) for x, y in points],
                    fill=fill,
                    width=width
                )

            def arrow(start, finish, fill, width=1, head=8):
                """
                Simple filled arrow equivalent to FancyArrowPatch.
                """

                x1, y1 = point(*start)
                x2, y2 = point(*finish)

                draw.line(
                    (x1, y1, x2, y2),
                    fill=fill,
                    width=width
                )

                dx = x2 - x1
                dy = y2 - y1

                length = (dx * dx + dy * dy) ** 0.5

                if length > 0:
                    ux = dx / length
                    uy = dy / length

                    # perpendicular
                    px = -uy
                    py = ux

                    # arrowhead
                    bx = x2 - ux * head
                    by = y2 - uy * head

                    left = (
                        bx + px * head * 0.5,
                        by + py * head * 0.5
                    )

                    right = (
                        bx - px * head * 0.5,
                        by - py * head * 0.5
                    )

                    draw.polygon(
                        [
                            (x2, y2),
                            left,
                            right
                        ],
                        fill=fill
                    )

            # ---------------------------------------------------------
            # incoming contour
            # ---------------------------------------------------------

            for x, y in self.c_raw_in:
                marker(
                    x,
                    y,
                    3,
                    edge='black',
                    fill='pink'
                )

            # ---------------------------------------------------------
            # convex hull
            # ---------------------------------------------------------

            for x, y in self.c_ch:
                marker(
                    x,
                    y,
                    5,
                    edge='red',
                    fill=None
                )

            # ---------------------------------------------------------
            # centre / pose information
            # ---------------------------------------------------------

            margin_x = 0.005
            margin_y = 0.005

            if self.cx is not None and self.cy is not None:

                # original contour centroid
                marker(
                    self.centroid_x,
                    self.centroid_y,
                    4,
                    edge='red',
                    fill=None
                )

                # calculated centre
                marker(
                    self.cx,
                    self.cy,
                    4,
                    edge='green',
                    fill=None
                )

                # bounding-box centre
                marker(
                    self.bbcx,
                    self.bbcy,
                    4,
                    edge='blue',
                    fill=None
                )

                # pose arrow
                arx1, ary1 = gl.percent_along_line(
                    *self.tail, *self.tip, 25)
                arx2, ary2 = gl.percent_along_line(
                    *self.tip, *self.tail, 25)

                arrow(
                    (arx1, ary1),
                    (arx2, ary2),
                    fill='black',
                    width=2,
                    head=8
                )

                # contour point numbers
                for idx in range(len(self.contour))[::4]:

                    pt_xy = self.c_raw_in[idx]

                    label_xy = gl.percent_along_line(
                        self.cx,
                        self.cy,
                        *pt_xy,
                        120
                    )

                    lx, ly = point(
                        label_xy[0] + margin_x,
                        label_xy[1] + margin_y
                    )

                    draw.text(
                        (lx, ly),
                        str(idx),
                        fill='black',
                        font=font,
                        anchor='mm' if font else None
                    )

            # ---------------------------------------------------------
            # identified vertices
            # ---------------------------------------------------------

            if self.valid:

                if self.tip is not None:
                    marker(
                        self.tip[0],
                        self.tip[1],
                        8,
                        edge='black',
                        fill='cyan'
                    )

                if self.tail is not None:
                    marker(
                        self.tail[0],
                        self.tail[1],
                        8,
                        edge='black',
                        fill='cyan'
                    )

                if self.v1 is not None:
                    marker(
                        self.v1[0],
                        self.v1[1],
                        4,
                        edge='black',
                        fill='red'
                    )

                if self.v2 is not None:
                    marker(
                        self.v2[0],
                        self.v2[1],
                        4,
                        edge='black',
                        fill='green'
                    )

                if self.v3 is not None:
                    marker(
                        self.v3[0],
                        self.v3[1],
                        4,
                        edge='black',
                        fill='blue'
                    )

                if self.v4 is not None:
                    marker(
                        self.v4[0],
                        self.v4[1],
                        4,
                        edge='black',
                        fill='yellow'
                    )

                # centroid
                if self.centroid_x is not None:

                    marker(
                        self.centroid_x,
                        self.centroid_y,
                        3,
                        edge='red',
                        fill='red'
                    )

                # fitted polygon
                if self.v4 is not None:
                    line(
                        [
                            self.v1,
                            self.v2,
                            self.v3,
                            self.v4,
                            self.v1
                        ],
                        fill='green',
                        width=1
                    )
                else:
                    line(
                        [
                            self.v1,
                            self.v2,
                            self.v3,
                            self.v1
                        ],
                        fill='green',
                        width=1
                    )

            # ---------------------------------------------------------
            # title
            # ---------------------------------------------------------

            try:

                title = str(self).replace('\t', '    ')

                title_colour = (
                    'black'
                    if self.valid
                    else 'red'
                )

                draw.text(
                    title_offset,
                    title,
                    fill=title_colour,
                    font=font,
                    anchor=None
                )

            except Exception:
                pass

        except Exception as ex:

            err_line = sys.exc_info()[-1].tb_lineno

            msg = (
                'Error in target plot: ' +
                str(ex) +
                ' on line ' +
                str(err_line)
            )

            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)
