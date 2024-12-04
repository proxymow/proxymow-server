import sys
import numpy as np
from skimage import transform
from scipy import interpolate
from skimage import transform as tf
import time


class Mapper(object):
    '''
        abstract base class
    '''

    def __init__(self,
                 map_arr_cols,
                 map_arr_rows,
                 pipeline,
                 matrix,
                 strength,
                 zoom,
                 datatype=np.int16,
                 logger=None
                 ):
        '''
        Constructor
        '''
        self.pipeline = pipeline
        self.matrix = matrix
        self.map_arr_cols = map_arr_cols
        self.map_arr_rows = map_arr_rows
        self.matrix = matrix
        self.strength = strength
        self.zoom = zoom
        self.datatype = datatype
        self.logger = logger

    def build_non_invertible_interpolator(self):
        extrap = 200
        px = np.linspace(-extrap, self.map_arr_cols + extrap - 1, num=20)
        py = np.linspace(-extrap, self.map_arr_rows + extrap - 1, num=20)
        xg, yg = np.meshgrid(px, py)
        xgf, ygf = xg.flatten(), yg.flatten()
        xy_pts = np.column_stack([xgf, ygf])

        values = self.unbarrel(
            xy_pts, self.map_arr_cols, self.map_arr_rows, self.correction_radius, self.zoom)
        x_values = values[:, 0]
        y_values = values[:, 1]

        self.unb_itp_x = interpolate.LinearNDInterpolator(
            (x_values, y_values), xgf, fill_value=-1)
        self.unb_itp_y = interpolate.LinearNDInterpolator(
            (x_values, y_values), ygf, fill_value=-1)

    def transform(self, coords, matrix):
        coords = np.array(coords, copy=False, ndmin=2)
        # Transposing a 1-D array returns an unchanged view of the original array
        x, y = np.transpose(coords)
        src = np.vstack((x, y, np.ones_like(x)))
        # matrix multiply the transposed matrices
        dst = src.T @ matrix.T
        # below, we will divide by the last dimension of the homogeneous
        # coordinate matrix. In order to avoid division by zero,
        # we replace exact zeros in this column with a very small number.
        dst[dst[:, 2] == 0, 2] = np.finfo(float).eps
        # rescale to homogeneous coordinates
        dst[:, :2] /= dst[:, 2:3]
        return dst[:, :2]

    def unbarrel(self, coords, cols, rows, correction_radius, zoom):
        return self.distortion(coords, cols, rows, correction_radius, zoom, False)

    def distortion(self, coords, cols, rows, correction_radius, zoom, invert):
        half_width = cols / 2
        half_height = rows / 2
        radial_x = coords[:, 0] - half_width
        radial_y = coords[:, 1] - half_height
        distance = np.hypot(radial_x, radial_y)
        ratio = distance / correction_radius
        # prepare angles for divide by zero cases
        theta = np.ones_like(ratio)
        # inverting division 'ratio / arctan(ratio)' creates pincushion distortion - rather than fixing barrel 'arctan / ratio'
        if not invert:
            # function courtesy tanner helland, fixes barrel distortion
            np.divide(np.arctan(ratio), ratio, out=theta, where=ratio != 0)
        else:
            # my approximate inverse, creates barrel distortion
            np.divide(ratio, np.arctan(ratio), out=theta, where=ratio != 0)

        source_x = half_width + theta * radial_x * zoom
        source_y = half_height + theta * radial_y * zoom
        result = np.column_stack([source_x, source_y])
        return result

    def unbarrel_inv(self, coords):
        source_x = self.unb_itp_x(coords)
        source_y = self.unb_itp_y(coords)
        result = np.column_stack([source_x, source_y])
        return result

    def get_coordinates(self, coords, trace=False):
        result = coords
        pipeline = self.pipeline
        if trace:
            msg = 'Processing coords shape {0} [{1}..{2}, {3}..{4}] through pipeline {5}'.format(
                coords.shape,
                np.min(coords, axis=0)[0],
                np.max(coords, axis=0)[0],
                np.min(coords, axis=0)[1],
                np.max(coords, axis=0)[1],
                pipeline
            )
            msg += 'Coords before operations\n{0}'.format(coords)
            if self.logger is not None:
                self.logger.debug(msg)
            else:
                print(msg)
        for operation in pipeline:
            if operation == "transform":
                result = self.transform(result, self.matrix)
            elif operation == "unbarrel_inv":
                # create inverse unbarrel distortion
                result = self.unbarrel_inv(result)
            elif operation == "unbarrel":
                # create pin-cushion distortion or undistort image
                result = self.unbarrel(
                    result, self.map_arr_cols, self.map_arr_rows, self.correction_radius, self.zoom)
            else:
                if operation is not None and operation.startswith('#'):
                    print(
                        'Mapper Warning: {0} is a commented operation. Skipping...'.format(operation))
                else:
                    raise Exception(
                        'Unrecognised Pipeline Operation {0}'.format(operation))

            if trace:
                msg = 'Coords after operation {0}:\n{1}'.format(
                    operation, result)
                if self.logger is not None:
                    self.logger.debug(msg)
                else:
                    print(msg)

        return result


