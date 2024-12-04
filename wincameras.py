import cv2
import sys
import numpy as np
import time
from timeit import default_timer as timer
from PIL import Image, ImageDraw

from cameras import USBCamera
from forms.settings import WusbSettings


class OpticalWusb(USBCamera):

    def __init__(self, device_index, debug=False, logger=None):
        self.settings = WusbSettings()
        super().__init__()
        self.device_index = device_index
        self.debug = debug
        self.logger = logger
        self.revision = 'WinCamera'
        self.video_capture = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)

    def snap(self, fmt=None):
        '''
            Capture an image from the camera, and return it.
        '''
        try:

            start = time.time()

            if self.debug and self.logger:
                self.logger.debug(
                    'WinCamera capture - incoming fmt: {}'.format(fmt))

            def_width_px = self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            def_height_px = self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if self.debug and self.logger:
                self.logger.debug(
                    "WinCamera capture - Frame default resolution: {0}x{1}".format(def_width_px, def_height_px))

            # Obtain the requested image size
            img_width_px = int(self.resolution.split('x')[0])
            img_height_px = int(self.resolution.split('x')[1])

            # force webcams to 800x600 - then resize to what I need...
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            if self.debug and self.logger:
                self.logger.debug("WinCamera capture - Frame resolution set to: (" + str(self.video_capture.get(
                    cv2.CAP_PROP_FRAME_WIDTH)) + "; " + str(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ")")

            # Take a frame
            threshold = 0  # 0.02 for lag-free capture
            elapsed = 0
            discards = 0
            while elapsed <= threshold and discards < 10:
                start_timer = timer()
                status, frame = self.video_capture.read()
                end_timer = timer()
                elapsed = end_timer - start_timer
                if self.debug and self.logger:
                    # Time in seconds, e.g. 5.38091952400282
                    self.logger.debug(
                        'Camera Snapshot time: ' + str(elapsed) + ' discarded: ' + str(discards))
                discards += 1

            if self.debug and self.logger:
                self.logger.debug('WinCamera capture status: ' + str(status))

            # resize 800x600 to requested resolution
            col_img_arr = cv2.resize(frame, (img_width_px, img_height_px))
            if self.debug and self.logger:
                self.logger.debug(
                    'WinCamera capture - colour shape: {2}x{1}x{0}'.format(*col_img_arr.shape))

            if self.hflip and not self.vflip:
                col_img_arr = cv2.flip(col_img_arr, 1)

            if self.vflip and not self.hflip:
                col_img_arr = cv2.flip(col_img_arr, 0)

            if self.vflip and self.hflip:
                col_img_arr = cv2.flip(col_img_arr, -1)

            # annotation
            if self.annotate:
                col_img = Image.fromarray(col_img_arr)
                img_draw = ImageDraw.Draw(col_img)  # refresh
                cur_time = time.time()
                now_fmtd = (
                    time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(cur_time)) +
                    '.{0:0>3}'.format(int((cur_time % 1) * 1000))
                )

                banner_height_px = img_height_px // 16
                _margin_px = banner_height_px // 2
                img_draw.text((0, 0), now_fmtd, fill=255,
                              font_size=banner_height_px)
                col_img_arr = np.array(col_img)

            if fmt == 'yuv':

                out_img = cv2.cvtColor(col_img_arr, cv2.COLOR_BGR2GRAY)
                if self.debug:
                    cv2.imwrite("web_cam_debug_grey.png", out_img)

            else:

                out_img = col_img_arr.astype(np.uint8)
                if self.debug:
                    cv2.imwrite("web_cam_debug_col.png", out_img)

            end = time.time()
            elapsed = round(end - start, 3)  # seconds

            if self.debug and self.logger:
                self.logger.info(
                    'WinCamera capture - captured in {} seconds'.format(elapsed))

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            msg = 'Error in WinCamera snap: ' + \
                str(e) + ' on line ' + str(err_line)
            if self.logger:
                self.logger.error(msg)
            else:
                print(msg)

        return out_img
