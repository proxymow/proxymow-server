import sys
import numpy as np
import re
from skimage.measure import find_contours

import constants
from utilities import get_mem_stats

class Viewport():
    '''
        represents a resolution-independent window into a larger image array
    '''

    def __init__(self, c1_rc=None, c2_rc=None, c3_rc=None, c4_rc=None, shape=None, index=None):
        '''
            constructor - accepts corner tuples in any corner order
            stores corners as percentages
            coordinate order is row, column
            if shape is passed in, converts incoming pixels to percentages
            if shape is None, assumes incoming coordinates are already percentages
        '''
        self.index = index
        if shape is not None:
            # incoming pixels - px => %
            c1_rc = tuple(np.array(c1_rc) * 100 / shape)
            c2_rc = tuple(np.array(c2_rc) * 100 / shape)
            c3_rc = tuple(np.array(c3_rc) * 100 / shape)
            c4_rc = tuple(np.array(c4_rc) * 100 / shape)
        # set reinforces anonymous corner ordering
        # Null Viewport is the empty set
        self.corners = set()

        if (c1_rc is not None and
            c2_rc is not None and
            c3_rc is not None and
                c4_rc is not None):
            self.corners = set([tuple(c1_rc), tuple(
                c2_rc), tuple(c3_rc), tuple(c4_rc)])

    @classmethod
    def from_corners(cls, c_origin, c_diag, shape=None, index=None):
        # alternative constructor from origin corner and dimensions
        if shape is not None:
            # incoming pixels - px => %
            c_origin = tuple(np.array(c_origin) * 100 / shape)
            c_diag = tuple(np.array(c_diag) * 100 / shape)
        bottom_left = (c_diag[0], c_origin[1])
        top_right = (c_origin[0], c_diag[1])
        inst = cls(c_origin, bottom_left, c_diag, top_right, index=index)

        return inst

    @classmethod
    def from_contour(cls, contour, shape, index=None):
        # alternative constructor from contour extremities
        # contours are in row, col order so comply
        top_left = np.min(contour, axis=0)
        bottom_right = np.max(contour, axis=0)
        inst = cls.from_corners(100 * top_left / shape,
                                100 * bottom_right / shape, index=index)

        return inst

    @classmethod
    def from_pose(cls, pose, shape, index=None):
        if pose is not None and pose.cam is not None and 'vertices_px' in vars(pose.cam):
            vertices_x_px = pose.cam.vertices_px[::2]
            vertices_y_px = pose.cam.vertices_px[1::2]
            left_px, top_px = min(vertices_x_px), min(vertices_y_px)
            right_px, bottom_px = max(vertices_x_px), max(vertices_y_px)
            left_pc, top_pc = left_px * 100 / shape[1], top_px * 100 / shape[0]
            right_pc, bottom_pc = right_px * 100 / \
                shape[1], bottom_px * 100 / shape[0]
            inst = cls.from_corners(
                (top_pc, left_pc), (bottom_pc, right_pc), index=index)
            return inst
        else:
            return None

    @classmethod
    def copy(cls, vp, aug_index=True):
        # copy constructor
        inst = cls(vp.origin, vp.bottom_left, vp.bottom_right, vp.top_right, index=str(
            vp.index) + ('-copy' if aug_index else ''))
        return inst

    @property
    def isnull(self):
        return self.corners == set()

    @property
    def shape(self):
        min_coords = np.min(self.corners, axis=0)
        max_coords = np.max(self.corners, axis=0)
        return (max_coords - min_coords)

    @property
    def footprint(self):
        result = None
        if self.height is not None and self.width is not None:
            result = (self.height * self.width) / 1e2
        return result

    @property
    def height(self):
        if not self.isnull:
            min_coords = np.min(list(self.corners), axis=0)
            max_coords = np.max(list(self.corners), axis=0)
            height = max_coords[0] - min_coords[0]
        else:
            height = None
        return height

    @property
    def width(self):
        if not self.isnull:
            min_coords = np.min(list(self.corners), axis=0)
            max_coords = np.max(list(self.corners), axis=0)
            width = max_coords[1] - min_coords[1]
        else:
            width = None
        return width

    def xyxy_polylines(self, shape):
        if not self.isnull:
            ccw_closed_corner_list = [self.origin, self.bottom_left,
                                      self.bottom_right, self.top_right, self.origin]  # y, x
            xy_closed_corners = [
                (c[1] * shape[1] / 100, c[0] * shape[0] / 100) for c in ccw_closed_corner_list]
            xyxy_closed_corners = list(
                zip(xy_closed_corners, xy_closed_corners[1:]))
        else:
            xyxy_closed_corners = []
        return xyxy_closed_corners

    @property
    def centre(self):
        if self.isnull:
            centre_coords = None  # undefined
        else:
            centre_coords = np.mean(list(self.corners), axis=0).clip(0)
        return centre_coords

    @property
    def origin(self):
        if self.isnull:
            min_coords = (0, 0)
        else:
            min_coords = tuple(np.min(list(self.corners), axis=0).clip(0))
        return min_coords

    @property
    def bottom_left(self):
        if self.isnull:
            # partially undefined as we don't know the outer array size
            coords = (sys.maxsize, 0)
        else:
            coords = tuple([np.max(list(self.corners), axis=0)[
                           0], np.min(list(self.corners), axis=0)[1]])
        return coords

    @property
    def bottom_right(self):
        if self.isnull:
            # undefined as we don't know the outer array size
            max_coords = (sys.maxsize, sys.maxsize)
        else:
            max_coords = tuple(np.max(list(self.corners), axis=0))
        return max_coords

    @property
    def top_right(self):
        if self.isnull:
            # partially undefined as we don't know the outer array size
            coords = (0, sys.maxsize)
        else:
            coords = tuple([np.min(list(self.corners), axis=0)[
                           0], np.max(list(self.corners), axis=0)[1]])
        return coords

    @property
    def slicer_info(self):
        # a[start:stop]  # items start through stop-1
        if not self.isnull:
            extreme_top = int(max(min(self.origin[0], self.top_right[0]), 0))
            extreme_left = int(
                max(min(self.origin[1], self.bottom_left[1]), 0))
            extreme_bottom = int(
                max(self.bottom_left[0], self.bottom_right[0]))
            extreme_right = int(max(self.bottom_right[1], self.top_right[1]))

            row_slice = slice(extreme_top, extreme_bottom)
            col_slice = slice(extreme_left, extreme_right)
        else:
            # all elements
            row_slice = slice(0, 100)
            col_slice = slice(0, 100)

        return row_slice, col_slice

    def slicer(self, shape):
        # a[start:stop]  # items start through stop-1
        if not self.isnull:
            extreme_top = max(min(self.origin[0], self.top_right[0]), 0)
            extreme_left = max(min(self.origin[1], self.bottom_left[1]), 0)
            extreme_bottom = max(self.bottom_left[0], self.bottom_right[0])
            extreme_right = max(self.bottom_right[1], self.top_right[1])

            row_slice = slice(
                int(extreme_top * shape[0] / 100), int(extreme_bottom * shape[0] / 100))
            col_slice = slice(
                int(extreme_left * shape[1] / 100), int(extreme_right * shape[1] / 100))
        else:
            # all elements
            row_slice = slice(0, shape[0])
            col_slice = slice(0, shape[1])

        return row_slice, col_slice

    def resize(self, height_factor, width_factor=None):
        '''
            resize viewport by factor(s)
            e.g. x2, x3, etc.
        '''
        if width_factor is None:
            width_factor = height_factor
        try:
            # find amounts to add to each corner
            new_height = self.height * height_factor
            height_growth = (new_height - self.height) / 2
            new_width = self.width * width_factor
            width_growth = (new_width - self.width) / 2
            self.grow(height_growth, width_growth)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in viewport scale:' + 
                  str(e) + ' on line ' + str(err_line))

    def grow(self, drows, dcols):
        # grow viewport by drows and dcols
        try:
            if not self.isnull:
                new_origin = tuple(
                    (self.origin + np.array([-drows, -dcols])).clip(0))
                new_bottom_left = tuple(
                    (self.bottom_left + np.array([drows, -dcols])).clip(0))
                new_bottom_right = tuple(
                    self.bottom_right + np.array([drows, dcols]))
                new_top_right = tuple(
                    self.top_right + np.array([-drows, dcols]))
                self.corners = set(
                    [new_origin, new_bottom_left, new_bottom_right, new_top_right])
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in viewport grow:' + 
                  str(e) + ' on line ' + str(err_line))

    def scale(self, factor):
        # scale viewport by factor
        try:
            if not self.isnull:
                new_origin = tuple((np.array(self.origin) * factor).clip(0))
                new_bottom_left = tuple(
                    (np.array(self.bottom_left) * factor).clip(0))
                new_bottom_right = tuple(np.array(self.bottom_right) * factor)
                new_top_right = tuple(np.array(self.top_right) * factor)
                self.corners = set(
                    [new_origin, new_bottom_left, new_bottom_right, new_top_right])
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in viewport scale:' + 
                  str(e) + ' on line ' + str(err_line))

    def find_contours(self, array, logger=None):
        margins = []
        edginess = []
        local_contours = []
        try:
            if logger is not None:
                logger.info(
                    'About to Find Contours - {} {}'.format(
                        array.shape,
                        get_mem_stats()
                    )
                )

            if array is not None and len(array.shape) >= 2 and array.shape[0] > 4 and array.shape[1] > 4:
                # if no threshold is specified, skimage is going to use (max(image) + min(image)) / 2
                # so might as well pre-calculate for insight
                # masking guarantees some black, so minimum will always be zero and range == max 
                max_intensity = np.max(array).astype(float)
                intensity_range = max_intensity  #  - min_intensity
                threshold = max_intensity / 2
                white_pixel_count = np.count_nonzero([array > threshold])
                tonal_ratio = white_pixel_count / array.size

                # skip situations where the statistics don't bode well...
                if threshold < constants.MINIMUM_CONTOUR_THRESHOLD:
                    if logger is not None:
                        logger.debug('Find Contours - skip as threshold is below constant minimum {:.3f} < {:.3f}'.format(
                            threshold,
                            constants.MINIMUM_CONTOUR_THRESHOLD
                            )
                        )
                elif self.footprint is not None and self.footprint > constants.MAXIMUM_VIEWPORT_FOOTPRINT:
                    if logger is not None:
                        logger.info(
                            'Find Contours - skip as scope is too broad {:.3f}% > {:.3f}%'.format(
                                self.footprint,
                                constants.MAXIMUM_VIEWPORT_FOOTPRINT
                            )
                        )
                else:

                    # find local contours at a constant value of threshold
                    local_contours = find_contours(array, threshold)
    
                    if logger is not None:
                        logger.info(
                            'Find Contours - {} {:.2f}% Max\\Range: {:.3f} Thresh: {:.3f} Whites: {} Tone: {:.6f} Num Contours: {}'.format(
                                array.shape,
                                self.footprint if self.footprint is not None else 100.0,
                                intensity_range,
                                threshold,
                                white_pixel_count,
                                tonal_ratio,
                                len(local_contours)
                            )
                        )
                        
                    # calculate margins
                    for c_arr in local_contours:
                        top_margin, left_margin = np.min(c_arr, axis=0)
                        bottom_margin, right_margin = array.shape - \
                            np.max(c_arr, axis=0)
                        margins.append(
                            (top_margin, left_margin, bottom_margin, right_margin))
                        arr_height, arr_width = array.shape
                        left_edginess = left_margin / arr_width
                        right_edginess = right_margin / arr_width
                        top_edginess = top_margin / arr_height
                        bottom_edginess = bottom_margin / arr_height
                        min_edginess_pc = min(
                            [left_edginess, right_edginess, top_edginess, bottom_edginess]) * 100
                        edginess.append(min_edginess_pc)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in viewport find contours: ' + 
                  str(e) + ' on line ' + str(err_line))
            print('Error in viewport array.size:', array.shape)

        return local_contours, margins, edginess

    def proximity_ratio(self, other):
        '''
            calculate a scale independent measure of proximity
            sum of diagonals / distance between centres
            values <= 1, viewports are in close proximity
        '''
        dist_between_centres = np.linalg.norm(
            np.array(other.centre) - np.array(self.centre))
        this_diag = np.linalg.norm(
            np.array(self.bottom_right) - np.array(self.origin))
        other_diag = np.linalg.norm(
            np.array(other.bottom_right) - np.array(other.origin))
        sum_of_diags = this_diag + other_diag
        ratio = sum_of_diags / (dist_between_centres + 0.00001)
        return ratio

    def absorb(self, other):
        '''
            find the left-most left, the highest top, right-most right and lowest bottom
        '''
        top_most_row = np.min([self.origin[0], other.origin[0]])
        left_most_col = np.min([self.origin[1], other.origin[1]])
        bottom_most_row = np.max([self.bottom_right[0], other.bottom_right[0]])
        right_most_col = np.max([self.bottom_right[1], other.bottom_right[1]])
        self.corners = set([(top_most_row, left_most_col), (bottom_most_row, left_most_col),
                           (bottom_most_row, right_most_col), (top_most_row, right_most_col)])
        '''
            extend self to include other

            -----------
            |  self    |
            |          |
            |      |   |---------
            -----------
                   |    other   |
                   -------------
            extend my bottom right

            -----------
            |  other   |
            |          |
            |      |   |--------
            -----------
                   |    self   |
                   -------------
            extend my top left
        '''

    def get_expected_target_span_px(self, tgt_dim_m, shape, data_mapper):
        '''
            round-trip from this viewport, to arena,
            add span_m, and transform back
        '''
        half_tgt_dim = tgt_dim_m / 2
        cent_yx = self.centre * shape / 100
        # get_coordinates is the singular form of transform_contour i.e. x, y
        arena_target_centre = data_mapper.get_coordinates(
            np.array([[int(cent_yx[1]), int(cent_yx[0])]]), trace=False)
        arena_target_tip = arena_target_centre[0] + [half_tgt_dim, 0]
        arena_target_tail = arena_target_centre[0] - [half_tgt_dim, 0]
        arena_target_vertices_m = [arena_target_tip, arena_target_tail]
        arena_target_vertices_x = np.array(arena_target_vertices_m)[:, 0]
        arena_target_vertices_y = np.array(arena_target_vertices_m)[:, 1]
        cam_target_vertices = data_mapper.reverse_coordinates(
            arena_target_vertices_x, arena_target_vertices_y)
        span_px = np.hypot(cam_target_vertices[0][0] - cam_target_vertices[0]
                           [1], cam_target_vertices[1][0] - cam_target_vertices[1][1])
        return span_px

    def __repr__(self):
        # need to identify corners for a helpful representation
        try:
            starts = np.array([self.origin, self.bottom_left,
                              self.bottom_right, self.top_right])
            sens_starts = starts.clip(0, 100)
            finishes = np.roll(sens_starts, -1, axis=0)
            sides = np.linalg.norm(finishes - sens_starts, axis=1)
            result = str(self.index) + ' ' + \
                str([(round(c[1], 2), round(c[0], 2))
                    for c in self.corners]) + '\n'
            fmt_str = '[{0:.0f}%, {1:.0f}%]..[{6:.0f}%, {7:.0f}%]\n[{2:.0f}%, {3:.0f}%]..[{4:.0f}%, {5:.0f}%]\n'
            fmt_str += ' +\t{11:^3.0f}%\t +\n'
            fmt_str += '{8:^3.0f}%\t\t{10:^3.0f}%\n'
            fmt_str += ' +\t{9:^3.0f}%\t +\n'
            result += fmt_str.format(*
                                     (np.hstack([sens_starts.flatten(), sides])))
            result += re.sub('(\\d+),', r'\1%,', str(self.slicer_info)
                             ) + ' [start, stop(excl), step]'
            result += ' using {:.3f}Mb'.format(sys.getsizeof(self)/1e6)
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in viewport __repr__: ' + 
                  str(e) + ' on line ' + str(err_line))
            result = 'Bad Viewport'
        return result


def merge_adjacent_viewports(vps, idx=0):

    if idx >= len(vps) - 1:
        # finished
        return
    else:
        first = vps[idx]
        second = vps[idx + 1]
        prox_ratio = first.proximity_ratio(second)
        adjacent = prox_ratio > 1
        if adjacent:
            first.absorb(second)
            vps.pop(idx + 1)
            # keep same pointer
        else:
            # advance pointer
            idx += 1
        merge_adjacent_viewports(vps, idx)
