import numpy as np

# specify column position/process order
process_order = 2

# define some setpoints
MIN_ASPECT_RATIO = 0.325
MAX_ASPECT_RATIO = 1.1

def assess(contour, _img_arr, _origin):
    '''
        assess function accepts a contour and raw image array
        array n*2 in y, x coordinate order 
    '''
    # 1. Centre the points
    mean = np.mean(contour, axis=0)
    centered_points = contour - mean

    # 2. Extract X and Y coordinates of the contour
    x = centered_points[:, 1]
    y = centered_points[:, 0]
    
    # 3. Define the line of symmetry extending through the centre
    radials = np.hypot(x, y)
    max_radial_y, max_radial_x = centered_points[np.argmax(radials)] * [-1, 1]
    if max_radial_x == 0: max_radial_x = 0.001
    rot_matrix = np.array([
        [max_radial_y / max_radial_x , -1], 
        [-1, -max_radial_y / max_radial_x]
        ]
    )
    # 4. Rotate points to align with the axis of symmetry
    # This aligns the data so we can use standard min/max
    rotated_points = centered_points @ rot_matrix
    
    # 5. Find the min and max in this rotated coordinate system
    min_p = np.min(rotated_points, axis=0)
    max_p = np.max(rotated_points, axis=0)
    
    # 6. Find rotated aspect ratio
    box_dimensions = max_p - min_p

    # 7. Calculate aspect ratio (width / height)
    # Ensure it's not dividing by zero
    width, height = min(box_dimensions), max(box_dimensions)
    if height == 0:
        aspect_ratio = 0
    else:
        aspect_ratio = width / height

    qualifies = MIN_ASPECT_RATIO < aspect_ratio < MAX_ASPECT_RATIO
    tooltip = '{:.3f} is {} {} and {}'.format(
        aspect_ratio,
        'between' if qualifies else 'beyond',
        MIN_ASPECT_RATIO,
        MAX_ASPECT_RATIO
    )
        
    # return a tuple of analogue-measure, tooltip, boolean-assessment
    return aspect_ratio, tooltip, qualifies