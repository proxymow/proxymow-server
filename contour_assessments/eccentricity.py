import numpy as np
import contour_lib as cl

# specify column position/process order
process_order = 5

# define some setpoints
MIN_ECCENTRICITY = 1.5
MAX_ECCENTRICITY = 10.0


def assess(contour, _img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 

        calculate standard deviation of radials
    '''

    # find centre of mass
    cy, cx = cl.center_of_mass(contour)

    radials = np.hypot(contour[:, 0] - cy, contour[:, 1] - cx)

    ecc = np.max(radials) / np.min(radials)

    qualifies = bool(MIN_ECCENTRICITY <= ecc <= MAX_ECCENTRICITY)
    tooltip = '{:.3f} is {} {} and {}'.format(
        ecc,
        'between' if qualifies else 'beyond',
        MIN_ECCENTRICITY,
        MAX_ECCENTRICITY
    )
    
    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return ecc, tooltip, qualifies