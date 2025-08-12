import sys
import time
from datetime import datetime
import numpy as np
from scipy.spatial import ConvexHull
from math import degrees
import matplotlib.patches as mpatches
import pprint

import constants
import geom_lib
import contour_lib as cl
from resourcesheet import Timesheet
import utilities

class Projection():
    '''
        represents the projected vertices of an isosceles target
        derived from infill sharpening
    '''

    def __init__(
            self,
            ssid,
            index,
            c_raw_in,
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

        try:
            num_pts = len(c_raw_in)
            if num_pts < 3:
                if logger:
                    logger.warning(
                        'Invalid target contour - Incoming Points {0} < 3'.format(num_pts))
                raise ValueError('Invalid target contour')
            if debug and logger:
                logger.debug(
                    'target incoming contour point count: {0}'.format(num_pts))

            # incoming bounding-box centre
            self.bbcx, self.bbcy = np.min(
                c_raw_in, axis=0) + (np.ptp(c_raw_in, axis=0) / 2)
            if debug and logger:
                logger.debug('bounding box centre: ({0:.2f}, {1:.2f})'.format(
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
                logger.debug('aspect {0:.2f}'.format(self.aspect))

            # evaluate centroid
            centroid = np.mean(c_raw_in, axis=0)
            self.centroid_x, self.centroid_y = centroid
            self.timesheet.add('centroid calculated')
            
            # evaluate edginess
            self.edginess = cl.edginess(c_raw_in)

            # point reduction?
            # we can be quite aggressive here without much loss of accuracy
            c_red = cl.reduce_contour_points(
                c_raw_in, 64, auto_step=True)
            self.timesheet.add('contour point reduction')

            # convex hull
            '''
                Indices of points forming the vertices of the convex hull.
                For 2-D convex hulls, the vertices are in counterclockwise order.
                For other dimensions, they are in input order
            '''
            ch_obj = ConvexHull(c_red)
            num_pts = len(ch_obj.vertices)
            if debug and logger:
                logger.debug(
                    'convex hull vertex indices: {0}'.format(ch_obj.vertices))
            self.c_ch = c_red[ch_obj.vertices]
            if debug and logger:
                logger.debug('{0} convex hull points: {1}'.format(
                    num_pts, np.round(self.c_ch, 3).tolist()))
            self.timesheet.add('convex hull')

            # hull area
            self.ch_area = ch_obj.volume
            if debug and logger:
                logger.debug('ch area {0:.2f}'.format(self.ch_area))
            self.timesheet.add('hull area calculated')

            # unidentified vertices
            vertices, morph_props = cl.morph_contour_to_polygon(
                self.c_ch, 3, max_iterations=255, debug=False, logger=logger)
            self.pyramid = '{0}|{1}|{2}|{3}'.format(
                len(c_raw_in),
                len(c_red),
                len(self.c_ch),
                len(vertices)
            )
            morph_props_clusters = morph_props['clusters']
            cluster_densities = {int(k): round(1000 * sum(areas) / len(areas), 3)
                                 for (k, (_, areas)) in morph_props_clusters.items()}
            self.cluster_info = pprint.pformat(cluster_densities)
            massive_cluster_count = len(
                [cd for cd in cluster_densities.values() if cd > 3.0])
            num_clusters = len(
                [cd for cd in cluster_densities.values() if cd > 0.04])
            self.clusters = num_clusters if massive_cluster_count == 0 else 0
            if debug and logger:
                logger.debug(pprint.pformat(morph_props))
                logger.debug('cluster_info: {0}'.format(self.cluster_info))
                logger.debug('clusters: {0}'.format(self.clusters))
            self.timesheet.add('morph to polygon')

            # derive an index for the shortest side
            vertices_1 = np.roll(vertices, 1, axis=0)
            self.side_lengths = np.linalg.norm(vertices_1 - vertices, axis=1)
            if debug and logger:
                logger.debug('vertices: {0}'.format(vertices))
                logger.debug('side lengths: {0}m'.format(
                    np.round(self.side_lengths, 3)))

            # side index
            base_side_index = np.argmin(self.side_lengths)
            tip_index = (base_side_index + 1) % 3
            v2_index = (base_side_index + 2) % 3
            v3_index = base_side_index
            if debug and logger:
                logger.debug('tip indices: base_side {} tip {} v2 {} v3 {}'.format(
                    base_side_index, tip_index, v2_index, v3_index))
            self.timesheet.add('shortest side indexing')

            # derive an index for the least infilled vertex
            centroid = np.mean(vertices, axis=0)
            # numpy arctan2 takes a y, x vector
            vector_y = vertices[:, 1] - centroid[1]
            vector_x = vertices[:, 0] - centroid[0]
            vertex_angles_rad = np.arctan2(vector_y, vector_x)  # -pi..pi cw
            vertex_angles_deg = np.rad2deg(vertex_angles_rad)  # -180..180 cw
            vertex_angles_full_deg = np.mod(
                vertex_angles_deg - 90, 360)  # 0.0..360.0 ccw
            vertex_angles = np.rint(vertex_angles_full_deg)  # 0..360 ccw
            if debug and logger:
                logger.debug('vertex_angles: {0}'.format(vertex_angles))
            cluster_area_sums = [sum(a[1])
                                 for a in morph_props_clusters.values()]
            if debug and logger:
                logger.debug(
                    'cluster_area_sums: {0}'.format(cluster_area_sums))
            least_infilled_cluster_index = np.argmin(cluster_area_sums)
            least_infilled_cluster_key = list(morph_props_clusters.keys())[
                least_infilled_cluster_index]
            if debug and logger:
                logger.debug('least_infilled_cluster_index: {0}'.format(
                    least_infilled_cluster_index))
                logger.debug('least_infilled_cluster_key: {0}'.format(
                    least_infilled_cluster_key))

            angular_distance_from_least_infilled_to_vertex = abs(
                vertex_angles - least_infilled_cluster_key)
            if debug and logger:
                logger.debug('angular_distance_from_least_infilled_to_vertex: {0}'.format(
                    np.rint(angular_distance_from_least_infilled_to_vertex)))

            # identified vertices
            self.v1 = vertices[tip_index]
            self.v2 = vertices[v2_index]
            self.v3 = vertices[v3_index]

            self.tip = self.v1
            
            # assess fit of original contour to triangle
            self.fitness = cl.fitness(c_raw_in, [self.v1, self.v2, self.v3])

            # simple tail from vague vertices
            self.tail = np.mean((self.v2, self.v3), axis=0)

            # publish contour not approximation
            self.contour = c_raw_in  # self.c_approx

            if debug and logger:
                logger.debug('tip: ({0:.2f}, {1:.2f})'.format(
                    self.tip[1], self.tip[0]))
                logger.debug('tail: ({0:.2f}, {1:.2f})'.format(
                    self.tail[1], self.tail[0]))

            # evaluate centre
            self.cx, self.cy = np.mean([self.v1, self.tail], axis=0)
            if debug and logger:
                logger.debug(
                    'simple centre: ({0:.2f}, {1:.2f})'.format(self.cx, self.cy))

            # calculate span
            self.span = np.linalg.norm(self.tail - self.v1)

            # evaluate heading
            self.heading = geom_lib.get_angle_between_cartesian_points(
                *self.tail, *self.tip)
            if debug and logger:
                logger.debug('heading: {0:.0f} degrees'.format(
                    degrees(self.heading)))

            self.isoscelicity = geom_lib.triangle_isoscelicity(
                [self.v1, self.v2, self.v3], 0, 1, 2, 0.6)

            self.area = geom_lib.triangle_area(self.v1, self.v2, self.v3)
            self.solidity = self.ch_area / self.area

            self.timesheet.add('tip/tail/centres')

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
        tmplt += 'isoscelicity: {:.3f}\tsolidity: {:.3f}\tfitness: {:.3f}\tedginess:{:.3f}\n'
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
            self.edginess,
            self.assessment(True).replace('&harr;', '~'),
            self.conf_pc,
            self.valid,
            self.elapsed_secs,
            self.mem_footprint/1e6)
        return result

    def plot(self, ax):

        try:

            ax.plot(self.c_raw_in[:, 0], self.c_raw_in[:, 1], marker='.', markersize=6,
                    markeredgecolor="black", markerfacecolor="pink", linestyle='None')
            ax.plot(self.c_ch[:, 0], self.c_ch[:, 1], marker='.', markersize=10,
                    markeredgecolor="red", markerfacecolor="none", linestyle='None')

            margin_x = margin_y = 0.005
            if self.cx is not None and self.cy is not None:
                ax.plot(self.cx, self.cy, marker='o', markersize=8,
                        markeredgecolor="g", markerfacecolor="None")
                ax.plot(self.bbcx, self.bbcy, marker='o', markersize=8,
                        markeredgecolor="b", markerfacecolor="None")
                arx1, ary1 = geom_lib.percent_along_line(
                    self.centroid_x, self.centroid_y, self.v1[0], self.v1[1], -50)
                arx2, ary2 = geom_lib.percent_along_line(
                    self.centroid_x, self.centroid_y, self.v1[0], self.v1[1], 50)
                pose_arrow = mpatches.FancyArrowPatch(
                    (arx1, ary1), (arx2, ary2), mutation_scale=20)
                ax.add_patch(pose_arrow)
                for idx in range(len(self.contour))[::4]:
                    pt_xy = self.c_raw_in[idx]
                    label_xy = geom_lib.percent_along_line(
                        self.cx, self.cy, *pt_xy, 120)
                    ax.annotate(str(
                        idx), (label_xy[0] + margin_x, label_xy[1] + margin_y), fontsize=12, ha='center', va='center')

            if self.valid:

                if self.tail is not None:
                    ax.plot(self.tail[0], self.tail[1], marker='o', markersize=16,
                            linestyle='None', markeredgecolor="black", markerfacecolor="cyan")
                if self.v1 is not None:
                    ax.plot(self.v1[0], self.v1[1], marker='o', markersize=8,
                            linestyle='None', markeredgecolor="black", markerfacecolor="red")
                if self.v2 is not None:
                    ax.plot(self.v2[0], self.v2[1], marker='o', markersize=8,
                            linestyle='None', markeredgecolor="black", markerfacecolor="green")
                if self.v3 is not None:
                    ax.plot(self.v3[0], self.v3[1], marker='o', markersize=8,
                            linestyle='None', markeredgecolor="black", markerfacecolor="blue")
                if self.centroid_x is not None:
                    ax.plot(self.centroid_x, self.centroid_y, marker='o', markersize=6,
                            markeredgecolor="r", markerfacecolor="r", alpha=0.5)

                ax.plot([self.v1[0], self.v2[0], self.v3[0], self.v1[0]], [
                        self.v1[1], self.v2[1], self.v3[1], self.v1[1]], linestyle='dashed', color='g')

            face_colour = 'white'
            if not self.valid:
                face_colour = 'red'
            elif self.conf_pc < constants.SCORE_THRESHOLD:
                face_colour = 'pink'
            elif self.conf_pc < np.mean([100, constants.SCORE_THRESHOLD]):
                face_colour = 'orange'
            ax.set_title(str(self).replace('\t', '    '), wrap=False, fontsize=12,
                         color='black' if self.valid else 'red', ha='left', loc='left')
            ax.set_facecolor(face_colour)

        except Exception as ex:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in target plot: ' + \
                str(ex) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)

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
            self.score_product = int(self.span_score * self.area_score *
                                     self.isoscelicity_score * self.solidity_score * self.fitness_score)
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