class ImageMapper(Mapper):
    '''
        transforms images
    '''

    def __init__(self,
                 pipeline=[],
                 map_arr_cols=0,
                 map_arr_rows=0,
                 matrix=None,
                 strength=0.0,
                 zoom=1.0,
                 datatype=np.int16,
                 logger=None,
                 populate=True
                 ):
        '''
        Constructor
        '''
        super().__init__(map_arr_cols, map_arr_rows, pipeline,
                         matrix, strength, zoom, datatype, logger)
        self.cache_key_tmplt = '{0}-{1}-{2}-{3}-{4}'

        if populate:
            self.populate(pipeline, map_arr_cols,
                          map_arr_rows, matrix, strength, zoom)

    def clear(self):
        self._map = None
        self.cache_key = None

    def populate(self,
                 pipeline,
                 map_arr_cols,
                 map_arr_rows,
                 matrix=None,
                 strength=0.0,
                 zoom=1.0):
        '''
            build the map if necessary
        '''

        self.pipeline = pipeline
        self.map_arr_cols = map_arr_cols
        self.map_arr_rows = map_arr_rows
        self.matrix = matrix
        self.strength = strength
        self.zoom = zoom

        # create unique key for these settings
        cache_key = self.cache_key_tmplt.format(
            self.map_arr_cols,
            self.map_arr_rows,
            hash(str(matrix)),
            strength,
            zoom
        )

        if hasattr(self, 'cache_key') and cache_key == self.cache_key:
            msg = 'ImageMapper, map is up to date'
            if self.logger:
                self.logger.info(msg)
        else:
            if hasattr(self, 'cache_key'):
                msg = 'ImageMapper, map is out of date - rebuilding...'
            else:
                msg = 'ImageMapper, building initial map...'
            if self.logger:
                self.logger.info(msg)

            if self.strength is None or self.strength == 0:
                self.strength = 0.00001
            if self.zoom is None:
                self.zoom = 1.0
            self.correction_radius = np.hypot(
                self.map_arr_cols, self.map_arr_rows) / self.strength

            # create interpolator for non-invertable function
            super().build_non_invertible_interpolator()

            self._map = self.build_map()

            # re-create unique key for these settings
            self.cache_key = self.cache_key_tmplt.format(
                self.map_arr_cols,
                self.map_arr_rows,
                hash(str(matrix)),
                strength,
                zoom
            )

    def build_map(self):

        msg = 'ImageMapper, about to create map...'
        if self.logger:
            self.logger.info(msg)
        build_start = time.time()
        new_map = transform.warp_coords(self.get_coordinates, shape=(
            self.map_arr_rows, self.map_arr_cols), dtype=self.datatype)
        msg = 'ImageMapper, created map, array {0} size: {1:.1f} MB [{2:.2f}, {3:.2f}, {4:.2f}, {5:.2f}] in {6:.3f} secs'.format(
            new_map.shape,
            new_map.size * new_map.itemsize / 1e6,
            np.min(new_map[0]),
            np.min(new_map[1]),
            np.max(new_map[0]),
            np.max(new_map[1]),
            time.time() - build_start)
        if self.logger:
            self.logger.info(msg)
        return new_map

    def transform_image(self, img_arr):

        out_arr = self.warp_colour(img_arr, self._map)

        return out_arr

    def warp_colour(self, img_arr, coord_map, preserve_scale=True, preserve_datatype=True):
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


