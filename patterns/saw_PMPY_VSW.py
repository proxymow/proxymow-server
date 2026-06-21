from patterns import pmpy_saw


def calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, debug):
    return pmpy_saw.calculate_route(fence_points_pc, arena_width_m, arena_length_m, cutter_dia_m, logger, debug, start_corner='SW', direction='V')
