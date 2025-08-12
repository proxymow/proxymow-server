from enum import Enum, auto


class Movement():
    '''
        represents an atomic action by the robot
            defined as left speed [%], right speed [%], duration [ms]
        requires a preset axle track [m] and velocity [mps]
            so it can be added to a Pose e.g. p2 = p1 + m
    '''
    axle_track_m = 0
    velocity_full_speed_mps = 0

    @classmethod
    def get_movement_code(cls, left_speed, right_speed):
        code = None
        try:
            nil = (left_speed is None) or (right_speed is None)
            if not nil:
                stop = (left_speed == 0) and (right_speed == 0)
                r1w = left_speed * right_speed == 0
                r1w_cw = r1w and (left_speed > right_speed)
                r1w_ccw = r1w and (left_speed < right_speed)
                r2w_cw = (left_speed > 0 and right_speed <
                          0) and not (r1w_cw or r1w_ccw or nil)
                r2w_ccw = (left_speed < 0 and right_speed >
                           0) and not (r1w_cw or r1w_ccw or nil)
                fwd = (left_speed > 0 and right_speed > 0)
                rev = (left_speed < 0 and right_speed < 0)

            if nil:
                code = MovementCode.NIL
            elif stop:
                code = MovementCode.STOP
            elif r1w_cw:
                code = MovementCode.R1W_CW
            elif r1w_ccw:
                code = MovementCode.R1W_CCW
            elif r2w_cw:
                code = MovementCode.R2W_CW
            elif r2w_ccw:
                code = MovementCode.R2W_CCW
            elif fwd:
                code = MovementCode.FWD
            elif rev:
                code = MovementCode.REV
        except Exception:
            pass
        return code

    @classmethod
    def init(cls, axle_track_m, velocity_full_speed_mps):
        '''
            Class Initialisation
        '''
        cls.axle_track_m = axle_track_m
        cls.velocity_full_speed_mps = velocity_full_speed_mps

    def __init__(self, left_speed_pc, right_speed_pc, duration_ms):
        try:
            self.left_speed_pc = left_speed_pc
            self.left_speed_unit = self.left_speed_pc / 100
            self.right_speed_pc = right_speed_pc
            self.right_speed_unit = self.right_speed_pc / 100
            self.duration_ms = duration_ms
            self.duration_s = duration_ms / 1000
            self.distance_m = max(self.left_speed_unit, self.right_speed_unit) * \
                self.duration_s * self.velocity_full_speed_mps
        except Exception:
            pass

    def __str__(self):
        return '[{0}%, {1}%, {2}ms] axle_track: {3}m velocity: {4}m/s dist: {5}m'.format(
            self.left_speed_pc,
            self.right_speed_pc,
            self.duration_ms,
            self.axle_track_m,
            round(self.velocity_full_speed_mps, 2),
            self.distance_m
        )


class MovementCode(Enum):
    NIL = auto()
    STOP = auto()
    R1W_CW = auto()
    R1W_CCW = auto()
    R2W_CW = auto()
    R2W_CCW = auto()
    FWD = auto()
    REV = auto()
