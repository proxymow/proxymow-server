import numpy as np

# specify column position/process order
process_order = 4

# define some setpoints
MIN_CONTRAST = 0.3

def assess(_contour, img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 

        calculate contrast
    '''

    # compute min and max of Y
    min_i = np.min(img_arr).astype(int)
    max_i = np.max(img_arr).astype(int)
    
    # compute contrast
    contrast = (max_i - min_i) / (max_i + min_i + 1)

    qualifies = contrast > MIN_CONTRAST
    
    tooltip = '{:.3f} is {} than {}'.format(
        contrast,
        'greater' if qualifies else 'less',
        MIN_CONTRAST
    )

    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return contrast, tooltip, qualifies