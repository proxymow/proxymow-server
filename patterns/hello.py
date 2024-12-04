import sys
from destination import Attitude


def calculate_route(_fence_points_pc, _arena_width_m, _arena_length_m, _cutter_dia_m, logger):

    # calculate the route that mows Hello {World}
    fence_polygon_pts_pc = []

    # define routes for each letter
    # font_size 100%
    # all characters start at (0,0) and finish at (100, 0)
    gw = 60  # glyph width
    gh = 70  # glyph height
    hgh = gh / 2
    # text_dict = {
    #     'H': [(0, 0), (0, gh), (0, hgh), (gw, hgh), (gw, gh), (gw, 0), (100, 0)],
    #     'E': [(0, 0), (0, gh), (gw, gh), (0, gh), (0, hgh), (gw, hgh), (0, hgh), (0, 0), (gw, 0), (100, 0)],
    #     'L': [(0, 0), (0, gh), (0, 0), (gw, 0), (100, 0)],
    #     'O': [(0, 0), (gw, 0), (gw, gh), (0, gh), (0, 0), (gw, 0), (100, 0)]
    # }
    # we now have the technology!
    advanced_text_dict = {
        'H': [
            (0, 0, Attitude.FWD_DRIVE),
            (0, gh, Attitude.FWD_MOW),
            (0, hgh, Attitude.REV_DRIVE),
            (gw, hgh, Attitude.FWD_MOW),
            (gw, gh, Attitude.FWD_MOW),
            (gw, 0, Attitude.REV_MOW),
            (100, 0, Attitude.FWD_DRIVE)
        ],
        'E': [
            (0, 0, Attitude.FWD_DRIVE),
            (0, gh, Attitude.FWD_MOW),
            (gw, gh, Attitude.FWD_MOW),
            # (0, gh, Attitude.DEFAULT),
            (0, hgh, Attitude.REV_DRIVE),
            (gw, hgh, Attitude.FWD_MOW),
            # (0, hgh, Attitude.DEFAULT),
            (0, 0, Attitude.REV_DRIVE),
            (gw, 0, Attitude.FWD_MOW),
            (100, 0, Attitude.FWD_DRIVE)
        ],
        'L': [
            (0, 0, Attitude.FWD_DRIVE),
            (0, gh, Attitude.FWD_MOW),
            (0, 0, Attitude.REV_DRIVE),
            (gw, 0, Attitude.FWD_MOW),
            (100, 0, Attitude.FWD_DRIVE)
        ],
        'O': [
            (0, 0, Attitude.FWD_DRIVE),
            (gw, 0, Attitude.FWD_MOW),
            (gw, gh, Attitude.FWD_MOW),
            (0, gh, Attitude.FWD_MOW),
            (0, 0, Attitude.FWD_MOW),
            # (gw, 0, Attitude.DEFAULT),
            (100, 0, Attitude.FWD_DRIVE)
        ]
    }
    text_message = 'HELLO'
    origin_pc = (25, 30)
    font_size_pc = (10, 20)
    try:
        for i, c in enumerate(text_message):
            glyphs_pc = advanced_text_dict[c]
            glyphs_arena_pc = [(
                (p[0] * font_size_pc[0] / 100) +
                (i * font_size_pc[0]) + origin_pc[0],
                (p[1] * font_size_pc[1] / 100) + origin_pc[1],
                p[2]) for p in glyphs_pc]
            fence_polygon_pts_pc.extend(glyphs_arena_pc)

    except Exception as e:
        err_line = sys.exc_info()[-1].tb_lineno
        logger.error('Error in route calculation: ' +
                     str(e) + ' on line ' + str(err_line))

    return fence_polygon_pts_pc
