import numpy as np

# specify column position/process order
process_order = 4

# define some setpoints
MIN_CONTRAST = 0.15

def assess(_contour, img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 

        calculate contrast
    '''

    # compute contrast
    std = np.std(img_arr)
    rng = np.ptp(img_arr)

    contrast = std/rng
    qualifies = contrast > MIN_CONTRAST

    tooltip = '{:.3f} / {} = {:.3f} is {} than {}'.format(
        std,
        rng,
        contrast,
        'greater' if qualifies else 'less',
        MIN_CONTRAST
    )

    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return contrast, tooltip, qualifies
