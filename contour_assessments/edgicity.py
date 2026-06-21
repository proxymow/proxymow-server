import numpy as np
import contour_lib as cl

# specify column position/process order
process_order = 3

# define some setpoints
MAX_EDGICITY = 0.6


def assess(contour, _img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 
    '''
    c1 = cl.reduce_contour_points(contour, 36)
    c2 = np.roll(c1, -2, axis=0)
    dx = c2[:, 0] - c1[:, 0]
    dy = c2[:, 1] - c1[:, 1]
    
    angles_rad = np.arctan2(dx, dy)
    angles = np.round(np.degrees(angles_rad), 3).astype(int)
    changes = np.abs(np.diff(angles, append=angles[0])).astype(int)
    limit = 5
    mask = changes < limit
    straights = (mask).astype(int)
    
    edgicity = np.count_nonzero(straights) / len(c2)
    
    qualifies = edgicity < MAX_EDGICITY
    
    tooltip = '{:.3f} is {} than {}'.format(
        edgicity,
        'less' if qualifies else 'greater',
        MAX_EDGICITY
    )
    
    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return edgicity, tooltip, qualifies