import contour_lib as cl

# specify column position/process order
process_order = 7

# define some setpoints
MIN_CONVEXITY = 1.0

def assess(contour, _img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 

        check centre of mass lies inside contour
    '''

    # find centre of mass
    cy, cx = cl.center_of_mass(contour)

    pip_sum = cl.is_inside_polygon((cy, cx), contour, validBorder=False)
    
    convexity = round(abs(pip_sum), 3)
    qualifies = abs(pip_sum) > MIN_CONVEXITY
    tooltip = '{:.3f} is {} than {}'.format(
        convexity,
        'greater' if qualifies else 'less',
        MIN_CONVEXITY
    )
        
    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return convexity, tooltip, qualifies