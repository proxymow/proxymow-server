import numpy as np
from contour_lib import reduce_contour_points

# specify column position/process order
process_order = 6

# define some setpoints
MAX_INTENSITY_MAD = 100.0

def assess(contour, img_arr, _origin):
    '''
        assess function accepts a local contour and matching raw image array
        array n*2 in y, x coordinate order 

        calculate standard deviation of intensity of radial points
    '''
    # reduce point count
    c_red = reduce_contour_points(contour, 10)
    
    # find centroid
    cy, cx = np.mean(contour, axis=0)
        
    finish_y = c_red[:, 0]
    finish_x = c_red[:, 1]
    start_y = np.full_like(finish_y, cy)
    start_x = np.full_like(finish_x, cx)
    
    # calculate coordinates on line from start to finish
    num_points = 6
    xvalues = np.linspace(start_x, finish_x, num_points, endpoint=False)[:-2].astype(int).flatten()
    yvalues = np.linspace(start_y, finish_y, num_points, endpoint=False)[:-2].astype(int).flatten()
    
    # bolt x and y back together
    yxvalues = np.dstack((yvalues, xvalues))[0]
    
    # only need unique pairs
    uyxvalues = np.unique(yxvalues, axis=0) # returns the sorted unique elements of an array
    zvalues = img_arr[uyxvalues[:, 0], uyxvalues[:, 1]].astype(int)
    
    # sd not ideal when there are bad outliers
    # sd = np.std(zvalues) / 255
    
    # median absolute deviation
    mad = np.median(np.absolute(zvalues - np.median(zvalues)))
    qualifies = mad < MAX_INTENSITY_MAD
    
    tooltip = '{:.3f} is {} than {}'.format(
        mad,
        'less' if qualifies else 'greater',
        MAX_INTENSITY_MAD
    )

    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return mad, tooltip, qualifies