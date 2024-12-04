from PIL import ImageDraw
import math
import sys
import numpy as np


class DashedImageDraw(ImageDraw.ImageDraw):

    def thick_line(self, xy, direction, fill=None, width=0):
        # xy: Sequence of 2-tuples like [(x, y), (x, y), ...]
        # direction: Sequence of 2-tuples like [(x, y), (x, y), ...]
        if xy[0] != xy[1]:
            self.line(xy, fill=fill, width=width)
        else:
            x1, y1 = xy[0]
            dx1, dy1 = direction[0]
            dx2, dy2 = direction[1]
            if dy2 - dy1 < 0:
                x1 -= 1
            if dx2 - dx1 < 0:
                y1 -= 1
            if dy2 - dy1 != 0:
                if dx2 - dx1 != 0:
                    k = -(dx2 - dx1) / (dy2 - dy1)
                    a = 1 / math.sqrt(1 + k ** 2)
                    b = (width * a - 1) / 2
                else:
                    k = 0
                    b = (width - 1) / 2
                x3 = x1 - math.floor(b)
                y3 = y1 - int(k * b)
                x4 = x1 + math.ceil(b)
                y4 = y1 + int(k * b)
            else:
                x3 = x1
                y3 = y1 - math.floor((width - 1) / 2)
                x4 = x1
                y4 = y1 + math.ceil((width - 1) / 2)
            self.line([(x3, y3), (x4, y4)], fill=fill, width=1)
        return

    def dashed_line(self, xy, dash=(2, 2), fill=None, width=0):
        try:
            for i in range(len(xy) - 1):
                x1, y1 = xy[i]
                x2, y2 = xy[i + 1]

                # obtain mark and space from dash
                mark_length = dash[0]
                space_length = dash[1]

                # using x1..x2 and y1..y2 construct triangle
                line_length_x = x2 - x1
                line_length_y = y2 - y1
                line_length = np.hypot(line_length_x, line_length_y)
                if line_length > 0:
                    slope_ratio = mark_length / line_length

                    # we need mark, space, mark, space, mark
                    shortened_line_length = line_length - mark_length  # up to final space
                    shortened_mark_length_x = slope_ratio * line_length_x
                    shortened_mark_length_y = slope_ratio * line_length_y

                    # x1 extended is x1 plus a mark
                    x1e, y1e = x1 + shortened_mark_length_x, y1 + shortened_mark_length_y
                    # x2 shortened is x2 - mark
                    x2s, y2s = x2 - shortened_mark_length_x, y2 - shortened_mark_length_y
                    num_slots = math.ceil(
                        shortened_line_length / (mark_length + space_length))
                    starts_x = np.linspace(x1, x2s, num=num_slots + 1)
                    starts_y = np.linspace(y1, y2s, num=num_slots + 1)
                    ends_x = np.linspace(x1e, x2, num=num_slots + 1)
                    ends_y = np.linspace(y1e, y2, num=num_slots + 1)

                    for line_index in range(len(starts_x)):
                        start_x = starts_x[line_index]
                        start_y = starts_y[line_index]
                        end_x = ends_x[line_index]
                        end_y = ends_y[line_index]
                        self.line((start_x, start_y, end_x, end_y),
                                  fill=fill, width=width)

        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            print('Error in dashed_image_draw.dashed_line: ' +
                  str(e) + ' on line ' + str(err_line))

    def dashed_rectangle(self, xy, dash=(2, 2), outline=None, width=0):
        # xy - Sequence of [(x1, y1), (x2, y2)] where (x1, y1) is top left
        # corner and (x2, y2) is bottom right corner
        x1, y1 = xy[0]
        x2, y2 = xy[1]
        halfwidth1 = math.floor((width - 1) / 2)
        halfwidth2 = math.ceil((width - 1) / 2)
        min_dash_gap = min(dash[1::2])
        end_change1 = halfwidth1 + min_dash_gap + 1
        end_change2 = halfwidth2 + min_dash_gap + 1
        odd_width_change = (width - 1) % 2
        self.dashed_line([(x1 - halfwidth1, y1), (x2 - end_change1, y1)],
                         dash, outline, width)
        self.dashed_line([(x2, y1 - halfwidth1), (x2, y2 - end_change1)],
                         dash, outline, width)
        self.dashed_line([(x2 + halfwidth2, y2 + odd_width_change),
                          (x1 + end_change2, y2 + odd_width_change)],
                         dash, outline, width)
        self.dashed_line([(x1 + odd_width_change, y2 + halfwidth2),
                          (x1 + odd_width_change, y1 + end_change2)],
                         dash, outline, width)
        return
