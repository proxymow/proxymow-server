import skimage.morphology as skm

'''
    LOG_MAX_BYTES - maximum file size before log rotates
'''
LOG_MAX_BYTES = 10000000  # 10Mb

'''
    LOG_BACKUP_COUNT - number of log-file backups
'''
LOG_BACKUP_COUNT = 12

'''
    RESOLUTIONS - pairs of 4:3 width, height pixel tuples
'''
# Optimal pc2 resolutions for 64 pixel alignment
RESOLUTIONS = [(3280, 2464), (3264, 2448), (2592, 1944), (2560, 1920), (2048, 1536), (1792, 1344), (1600, 1200),
               (1536, 1152), (1296, 972), (1280, 960), (1280, 800), (1024, 768), (512, 384)]

'''
    CAPPED_IMAGE_RESOLUTION - the maximum size for display images
'''
CAPPED_IMAGE_RESOLUTION = (800, 600)

'''
    PLATFORM_AGNOSTIC_DEVICES - boolean enabling windows camera devices to be managed on linux and vice versa
'''
PLATFORM_AGNOSTIC_DEVICES = True

'''
    NOT_FOUND_RESET_COUNT - count to be exceeded before resetting visual lock
'''
NOT_FOUND_RESET_COUNT = 15  # 99 to disable

'''
    SCORE_THRESHOLD - score above which we are confident target is the mower 
'''
SCORE_THRESHOLD = 54

'''
    VIRTUAL_NOISE - 0 Off, 1 Tracking Around, 2 Random Fixed, 3 Fixed, 4 random ellipse scatter, 5 bot parts, 6 animals
'''
VIRTUAL_NOISE = 0

'''
    VIRTUAL_OBSTACLE_LINE_WIDTH - line width of the virtual obstacle in pixels, e.g. 32 or zero to hide
'''
VIRTUAL_OBSTACLE_LINE_WIDTH = 0

'''
    DISPLAY_VIRTUAL_LAWN_BOLLARDS - add some calibration bollards for calibration experiments
'''
DISPLAY_VIRTUAL_LAWN_BOLLARDS = False


'''
    BLUR_SIGMA - value for gaussian blur sigma, set to zero to disable blur stage
'''
BLUR_SIGMA = 1

'''
    CLOSING_FOOTPRINT - structuring element for closing filter, set to None to disable closing stage
'''
if hasattr(skm, 'footprint_rectangle'):
    CLOSING_FOOTPRINT = skm.footprint_rectangle((3, 3))
else:
    CLOSING_FOOTPRINT = skm.rectangle(3, 3)

'''
    FENCE_MASKING - boolean indicating whether to mask beyond fence
'''
FENCE_MASKING = True

'''
    MAX_SNAPSHOT_ID - maximum snapshot id before rolling around
'''
MAX_SNAPSHOT_ID = 9999

'''
    RNF_MITIGATION - make an assumption about the pose if Robot Not Found
'''
RNF_MITIGATION = True

'''
    ARCHIVE_IMAGE_RATE_SECS - rate at which archive images are captured (zero to disable)
'''
ARCHIVE_IMAGE_RATE_SECS = 10

'''
    ARCHIVE_IMAGE_MAX_COUNT - maximum number before wrapping
'''
ARCHIVE_IMAGE_MAX_COUNT = 1000

'''
    DEBUG_LOCATE_LEVEL - level at which to debug locating
    0 - no debugging
    1 - basic debugging
    2 - full debugging
    3 - verbose
    4 - more verbose
'''
DEBUG_LOCATE_LEVEL = 1

'''
    DEBUG_SAVE_IMAGE_LEVEL - level for which images will be saved for debugging
    0 - disabled
    1 - low resolution prospects and filter pipeline output
    2 - lo-res prospects
    3 - hi-res viewports
    4 - hi-res pipeline
    5 - projection plots
    
    use -1, -3, etc. to debug just that level 
'''
DEBUG_SAVE_IMAGE_LEVEL = 0

'''
    DEBUG_SAVE_IMAGE_GENERATIONS - number of generations of images saved for debugging
'''
DEBUG_SAVE_IMAGE_GENERATIONS = 3

'''
    DEBUG_IMAGE_QUALITY - quality for debugging (%)
'''
DEBUG_IMAGE_QUALITY = 50

'''
    DARK_ZONE_FENCE_BUFFER_PERCENT - buffer zone beyond fence as a percentage
'''
DARK_ZONE_FENCE_BUFFER_PERCENT = 10  # make this as small as possible! 

'''
    DARK_ZONE_MIN_SEGMENT_PERCENT - minimum segment length for defining dark zone boundary, as percentage of arena
'''
DARK_ZONE_MIN_SEGMENT_PERCENT = 1.75

'''
    MINIMUM_CONTOUR_THRESHOLD - minimum intensity threshold (0..1) below which contour finding won't be attempted 
'''
MINIMUM_CONTOUR_THRESHOLD = 0.01