class DataMapper(Mapper):
    '''
        transforms data
    '''

    def __init__(self,
                 pipeline=[],
                 map_arr_cols=0,
                 map_arr_rows=0,
                 matrix=None,
                 strength=0.0,
                 zoom=1.0,
                 datatype=np.int16,
                 num_samp_per_dim=100,
                 interp_extrap=50,
                 logger=None,
                 populate=True
                 ):
        '''
        Constructor
        '''
        super().__init__(map_arr_cols, map_arr_rows, pipeline,
                         matrix, strength, zoom, datatype, logger)
        self.num_samp_per_dim = num_samp_per_dim
        self.interp_extrap = interp_extrap
        self.cache_key_tmplt = '{0}-{1}-{2}-{3}-{4}'

        if populate:
            self.populate(pipeline, map_arr_cols,
                          map_arr_rows, matrix, strength, zoom)

    def clear(self):
        self._map = None
        self.rev_itp_x = None
        self.rev_itp_y = None
        self.cache_key = None

    def populate(self,
                 pipeline,
                 map_arr_cols,
                 map_arr_rows,
                 matrix=None,
                 strength=0.5,
                 zoom=1
                 ):
        '''
            populate if necessary
        '''
        self.pipeline = pipeline
        self.map_arr_cols = map_arr_cols
        self.map_arr_rows = map_arr_rows
        self.matrix = matrix
        self.strength = strength
        self.zoom = zoom

        if self.strength is None or self.strength == 0:
            self.strength = 0.00001
        if self.zoom is None:
            self.zoom = 1.0

        self.correction_radius = np.hypot(
            self.map_arr_cols, self.map_arr_rows) / self.strength

        # create unique key for these settings
        cache_key = self.cache_key_tmplt.format(
            self.map_arr_cols,
            self.map_arr_rows,
            hash(str(matrix)),
            strength,
            zoom
        )

        if hasattr(self, 'cache_key') and cache_key == self.cache_key:
            msg = 'DataMapper, map is up to date'
            if self.logger:
                self.logger.info(msg)
        else:
            if hasattr(self, 'cache_key'):
                msg = 'DataMapper, map is out of date - rebuilding...'
            else:
                msg = 'DataMapper, building initial map...'
            if self.logger:
                self.logger.info(msg)

            build_start = time.time()

            # create interpolator for non-invertable function
            self.build_non_invertible_interpolator()

            # create interpolators
            px = np.linspace(-self.interp_extrap, self.map_arr_cols +
                             self.interp_extrap - 1, num=self.num_samp_per_dim)
            py = np.linspace(-self.interp_extrap, self.map_arr_rows +
                             self.interp_extrap - 1, num=self.num_samp_per_dim)
            xg, yg = np.meshgrid(px, py)
            xgf, ygf = xg.flatten(), yg.flatten()
            xy_pts = np.column_stack([xgf, ygf])

            values = self.get_coordinates(xy_pts)
            x_values = values[:, 0]
            y_values = values[:, 1]

            self.rev_itp_x = interpolate.LinearNDInterpolator(
                (x_values, y_values), xgf, fill_value=-1)
            self.rev_itp_y = interpolate.LinearNDInterpolator(
                (x_values, y_values), ygf, fill_value=-1)

            map_size = (self.num_samp_per_dim + (2 * self.interp_extrap)) ** 2
            msg = 'DataMapper, created map, grid {0} size: {1:.1f} KB [{2:.2f}, {3:.2f}, {4:.2f}, {5:.2f}] in {6:.3f} secs'.format(
                (self.num_samp_per_dim, self.num_samp_per_dim),
                map_size * sys.getsizeof(self.datatype.__call__()) / 1e3,
                min(y_values),
                min(x_values),
                max(y_values),
                max(x_values),
                time.time() - build_start)
            if self.logger:
                self.logger.info(msg)

            # re-create unique key for these settings
            self.cache_key = self.cache_key_tmplt.format(
                self.map_arr_cols,
                self.map_arr_rows,
                hash(str(matrix)),
                strength,
                zoom
            )

    def transform_contour(self, c_yx, trace=False):

        # the incoming contour is in y, x order
        # we need the contour in x, y order so we can process it
        # note that x, y is the order returned
        c_xy = np.flip(c_yx, axis=1)
        return self.get_coordinates(c_xy, trace)

    def reverse_coordinates(self, x, y):
        result = None
        if self.rev_itp_x is not None and self.rev_itp_y is not None:
            result = self.rev_itp_x(x, y), self.rev_itp_y(x, y)

        return result
