import sys
import time
import numpy as np
from PIL import Image, ImageDraw
from libcamera import Transform  # @UnresolvedImport
from pprint import pformat

import constants
from cameras import BaseCamera, USBCamera
from forms.settings import LusbSettings, PiSettings
import vis_lib
from timesheet import Timesheet
from utilities import await_elapsed


class CamRes():

    def __init__(self, res_str='0x0'):
        res_vals = res_str.split('x')
        self.width = int(res_vals[0])
        self.height = int(res_vals[1])

    def __getitem__(self, item):
        return self.width if item == 0 else self.height

    def __repr__(self):
        return '{0:.0f}x{1:.0f}'.format(self.width, self.height)


class OpticalLusb(USBCamera):

    def __init__(self, picam2, debug=False, logger=None):

        self.settings = LusbSettings()
        self.local_config_string = None
        super().__init__()

        self.debug = debug
        self.logger = logger
        self.revision = 'Picamera II USB'
        self._resolution = CamRes()
        # Flip Image?
        self.hflip = False
        self.vflip = False
        self.picam2 = picam2

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, value):
        if isinstance(value, str):
            self._resolution = CamRes(value)
        elif isinstance(value, tuple):
            self._resolution = CamRes(
                '{0:.0f}x{1:.0f}'.format(value[0], value[1]))

    @property
    def metadata(self):
        return self.picam2.capture_metadata()

    def __str__(self):
        result = ''
        result += 'resolution: ' + str(self._resolution) + '\n'
        result += 'hflip: ' + str(self.hflip) + '\n'
        result += 'vflip: ' + str(self.vflip) + '\n'

        return result

    def snap(self, cap_fmt):
        '''
            Capture an image from the usb camera
        '''

        try:
            # snap to rgb array
            img_array = self.capture(cap_fmt)
            chans = len(img_array.shape)
            if self.debug:
                if chans == 3:
                    self.logger.debug(
                        'lusb snap {2}x{1}x{0}'.format(*img_array.shape))
                else:
                    self.logger.debug(
                        'lusb snap {0}x{1}'.format(*img_array.shape))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in picamera II usb snap: ' +
                  str(e) + ' on line ' + str(err_line))

        return img_array

    def capture(self, fmt=None):

        try:

            start = time.time()
            timesheet = Timesheet('Optical-USB-Capture')

            local_config_string = ''.join({k: str(v) for k, v in self.settings.get_settings_as_dict(
            ).items() if k not in ['client', 'queue']}.values())
            timesheet.add('local config string assembled')
            if self.debug and self.logger:
                self.logger.debug('Current config:' + str(local_config_string))
            if self.debug and self.logger:
                self.logger.debug('Previous config:' +
                                  str(self.local_config_string))

            # Calculate the actual image size (accounting for rounding of the resolution)
            width_px = self.resolution.width
            height_px = self.resolution.height
            array_width_px = width_px  # (width_px + 31) // 32 * 32
            array_height_px = height_px  # (height_px + 15) // 16 * 16

            # Take a frame
            try:
                start = time.time()

                if local_config_string != self.local_config_string:

                    # Take image in requested format
                    capture_config = self.picam2.create_still_configuration(
                        main={
                            "size": (width_px, height_px)
                        }
                    )
                    timesheet.add('still config created')

                    # optimise config
                    if self.debug and self.logger:
                        self.logger.debug(
                            'Requested config:' + str(capture_config['main']))
                    if self.debug and self.logger:
                        self.logger.debug(
                            'Revised config:' + str(capture_config['main']))

                    if self.debug and self.logger:
                        self.logger.info(
                            'Stopping picamera2 to change configuration/controls')
                    self.picam2.stop()  # in case left running
                    timesheet.add('camera stopped')

                    # apply modified config
                    self.picam2.configure(capture_config)
                    timesheet.add('modified config applied')

                    if self.debug and self.logger:
                        self.logger.debug(pformat(self.picam2.camera_controls))

                    # set controls
                    if self.debug and self.logger:
                        self.logger.info(
                            'Starting picamera2 following change to configuration/controls')
                    self.picam2.start()
                    timesheet.add('camera started')

                    pc2_cap_arr = self.picam2.capture_array()
                    timesheet.add('config change array captured')

                    self.local_config_string = local_config_string
                else:
                    pc2_cap_arr = self.picam2.capture_array()
                    timesheet.add('no config change array captured')

                if self.debug:
                    self.logger.debug('pc2_cap_arr sample:' +
                                      str(pc2_cap_arr[0:10, 0:10]))

                if self.debug:
                    cap_img = Image.fromarray(pc2_cap_arr)
                    cap_img.save(
                        '/dev/shm/pc2-usb-captured-{0}.jpg'.format(fmt))

                    if self.debug and self.logger:
                        self.logger.debug(
                            'size requested: {0},{1}'.format(width_px, height_px))
                    if self.debug and self.logger:
                        self.logger.debug('array predicted: {0},{1}'.format(
                            array_height_px, array_width_px))
                    if self.debug and self.logger:
                        self.logger.debug('pc2 captured: {} {} {} {}'.format(
                            pc2_cap_arr.shape,
                            pc2_cap_arr[:height_px, :width_px].shape,
                            pc2_cap_arr[:height_px,
                                        :width_px - 1].flatten().shape,
                            pc2_cap_arr.dtype
                        ))

                # usb cameras can't do transforms
                if self.hflip and not self.vflip:
                    pc2_cap_arr = np.fliplr(pc2_cap_arr)
                    timesheet.add('hflip')

                if self.vflip and not self.hflip:
                    pc2_cap_arr = np.flipud(pc2_cap_arr)
                    timesheet.add('vflip')

                if self.vflip and self.hflip:
                    pc2_cap_arr = np.fliplr(np.flipud(pc2_cap_arr))
                    timesheet.add('h and v flip')

                # usb cameras only support rgb, not yuv
                if fmt == 'rgb':
                    pc2_cap_arr = pc2_cap_arr.astype(np.uint8)
                    timesheet.add('array converted to uint8')
                else:
                    pc2_cap_arr = vis_lib.rgb_to_gray(
                        pc2_cap_arr).astype(np.uint8)
                    timesheet.add('array converted to grayscale')

                # annotation
                if self.annotate:
                    reference_time_ms = (time.time() - time.monotonic()) * 1000
                    md = self.picam2.capture_metadata()
                    if self.debug and self.logger:
                        self.logger.debug(
                            'pc2 usb capture metadata: {0}'.format(md))

                    exposure_elapsed_time_ms = md['SensorTimestamp'] / 1000000
                    exposure_real_time_ms = reference_time_ms + exposure_elapsed_time_ms
                    exposure_real_time_fmtd = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.gmtime(exposure_real_time_ms / 1000))
                    self.annotate_text = '{0}.{1:0>3}'.format(
                        exposure_real_time_fmtd, int((exposure_real_time_ms % 1) * 1000))

                    banner_height_px = height_px // 16
                    margin_px = banner_height_px // 2
                    overlay_img = Image.new(
                        'L', (width_px - margin_px, banner_height_px))
                    overlay_img_draw = ImageDraw.Draw(overlay_img)
                    overlay_img_draw.text(
                        (0, 0), self.annotate_text, fill=255, font_size=banner_height_px)
                    if fmt == 'rgb':
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 0] = np.array(overlay_img)
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 1] = np.array(overlay_img)
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 2] = np.array(overlay_img)
                    else:
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px] = np.array(overlay_img)
                    timesheet.add('array annotated')

                end = time.time()
                elapsed = end - start
                if self.debug and self.logger:
                    self.logger.debug('Camera Snapshot time: {0:.2f} secs'.format(
                        elapsed))  # Time in seconds, e.g. 5.38091952400282

                self.logger.debug(timesheet)

            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                if self.debug and self.logger:
                    self.logger.error(
                        'Error in OpticalLusb capture: ' + str(e1) + ' on line ' + str(err_line))

                gray_img_arr = np.full((height_px, width_px), 127)
                dummy_img = Image.fromarray(gray_img_arr)
                dummy_draw = ImageDraw.Draw(dummy_img)
                dummy_draw.text((10, 10), 'Picamera II USB', font_size=32)
                if not self.linux:
                    dummy_draw.text(
                        (20, 60), 'Picamera II is only available on Linux!', font_size=20)
                dummy_draw.text((20, 110), '{0} on line {1}'.format(
                    e1, err_line), font_size=20)
                gray_img_arr = np.array(dummy_img)

                (gray_height_px, gray_width_px) = gray_img_arr.shape
                if self.debug and self.logger:
                    self.logger.debug(
                        'OpticalLusb usb capture - gray shape: {}x{}'.format(
                          (gray_width_px, gray_height_px)
                          )
                    )
                # create a yuv plain grey image
                y_array_size = array_width_px * array_height_px
                yuv_array_size = y_array_size * 1.5
                if self.debug and self.logger:
                    self.logger.debug(
                        'OpticalLusb capture - yuv_array_size: {0}'.format(yuv_array_size))

                lum_img = np.zeros((array_height_px, array_width_px), np.uint8)
                lum_img[0:gray_height_px, 0:gray_width_px] = gray_img_arr
                l_img = lum_img.reshape(y_array_size)
                if fmt == 'rgb':
                    if self.debug and self.logger:
                        self.logger.debug('3 channel output - colour')
                    pc2_cap_arr = l_img.reshape(
                        array_height_px, array_width_px)
                else:
                    pc2_cap_arr = l_img.reshape(
                        array_height_px, array_width_px)
                    if self.debug and self.logger:
                        self.logger.debug('1 channel output - gray')

            end = time.time()
            elapsed = round(end - start, 3)  # seconds

            if self.debug and self.logger:
                self.logger.debug(
                    'OpticalLusb capture - captured in {0} seconds'.format(elapsed))

            return pc2_cap_arr

        except Exception as e2:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in OpticalLusb usb capture: ' + \
                str(e2) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)


