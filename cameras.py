import sys
import platform
import tempfile
import time
import logging
import numpy as np
import requests
from PIL import Image, ImageDraw

import constants
from forms.settings import VirtualSettings, PiSettings
from setting import IntSetting, FloatSetting
from utilities import await_elapsed


class BaseCamera():

    def __init__(self):
        try:
            self.debug = False
            self.tmp = tempfile.gettempdir()
            # Windows | Linux | Darwin(mac)
            self.linux = (platform.system() == 'Linux')

            self.logger = logging.getLogger('vision')
            if self.debug:
                self.logger.debug('in BaseCamera init self is: {0}'.format(
                    type(self)
                ))
            # create property
            for stg_name, stg in self.settings.class_settings().items():
                if stg.label is not None:
                    if self.debug:
                        self.logger.debug(
                            'adding property: {0} with default value: {1}'.format(
                                stg_name, stg.default)
                        )
                    try:
                        setattr(self, stg_name, stg.default)
                    except Exception as e:
                        self.logger.warning(
                            'failed to add/set property: {0}'.format(e))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            err_msg = 'Error in BaseCamera.__init__: ' + \
                str(e) + ' on line ' + str(err_line)
            self.logger.error(err_msg)

    def __contains__(self, key):
        return key in vars(self)

    def __getitem__(self, key):
        return self.settings[key]

    def __setitem__(self, key, value):
        self.settings[key] = value
        setattr(self, key, value)

    def align_with_config(self, config):
        self.settings.align_with_config(config)
        self.apply_settings()

    def apply_settings(self, new_settings=None):
        changed = False
        trace = ''
        if new_settings is not None:
            try:
                if self.debug:
                    self.logger.debug(
                        'camera apply new settings: {0}'.format(new_settings))
                self.settings = new_settings
            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                self.logger.error(
                    'Error in camera apply new settings: {0} on line {1}'.format(e, err_line))

        child = self.settings.__class__
        for stg_name, stg in child.class_settings().items():
            stg_value = self.settings[stg_name]
            # skip system settings
            if stg.label is not None:
                if isinstance(stg, IntSetting) and stg_value is None:
                    if self.debug:
                        self.logger.debug('adjusting None to 0 for IntSetting')
                    stg_value = 0
                elif isinstance(stg, FloatSetting) and stg_value is None:
                    if self.debug:
                        self.logger.debug(
                            'adjusting None to 0.0 for FloatSetting')
                    stg_value = 0.0
                if self.debug:
                    self.logger.debug('camera apply settings: {0} {1}'.format(
                        stg_name, self.settings[stg_name]))
                try:
                    cur_val = str(getattr(self, stg_name))
                    if cur_val != str(stg_value):
                        changed = True
                        trace += 'Camera Changing {0} Setting from {1} to {2}\n'.format(
                            stg_name, cur_val, stg_value)
                        setattr(self, stg_name, stg_value)

                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.error(
                        'Error in camera apply setting: {0} on line {1}'.format(e, err_line))

        if changed:
            delay_secs = 0
            self.logger.info(
                'apply_settings Settings changed - pausing for {0} secs...'.format(delay_secs))
            time.sleep(delay_secs)

        return trace, changed

    def align_with_qs(self, qs):
        self.settings.align_with_qs(qs)
        self.apply_settings()

    def get_settings_as_toolpane(self, tp_id, tp_class):
        return self.settings.get_settings_as_toolpane(tp_id, tp_class)

    def as_public_dict(self):
        return {k: v for (k, v) in vars(self).items() if not k.startswith('_')}

    def __repr__(self):
        return str(self.__dict__)