'''
    MAXIMUM_VIEWPORT_FOOTPRINT - maximum footprint area (0..100%) above which viewports can't be mower 
'''
MAXIMUM_VIEWPORT_FOOTPRINT = 15

'''
    LORES_CONTOUR_MINIMUM_POINT_COUNT - minimum point count for lo-res contours
'''
LORES_CONTOUR_MINIMUM_POINT_COUNT = 10

'''
    HIRES_CONTOUR_MINIMUM_POINT_COUNT - minimum point count for hi-res contours
'''
HIRES_CONTOUR_MINIMUM_POINT_COUNT = 35

'''
    CONTOUR_POINT_COUNT_THRESHOLD - proportion of mid-range
'''
CONTOUR_POINT_COUNT_THRESHOLD = 0.175

'''
    CONTOUR_TABLE_MAX_ROWS - maximum rows to display in table
'''
CONTOUR_TABLE_MAX_ROWS = 12

'''
    MOWER_TELEMETRY_PERIOD_SECS - period between requests for mower telemetry
'''
MOWER_TELEMETRY_PERIOD_SECS = 10

'''
    LANDING_TIME_OVERHEAD_SECS  - additional time added to duration when predicting landing
                                - needs to allow for any velocity ramping in mower code
'''
LANDING_TIME_OVERHEAD_SECS = 1.5

'''
    ENABLE_CONTOUR_LOGGING  [True | False]
'''
ENABLE_CONTOUR_LOGGING = True

'''
    UI_AUTO_FREEZE_MS - Automatically freeze certain user interface features to minimise server load
'''
UI_AUTO_FREEZE_MS = 600000 # 5 mins

'''
    NAVIGATOR_AUTO_FREEZE_MS - Automatically freeze navigator to minimise server load
'''
NAVIGATOR_AUTO_FREEZE_MS = 300000 # 5 mins

'''
    FROZEN_SPEED_THRESHOLD_PERCENT - absolute speed threshold below which movement can't be considered frozen 
'''
FROZEN_SPEED_THRESHOLD_PERCENT = 50

'''
    FROZEN_DISTANCE_THRESHOLD_METRES - distance threshold below which movement is considered frozen 
'''
FROZEN_DISTANCE_THRESHOLD_METRES = 0.044

'''
    FROZEN_ANGLE_THRESHOLD_DEGREES - angular threshold below which movement is considered frozen 
'''
FROZEN_ANGLE_THRESHOLD_DEGREES = 2.0

'''
    ANIMAL_MIN_PT_COUNT - contour point count above which contours are assumed to be animals
'''
ANIMAL_MIN_PT_COUNT = -1  # 150 looks reasonable, -1 to disable because it doesn't work!

'''
    MINIMUM_INTER_NODE_DISTANCE_M - minimum distance between route nodes for a node to qualify
'''
MINIMUM_INTER_NODE_DISTANCE_M = 0.05

'''
    ESCALATION_ENABLED - [True | False]

'''
ESCALATION_ENABLED = True

'''
    Number of additional rungs in the escalation ladder (excluding bottom starting rung)
'''
NUM_ESCALATION_RUNGS = 3

'''
    ESCALATION_DURATION_FACTOR - [0.0] reduce duration linearly with escalating speeds, [1.0] no reduction
'''
ESCALATION_DURATION_FACTOR = 2.0

'''
    WAIT_FOR_CAMERA_SECS - delay before camera snap to compensate for lag
    For most cameras this should be zero, but web-cams on windows may need up to 5 seconds
'''
WAIT_FOR_CAMERA_SECS = 0.0

'''
    THROTTLE_CAMERA_SNAP_SECS - throttle camera snap seconds
'''
THROTTLE_CAMERA_SNAP_SECS = 0.75  # 1.5 to simulate usb speeds

'''
    RESET_LAST_VISITED_NODE_ON_PROFILE_CHANGE - Flag to indicate last visited node will be reset
'''
RESET_LAST_VISITED_NODE_ON_PROFILE_CHANGE = False

'''
    RESIZE_POSE_TO_VIEWPORT - scale factor to grow pose extent to tracking viewport
'''
RESIZE_POSE_TO_VIEWPORT = 5.0

'''
    OVERLAY_EXTRAPOLATED_POSE - overlay extrapolated pose on arena image
'''
OVERLAY_EXTRAPOLATED_POSE = False

'''
    CLOSE_TO_HOME_RADIUS_M - distance below which rotations towards destination are unsafe
'''
CLOSE_TO_HOME_RADIUS_M = 0.1

'''
    DIGITAL_SHADOW_DELTA_INTENSITY - amount by which to reduce intensity
     of lower half of analysis array.  e.g. 192, set to zero to disable
'''
DIGITAL_SHADOW_DELTA_INTENSITY = 0

'''
    VISUAL_POSE_HISTORY - display kite tails
'''
VISUAL_POSE_HISTORY = True