class OpticalPi(BaseCamera):

    awb_mode_list = ["Auto", "Incandescant", "Tungsten",
                     "Flourescent", "Indoor", "Daylight", "Cloudy", "Custom"]

    def __init__(self, picam2, device_index=0, debug=False, logger=None):
        try:
            self.settings = PiSettings()
            self.local_config_string = None
            BaseCamera.__init__(self)

            self.device_index = device_index
            self.debug = debug
            self.logger = logger
            self.revision = 'Pi Camera II'

            self.framerate = 0
            self._resolution = CamRes()

            # Flip Image?
            self.hflip = False
            self.vflip = False

            # set automatic white balance
            self.awb_mode = 'off'
            self.picam2 = picam2  # Picamera2()

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            err_msg = 'Error in OpticalPi.__init__: ' + \
                str(e) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(err_msg)
            else:
                print(err_msg)

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, value):
        if isinstance(value, str):
            self._resolution = CamRes(value)
        elif isinstance(value, tuple):
            self._resolution = CamRes(
                '{0:.0f}x{1:.0f}'.format(value[0], value[1]))

    @property
    def metadata(self):
        return self.picam2.capture_metadata()

    def __str__(self):
        result = ''
        result += 'resolution: ' + str(self._resolution) + '\n'
        result += 'hflip: ' + str(self.hflip) + '\n'
        result += 'vflip: ' + str(self.vflip) + '\n'
        result += 'awb_mode: {0}'.format(self.awb_mode) + '\n'

        return result

    def snap(self, cap_fmt):
        '''
            capture an image
            handle the rounding-up of image size, and cropping back down
        '''
        cam_array = None
        img_array = None

        try:

            if self.debug and self.logger:
                self.logger.debug('snap format {0}'.format(cap_fmt))

            if self.debug and self.logger:
                self.logger.debug('res: {0} type: {1}'.format(
                    self.resolution, type(self.resolution)))
            img_width_px = self.resolution.width
            img_height_px = self.resolution.height

            if self.debug and self.logger:
                self.logger.debug('snap camera resolution {0}x{1}'.format(
                    img_width_px, img_height_px))

            if cap_fmt == 'rgb':
                chans = 3
            else:
                chans = 1

            if self.debug and self.logger:
                self.logger.debug('snap {2}x{1}x{0}'.format(
                    img_height_px, img_width_px, chans))

            # snap to array
            cam_array = self.capture(cap_fmt)

            # finally crop to discard extra uninitialised pixels
            img_array = cam_array[:img_height_px, :img_width_px]

            if self.debug:
                if chans == 3:
                    self.logger.debug(
                        'snap {2}x{1}x{0}'.format(*img_array.shape))
                else:
                    self.logger.debug('snap {0}x{1}'.format(*img_array.shape))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            err_msg = 'Error in OpticalPi.snap: ' + \
                str(e) + ' on line ' + str(err_line)
            if self.logger is not None:
                self.logger.error(err_msg)
            else:
                print(err_msg)
        return img_array

    def capture(self, fmt=None):

        try:

            start = time.time()

            local_config_string = ''.join({k: str(v) for k, v in self.settings.get_settings_as_dict(
            ).items() if k not in ['client', 'queue']}.values())
            if self.debug and self.logger:
                self.logger.debug('Current config:' + str(local_config_string))
            if self.debug and self.logger:
                self.logger.debug('Previous config:' +
                                  str(self.local_config_string))

            width_px = self.resolution.width
            height_px = self.resolution.height

            # Take a frame
            try:
                start = time.time()

                if local_config_string != self.local_config_string:

                    # Take image in requested format
                    trfrm = Transform(hflip=self.hflip, vflip=self.vflip)
                    capture_config = self.picam2.create_still_configuration(
                        main={
                            "size": (width_px, height_px),
                            "format": "YUV420" if fmt == 'yuv' else "BGR888"
                        },
                        transform=trfrm,
                        buffer_count=1  # must be one to restrict lag!
                    )

                    # optimise config
                    if self.debug and self.logger:
                        self.logger.debug(
                            'Requested config:' + str(capture_config['main']))
                    self.picam2.align_configuration(capture_config)
                    if self.debug and self.logger:
                        self.logger.debug(
                            'Revised config:' + str(capture_config['main']))

                    if self.debug and self.logger:
                        self.logger.info(
                            'Stopping picamera2 to change configuration/controls')
                    self.picam2.stop()  # in case left running

                    # apply modified config
                    self.picam2.configure(capture_config)

                    # set controls

                    # Automatic White Balance
                    try:
                        if self.awb_mode is not None and self.awb_mode.lower() == 'off' and (self.redgain > 0 or self.bluegain > 0):
                            if self.debug and self.logger:
                                self.logger.debug(
                                    'picamera2 capture - enabling manual gain, disabling awb')
                            self.picam2.controls.ColourGains = (
                                self.redgain, self.bluegain)
                            self.picam2.controls.AwbEnable = 0
                            self.awb_mode = 'off'
                            pc2_awb_mode = 0  # auto
                        elif self.awb_mode is not None and self.awb_mode.lower() == 'off':
                            if self.debug and self.logger:
                                self.logger.debug(
                                    'picamera2 capture - disabling awb')
                            self.picam2.controls.AwbEnable = 0
                            pc2_awb_mode = 0  # auto
                        else:
                            if self.debug and self.logger:
                                self.logger.debug(
                                    'picamera2 capture - enabling awb, disabling manual gain')
                            self.picam2.controls.AwbEnable = 1
                            if self.awb_mode in self.awb_mode_list:
                                pc2_awb_mode = self.awb_mode_list.index(
                                    self.awb_mode)
                                if self.debug and self.logger:
                                    self.logger.debug(
                                        'picamera2 capture - using awb mode {0}'.format(pc2_awb_mode))
                            else:
                                pc2_awb_mode = 0  # auto
                                if self.debug and self.logger:
                                    self.logger.debug(
                                        'picamera2 capture - no mapping, using awb mode auto')
                        self.picam2.controls.AwbMode = pc2_awb_mode
                    except Exception:
                        pass

                    if self.debug and self.logger:
                        self.logger.info(
                            'Starting picamera2 following change to configuration/controls')
                    self.picam2.start()

                    pc2_cap_arr = self.picam2.capture_array()  # "main")
                    if self.debug:
                        cap_img = Image.fromarray(pc2_cap_arr)
                        cap_img.save('/dev/shm/captured-{0}.jpg'.format(fmt))

                        if self.debug and self.logger:
                            self.logger.debug(
                                'size requested: {0},{1}'.format(width_px, height_px))
                        if self.debug and self.logger:
                            self.logger.debug('pc2 captured: {0} {1} {2}'.format(
                                pc2_cap_arr.shape,
                                pc2_cap_arr[:height_px, :width_px].shape,
                                pc2_cap_arr[:height_px,
                                            :width_px - 1].flatten().shape
                            ))

                    self.local_config_string = local_config_string
                else:
                    pc2_cap_arr = self.picam2.capture_array()  # "main")

                # annotation
                if self.annotate:
                    reference_time_ms = (time.time() - time.monotonic()) * 1000
                    md = self.picam2.capture_metadata()
                    exposure_elapsed_time_ms = (
                        md['SensorTimestamp'] - 1000 * md['ExposureTime']) / 1000000
                    exposure_real_time_ms = reference_time_ms + exposure_elapsed_time_ms
                    exposure_real_time_fmtd = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.gmtime(exposure_real_time_ms / 1000))
                    self.annotate_text = '{0}.{1:0>3}'.format(
                        exposure_real_time_fmtd, int((exposure_real_time_ms % 1) * 1000))

                    banner_height_px = height_px // 16
                    margin_px = banner_height_px // 2
                    overlay_img = Image.new(
                        'L', (width_px - margin_px, banner_height_px))
                    overlay_img_draw = ImageDraw.Draw(overlay_img)
                    overlay_img_draw.text(
                        (0, 0), self.annotate_text, fill=255, font_size=banner_height_px)
                    if fmt == 'rgb':
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 0] = np.array(overlay_img)
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 1] = np.array(overlay_img)
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px, 2] = np.array(overlay_img)
                    else:
                        pc2_cap_arr[margin_px:banner_height_px + margin_px,
                                    margin_px:width_px] = np.array(overlay_img)

                # artificially extend camera capture time...
                extra_delay_secs = await_elapsed(
                    time.time(), start + constants.THROTTLE_CAMERA_SNAP_SECS)  # blocks
                if self.debug:
                    if extra_delay_secs > 0:
                        self.logger.debug(
                            'OpticalPi capture throttle - slept for {0} seconds'.format(extra_delay_secs))
                    else:
                        self.logger.debug(
                            'OpticalPi capture throttling not required')

                end = time.time()
                elapsed = round(end - start, 3)  # seconds
                if self.debug:
                    self.logger.debug(
                        'OpticalPi capture - captured in {0:.2f} seconds'.format(elapsed))

            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                if self.debug and self.logger:
                    self.logger.error(
                        'Error in picamera2 capture: ' + str(e1) + ' on line ' + str(err_line))

                gray_img_arr = np.full((height_px, width_px), 127)
                dummy_img = Image.fromarray(gray_img_arr)
                dummy_draw = ImageDraw.Draw(dummy_img)
                dummy_draw.text((10, 10), 'Picamera II', font_size=32)
                if not self.linux:
                    dummy_draw.text(
                        (20, 60), 'Picamera is only available on Linux!', font_size=20)
                dummy_draw.text((20, 110), '{0} on line {1}'.format(
                    e1, err_line), font_size=20)
                gray_img_arr = np.array(dummy_img)

                (gray_height_px, gray_width_px) = gray_img_arr.shape
                if self.debug:
                    print('picamera2 capture - gray shape:',
                          (gray_width_px, gray_height_px))

                # create a yuv plain grey image
                # Estimate the actual array size (accounting for rounding of the resolution)
                array_width_px = (width_px + 31) // 32 * 32
                array_height_px = (height_px + 15) // 16 * 16

                y_array_size = array_width_px * array_height_px
                yuv_array_size = y_array_size * 1.5
                if self.debug and self.logger:
                    self.logger.debug(
                        'picamera2 capture - yuv_array_size: {0}'.format(yuv_array_size))

                lum_img = np.zeros((array_height_px, array_width_px), np.uint8)
                lum_img[0:gray_height_px, 0:gray_width_px] = gray_img_arr
                l_img = lum_img.reshape(y_array_size)
                if fmt == 'rgb':
                    if self.debug and self.logger:
                        self.logger.debug('3 channel output - colour')
                    pc2_cap_arr = l_img.reshape(
                        array_height_px, array_width_px)
                else:
                    pc2_cap_arr = l_img.reshape(
                        array_height_px, array_width_px)
                    if self.debug and self.logger:
                        self.logger.debug('1 channel output - gray')

            end = time.time()
            elapsed = round(end - start, 3)  # seconds

            if self.debug and self.logger:
                self.logger.debug(
                    'picamera2 capture - captured in {0} seconds'.format(elapsed))

            return pc2_cap_arr

        except Exception as e2:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in OpticalPi capture: ' + \
                str(e2) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)