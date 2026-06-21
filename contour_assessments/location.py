import numpy as np

# specify column position/process order
process_order = 1

def assess(contour, _img_arr, origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 

        calculate centre of mass
    '''

    x = contour[:,0]
    y = contour[:,1]
    g = (x[:-1]*y[1:] - x[1:]*y[:-1])
    A = 0.5*g.sum()
    cx = ((x[:-1] + x[1:])*g).sum()
    cy = ((y[:-1] + y[1:])*g).sum()
    centre_of_mass_arr = (1./(6*A)*np.array([cx,cy])).astype(int) + origin
    location = '({1}, {0})px'.format(*centre_of_mass_arr)

    qualifies = True # don't filter just inform
    
    tooltip = location
    
    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return location, tooltip, qualifies