class OpticalVirtual(BaseCamera):

    def __init__(self, lawn_bounds_pc, vlawn_bollards_pc, distortion, distort_mapper, debug=False):
        self.settings = VirtualSettings()
        super().__init__()
        if self.debug:
            self.logger.debug('in VirtualCamera init')
        self.revision = 'Virtual Camera'
        self._lawn_bounds_pc = lawn_bounds_pc
        self._vlawn_bollards_pc = vlawn_bollards_pc
        self._distortion = distortion
        self._distort_mapper = distort_mapper
        self.debug = debug
        self.virtual = True
        self.img_arr = None
        self.awb_bg_map = {
            'Off': 'black',
            'Auto': 'bisque',
            'Incandescant': 'gold',
            'Tungsten': 'khaki',
            'Flourescent': 'thistle',
            'Indoor': 'oldlace',
            'Daylight': 'lightskyblue',
            'Cloudy': 'lightslategrey',
            'Custom': 'lightcyan'
        }

    def snap(self, fmt=None):
        '''
            Capture an image from the virtual camera, and return it.
        '''
        try:

            start = time.time()

            if self.debug:
                self.logger.debug(
                    'OpticalVirtual capture - incoming fmt: {0}'.format(fmt))

            if self.debug:
                self.logger.debug(
                    'OpticalVirtual capture generating new image...')

            # Obtain the requested image size
            img_width_px = int(self.resolution.split('x')[0])
            img_height_px = int(self.resolution.split('x')[1])

            self._distort_mapper.populate(
                ["unbarrel_inv"],
                img_width_px,
                img_height_px,
                strength=self._distortion,
                zoom=1
            )

            # Create a frame
            img = Image.new('RGB' if fmt == 'rgb' else 'L', (img_width_px,
                            img_height_px), self.awb_bg_map[self.awb_mode])
            img_draw = ImageDraw.Draw(img)

            h_scale = img_width_px / 100
            v_scale = img_height_px / 100

            scaled_lawn_bounds_px = np.array(
                self._lawn_bounds_pc) * (h_scale, v_scale)

            lawn_bounds_px = scaled_lawn_bounds_px.flatten().tolist()
            img_draw.polygon(lawn_bounds_px, fill='#437513')

            # draw some calibration bollards
            boll_radius = 1
            for b in [(h_scale * boll[0], v_scale * (100 - boll[1])) for boll in self._vlawn_bollards_pc]:
                xy = b[0] - boll_radius, b[1] - boll_radius, b[0] + \
                    boll_radius, b[1] + boll_radius
                img_draw.ellipse(xy, fill='white')

            if self.hflip:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

            if self.vflip:
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            # annotation
            if self.annotate:
                img_draw = ImageDraw.Draw(img)  # refresh
                cur_time = time.time()
                now_fmtd = (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(cur_time)) +
                    '.{0:0>3}'.format(int((cur_time % 1) * 1000))
                )

                banner_height_px = img_height_px // 16
                _margin_px = banner_height_px // 2
                img_draw.text((0, 0), now_fmtd, fill=255,
                              font_size=banner_height_px)

            if self.debug:
                try:
                    if fmt.lower() == 'yuv':
                        img.save(self.tmp + "/virtual_cam_plan_debug_grey.jpg")
                    else:
                        img.save(self.tmp + "/virtual_cam_plan_debug_col.jpg")
                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.logger.error(
                        'Warning in OpticalVirtual snap: {0} on line {1}'.format(e, err_line))

            plan_img_arr = np.array(img)
            img_arr = self._distort_mapper.transform_image(plan_img_arr)

            out_arr = img_arr.astype(np.uint8)
            if self.debug:
                if fmt.lower() == 'yuv':
                    out_img = Image.fromarray(out_arr)
                    out_img.save(self.tmp + "/virtual_cam_debug_grey.jpg")
                else:
                    out_img = Image.fromarray(out_arr, 'RGB')
                    out_img.save(self.tmp + "/virtual_cam_debug_col.jpg")

            extra_delay_secs = await_elapsed(
                time.time(), start + constants.THROTTLE_CAMERA_SNAP_SECS)  # blocks
            if self.debug:
                if extra_delay_secs > 0:
                    self.logger.debug(
                        'OpticalVirtual capture throttle - slept for {0} seconds'.format(extra_delay_secs))
                else:
                    self.logger.debug(
                        'OpticalVirtual capture throttling not required')
            end = time.time()
            elapsed = round(end - start, 3)  # seconds
            if self.debug:
                self.logger.debug(
                    'OpticalVirtual capture - captured in {0:.2f} seconds'.format(elapsed))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error(
                'Error in OpticalVirtual snap: {0} on line {1}'.format(e, err_line))

        return out_arr


class USBCamera(BaseCamera):
    pass


class RemoteOpticalPi(BaseCamera):

    def __init__(self, endpoint):
        self.settings = PiSettings()
        super().__init__()
        self.endpoint = endpoint
        self.revision = 'Remote Linux RPI'

        self.logger.debug('in RemoteOpticalPi init')

    def snap(self, _fmt=None):
        self.logger.debug('Remote Optical Pi Snap...')
        '''
            use the url to make a remote snap request
        '''
        img_arr = None
        try:
            # obtain settings as a query string
            qs = self.settings.get_qs()
            # override settings default 'locate' client with 'remote'
            url = 'http://{0}/raw_img?fmt=raw&{1}&client=remote'.format(
                self.endpoint, qs)
            self.logger.debug(
                'RemoteOpticalPi making raw_img request to: {0}'.format(url))

            img_width_px = int(self.settings.resolution.split('x')[0])
            img_height_px = int(self.settings.resolution.split('x')[1])

            req_start = time.time()
            resp = requests.get(url, stream=True, timeout=45).raw
            self.logger.debug('RemoteOpticalPi image returned in {0:.3f} seconds'.format(
                time.time() - req_start))
            img_arr_serial = np.asarray(bytearray(resp.read()), dtype="uint8")
            self.logger.debug('RemoteOpticalPi img_arr_serial: {} w: {} h: {} w*h: {}'.format(
                img_arr_serial.shape, 
                img_width_px,
                img_height_px,
                (img_width_px * img_height_px))
            )

            # resize array
            chans = img_arr_serial.shape[0] // (img_width_px * img_height_px)
            if chans == 3:
                img_arr = np.reshape(img_arr_serial.astype(
                    np.uint8), (img_height_px, img_width_px, 3))
            else:
                img_arr = np.resize(
                    img_arr_serial, (img_height_px, img_width_px)).astype(np.uint8)

            if self.debug:
                out_img = Image.fromarray(img_arr)
                out_img.save(self.tmp + "/remote.jpg")

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.logger.error(
                'Error in RemoteOpticalPi snap: {0} on line {1}'.format(e, err_line))

        return img_arr
