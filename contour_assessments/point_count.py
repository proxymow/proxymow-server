# specify column position/process order
process_order = 0

def assess(contour, _img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 
    '''
    
    pt_count = len(contour)
    qualifies = True
    
    # return a tuple of measure, units, assessment
    return pt_count, '{} points'.format(pt_count), qualifies