from html_tool_pane import HtmlToolPane
from tool_pane_tool import ToolPaneButton, ToolPaneDropdown, ToolPaneNumber, ToolPaneBatteryIndicator, \
    ToolPaneIndicator, ToolPaneNewline, ToolPaneGap, ToolPaneReadout, ToolPaneLabel, \
    ToolPaneSlide

# icons
save_svg = '<svg viewBox="0 0 24 24">'
save_svg += '<path d="M21 0h-21v24h24v-21l-3-3zM12 3h3v6h-3v-6zM21 21h-18v-18h1.5v7.5h13.5v-7.5h1.757l1.243 1.243v16.757z"></path>'
save_svg += '</svg>'

freeze_svg = '<svg viewBox="0 0 24 24">'
freeze_svg += '<path d="M3 3h7.5v18h-7.5zM13.5 3h7.5v18h-7.5z"></path>'
freeze_svg += '</svg>'

plus_svg = '<svg viewBox="0 0 24 24">'
plus_svg += '<path d="M23.25 9h-8.25v-8.25c0-0.414-0.336-0.75-0.75-0.75h-4.5c-0.414 0-0.75 0.336-0.75 0.75v8.25h-8.25c-0.414 0-0.75 0.336-0.75 0.75v4.5c0 0.414 0.336 0.75 0.75 0.75h8.25v8.25c0 0.414 0.336 0.75 0.75 0.75h4.5c0.414 0 0.75-0.336 0.75-0.75v-8.25h8.25c0.414 0 0.75-0.336 0.75-0.75v-4.5c0-0.414-0.336-0.75-0.75-0.75z"></path>'
plus_svg += '</svg>'

minus_svg = '<svg viewBox="0 0 24 24">'
minus_svg += '<path d="M0 9.75v4.5c0 0.414 0.336 0.75 0.75 0.75h22.5c0.414 0 0.75-0.336 0.75-0.75v-4.5c0-0.414-0.336-0.75-0.75-0.75h-22.5c-0.414 0-0.75 0.336-0.75 0.75z"></path>'
minus_svg += '</svg>'

left_svg = '<svg viewBox="0 0 24 24">'
left_svg += '<path d="M0.75 12l11.25 11.25v-6.75h12v-9h-12v-6.75z"></path>'
left_svg += '</svg>'

right_svg = '<svg viewBox="0 0 24 24">'
right_svg += '<path d="M23.25 12l-11.25-11.25v6.75h-12v9h12v6.75z"></path>'
right_svg += '</svg>'

up_svg = '<svg viewBox="0 0 24 24">'
up_svg += '<path d="M12 0.75l-11.25 11.25h6.75v12h9v-12h6.75z"></path>'
up_svg += '</svg>'

down_svg = '<svg viewBox="0 0 24 24">'
down_svg += '<path d="M12 23.25l11.25-11.25h-6.75v-12h-9v12h-6.75z"></path>'
down_svg += '</svg>'

all_svg = '<svg viewBox="0 0 24 24" fill="black">'
all_svg += '<path d="M5,5h14v14h-14z" fill="none" stroke="black"/>'
all_svg += '<circle cx="5" cy="5" r="5" />'
all_svg += '<circle cx="19" cy="5" r="5" />'
all_svg += '<circle cx="19" cy="19" r="5" />'
all_svg += '<circle cx="5" cy="19" r="5" />'
all_svg += '</svg>'

none_svg = '<svg viewBox="0 0 24 24" fill="gray">'
none_svg += '<path d="M5,5h14v14h-14z" fill="none" stroke="black"/>'
none_svg += '<circle cx="5" cy="5" r="5" />'
none_svg += '<circle cx="19" cy="5" r="5" />'
none_svg += '<circle cx="19" cy="19" r="5" />'
none_svg += '<circle cx="5" cy="19" r="5" />'
none_svg += '</svg>'

sel_svg = '<svg viewBox="0 0 24 24" fill="gray">'
sel_svg += '<path d="M5,5h14v14h-14z" fill="none" stroke="black"/>'
sel_svg += '<circle cx="5" cy="5" r="5" fill="black"/>'
sel_svg += '<circle cx="19" cy="5" r="5" />'
sel_svg += '<circle cx="19" cy="19" r="5" />'
sel_svg += '<circle cx="5" cy="19" r="5" />'
sel_svg += '</svg>'

del_svg = '<svg viewBox="0 0 24 24" stroke-width="2">'
del_svg += '<circle cx="12" cy="12" r="11" fill="none" stroke="black" />'
del_svg += '<path d="M7,7L17,17M17,7L7,17" stroke="black" />'
del_svg += '</svg>'

ext_svg = '<svg viewBox="0 0 24 24" fill="gray">'
ext_svg += '<path d="M5,5h14v14h-14z" fill="none" stroke="black"/>'
ext_svg += '<circle cx="5" cy="5" r="5" fill="black"/>'
ext_svg += '<circle cx="19" cy="5" r="5" fill="black"/>'
ext_svg += '<circle cx="19" cy="19" r="5" />'
ext_svg += '<circle cx="5" cy="19" r="5" />'
ext_svg += '</svg>'

cam_svg = '<svg viewBox="0 0 24 24">'
cam_svg += '<path d="M7.125 14.25c0 2.692 2.183 4.875 4.875 4.875s4.875-2.183 4.875-4.875-2.183-4.875-4.875-4.875-4.875 2.183-4.875 4.875zM22.5 6h-5.25c-0.375-1.5-0.75-3-2.25-3h-6c-1.5 0-1.875 1.5-2.25 3h-5.25c-0.825 0-1.5 0.675-1.5 1.5v13.5c0 0.825 0.675 1.5 1.5 1.5h21c0.825 0 1.5-0.675 1.5-1.5v-13.5c0-0.825-0.675-1.5-1.5-1.5zM12 20.906c-3.676 0-6.656-2.98-6.656-6.656s2.98-6.656 6.656-6.656c3.676 0 6.656 2.98 6.656 6.656s-2.98 6.656-6.656 6.656zM22.5 10.5h-3v-1.5h3v1.5z"></path>'
cam_svg += '</svg>'

fact_svg = '<svg viewBox="0 0 24 24">'
fact_svg += '<path d="M22 20h-20v-11l7 5v-5l7 5v-5v-8h6zM4 15v3h3v-3zM11 15v3h3v-3z" />'
fact_svg += '</svg>'

vert_class = 'ToolPaneVert'
hor_class = 'ToolPaneHor'
dual_class = 'ToolPaneDual'

# html attribute options
one_dp_opts_ro = {'class': 'number-tool-1dp readonly', 'readonly': 'readonly'}
two_dp_opts = {'class': 'number-tool-2dp'}
two_dp_opts_ro = {'class': 'number-tool-2dp readonly', 'readonly': 'readonly'}
three_dp_opts = {'class': 'number-tool-3dp'}

#    type | id | name | label | tooltip | icon | action | disabled state| html_options | data_options
select_btn = ToolPaneButton(
    'select', None, 'select', 'select first or next point', None, False, {}, sel_svg)
extend_btn = ToolPaneButton(
    'extend', None, 'extend', 'extend selection to include next point', None, False, {}, ext_svg)
selall_btn = ToolPaneButton(
    'all', None, 'select all', 'select all points', None, False, {}, all_svg)
clr_btn = ToolPaneButton('clear', None, 'clear',
                         'cancel selection', None, False, {}, none_svg)
expand_btn = ToolPaneButton(
    'expand', None, 'expand', 'expand all points', None, False, {}, plus_svg)
contract_btn = ToolPaneButton(
    'contract', None, 'contract', 'contract all points', None, False, {}, minus_svg)
left_btn = ToolPaneButton('left', None, 'left',
                          'nudge left', None, False, {}, left_svg)
right_btn = ToolPaneButton('right', None, 'right',
                           'nudge right', None, False, {}, right_svg)
up_btn = ToolPaneButton('up', None, 'up', 'nudge up', None, False, {}, up_svg)
down_btn = ToolPaneButton('down', None, 'down',
                          'nudge down', None, False, {}, down_svg)
del_btn = ToolPaneButton('delete', None, 'delete',
                         'delete selected point', None, False, {}, del_svg)

# selection buttons
sel_btns = [select_btn, extend_btn, selall_btn, clr_btn]

# nudge buttons
nudge_btns = [left_btn, right_btn, up_btn, down_btn]

# expansion buttons
exp_btns = [expand_btn, contract_btn]

# factory reset button
rst_btn = ToolPaneButton('reset', None, 'reset',
                         'factory reset', None, True, {}, fact_svg)

# fence selected node position label
info_lbl = ToolPaneReadout(
    'Node.XYM',
    None,
    '',
    'X, Y Coordinates of Node in metres',
    True,
    {'class': 'readonly btn-string-tool', 'width': '100%'},
    None
)

# settings pane buttons
#    type | id | label | tooltip  | action | disabled state| html_options | data_options | icon
saveButton = ToolPaneButton(
    'save', None, 'save', 'save settings', None, False, {}, save_svg)
captureButton = ToolPaneButton(
    'capture', None, 'capture', 'capture', 'capture()', True, {}, cam_svg)
freezeButton = ToolPaneButton(
    'freeze', None, 'freeze', 'pause refresh', None, True, {}, freeze_svg)
settings_config = [saveButton, freezeButton]
meas_settings_config = [saveButton]

# contours buttons
# contours_ctrl = [freezeButton]

# calibration 4 point toolpane
cal_quad_config = sel_btns + nudge_btns + [rst_btn, info_lbl]


# fence multipoint toolpane
fence_edit_config = sel_btns + nudge_btns + \
    exp_btns + [del_btn, rst_btn, info_lbl]
    
# primary dropdowns
#    key | name | label | tooltip | action | enabled state | html_options | data_options | cur_val | default
profile_dropdown = ToolPaneDropdown(
        'current.profile',
        None,
        'Profile',
        'Selected Profile',
        "sendData('PUT', 'api', 'current.profile', this.value, true, function() {location.reload(true)})",
        True,
        {},
        'profiles',
        'current.profile',
        {}
    )
strategy_dropdown = ToolPaneDropdown(
        'current.strategy',
        'strategy-select',
        'Strategy',
        'Selected Navigation Strategy',
        "sendData('PUT', 'api', 'current.strategy', this.value, true, function() {location.reload(true)})",
        True,
        {},
        'strategies',
        'current.strategy',
        {None: "None"}
    )
pattern_dropdown = ToolPaneDropdown(
        'current.pattern',
        None,
        'Pattern',
        'Selected Pattern',
        "sendData('PUT', 'api', 'current.pattern', this.value, true, function() {location.reload(true)})",
        True,
        {},
        'patterns',
        'current.pattern',
        {None: "None"}
    )
# profile selection - standalone action acceptable
profile_sel_config = [
    profile_dropdown
]
# primary trio
trio_sel_config = [
    profile_dropdown,
    pattern_dropdown,
    strategy_dropdown
    ]

# calibration lawn dimensions - standalone action acceptable
cal_lawn_dim_config = [
    captureButton,
    ToolPaneDropdown(
        'calibration_source',
        'calibration_source',
        'Source',
        'Select Source',
        "selectSource(this)",
        True,
        {},
        ['Live', 'Archive', 'Blend'],
        'Live',
        {}
    ),
    #    type | id | name | label | tooltip | icon | action | disabled state
    ToolPaneNumber(
        'calib.width_m',
        None,
        'Width[m]',
        'm',
        'Width of calibration quad in metres',
        "calCmdQueue.add('calib.width_m', this.value)",
        None,
        True,
        two_dp_opts,
        0.5,
        10,
        0.005,
        'calib.width_m'
    ),
    ToolPaneNumber(
        'calib.length_m',
        None,
        'Length[m]',
        'm',
        'Length of Calibration quad in metres',
        "calCmdQueue.add('calib.length_m', this.value)",
        None,
        True,
        two_dp_opts,
        0.5,
        10,
        0.005,
        'calib.length_m'
    ),
    ToolPaneNumber(
        'calib.offset_x_m',
        None,
        'X Offset[m]',
        'm',
        'X Offset of Calibration from Lawn metres',
        "calCmdQueue.add('calib.offset_x_m', this.value)",
        None,
        True,
        two_dp_opts,
        -5.0,
        5,
        0.05,
        'calib.offset_x_m'
    ),
    ToolPaneNumber(
        'calib.offset_y_m',
        None,
        'Y Offset[m]',
        'm',
        'Y Offset of Calibration from Lawn metres',
        "calCmdQueue.add('calib.offset_y_m', this.value)",
        None,
        True,
        two_dp_opts,
        -5.0,
        5,
        0.05,
        'calib.offset_y_m'
    )
]

# fence cutter diameter, potentially offsets at a later date
#  - standalone action acceptable
fence_toolbar_config = [
    #    type | id | name | label | tooltip | icon | action | disabled state
    ToolPaneNumber(
        'lawn.width_m',
        None,
        'Lawn Width[m]',
        'm',
        'Width of Lawn in metres',
        "fenceCmdQueue.add('lawn.width_m', this.value)",
        None,
        True,
        two_dp_opts,
        0.5,
        10,
        0.005,
        'lawn.width_m'
    ),
    ToolPaneNumber(
        'lawn.length_m',
        None,
        'Lawn Length[m]',
        'm',
        'Length of Lawn in metres',
        "fenceCmdQueue.add('lawn.length_m', this.value)",
        None,
        True,
        two_dp_opts,
        0.5,
        10,
        0.005,
        'lawn.length_m'
    ),
    ToolPaneNumber(
        'lawn.border_m',
        None,
        'Lawn Border[m]',
        'm',
        'Width of Lawn Border in metres',
        "fenceCmdQueue.add('lawn.border_m', this.value)",
        None,
        True,
        two_dp_opts,
        0,
        0.5,
        0.05,
        'lawn.border_m'
    )
]

PROFILE_SELECTION = HtmlToolPane(
    'cal_lawn_sel', hor_class + ' ' + dual_class, profile_sel_config)
PROF_STRAT_PATT_SELECTION = HtmlToolPane(
    'cal_lawn_sel', hor_class + ' ' + dual_class, trio_sel_config)
NAVIGATOR_SELECTION = HtmlToolPane(
    'navsel', hor_class + ' ' + dual_class, trio_sel_config + [freezeButton])
CALIBRATION_LAWN_DIMS = HtmlToolPane(
    'cal_lawn_dim', hor_class + ' ' + dual_class, cal_lawn_dim_config, tp_labels=True, tp_vertical=False)
CALIBRATION_QUAD = HtmlToolPane(
    'calquad', vert_class + ' ' + dual_class, cal_quad_config, tp_labels=True, tp_vertical=True)
FENCE_EDIT = HtmlToolPane('editpoint', vert_class + ' ' + dual_class,
                          fence_edit_config, tp_labels=True, tp_vertical=True)
FENCE_CUTTER = HtmlToolPane('edit_lawn', hor_class + ' ' + dual_class,
                            fence_toolbar_config, tp_labels=True, tp_vertical=False)
CAM_SET_BTNS = HtmlToolPane(
    'camsettings', hor_class + ' ' + dual_class, settings_config)
CONTOUR_BTNS = HtmlToolPane(
    'contourctrl', hor_class + ' ' + dual_class, [freezeButton])
MEAS_SET_BTNS = HtmlToolPane(
    'meassettings', hor_class + ' ' + dual_class, meas_settings_config)

# cockpit state
cockpit_state_config = [
    #    key | name | label | tooltip | icon | action | disabled state | html_options
    ToolPaneIndicator(
        'Wifi.Strength',
        None,
        None,
        'WiFi Strength',
        None,
        False,
        {'class': 'wifi-offline dashboard-icon'}
    ),
    ToolPaneBatteryIndicator(
        'Battery',
        None,
        None,
        'Battery Level',
        None,
        False,
        {'class': 'offline dashboard-icon battery'}
    ),
    ToolPaneIndicator(
        'Found',
        None,
        None,
        'Robot Not Found',
        None,
        False,
        {'class': 'robot-lost dashboard-icon'}
    ),
    ToolPaneReadout(
        'Robot.XM',
        None,
        'X',
        'X Coordinate of Robot in metres',
        False,
        {'class': 'number-tool readonly'},
        1.5
    ),
    ToolPaneReadout(
        'Robot.YM',
        None,
        'Y',
        'Y Coordinate of Robot in metres',
        False,
        {'class': 'number-tool readonly'},
        1.8
    ),
    ToolPaneReadout(
        'Robot.Theta',
        None,
        '&theta;',
        'Heading of Robot in degrees counterclockwise',
        False,
        {'class': 'number-tool readonly'},
        90
    ),
    ToolPaneIndicator(
        'Compass',
        None,
        None,
        'Robot Compass Direction CCW ^ 0&#176; N | <- 90&#176; W | V 180&#176; S | -> 270&#176; E',
        None,
        False,
        {'class': 'dashboard-icon compass-image hidable'}
    ),
    ToolPaneIndicator(
        'Emergency.Stop',
        None,
        None,
        'Emergency Stop',
        None,
        False,
        {'class': 'dashboard-icon emergency-stop hidable'}
    )
]

# cockpit state toolpane
tp_cockpit_state_1 = HtmlToolPane('cockpitstate', None, cockpit_state_config)

# control toolpane rows

# compute speed options
robot_speed_opts = {'0.0': 'R0/0%'}
speed_range = list(range(40, 80, 5)) + list(range(80, 110, 10))
for rot_spd in speed_range:
    for drv_spd in speed_range:
        opt_key = '{0}.{1}'.format(rot_spd, drv_spd)
        opt_val = 'R{0}/{1}%'.format(rot_spd, drv_spd)
        robot_speed_opts[opt_key] = opt_val

# compute direct commands
dir_cmd_list = [
    "sweep(100,-100,50)",
    "sweep(-100,100,50)",
    "sweep(100,-100,100)",
    "sweep(-100,100,100)",
    "sweep(100,-100,200)",
    "sweep(100,-100,300)",
    "sweep(100,-100,400)",
    "sweep(100,-100,500)",
    "sweep(100,-100,1000)",
    "sweep(100,-100,3000)",
    "sweep(-100,100,1000)",
    "sweep(-100,100,3000)",
    "sweep(-100,-100,1000)",
    "sweep(-100,-100,3000)",
    "sweep(-100,-100,5000)",
    "sweep(100,100,100)",
    "sweep(100,100,500)",
    "sweep(100,100,1000)",
    "sweep(90,90,1000)",
    "sweep(80,80,1000)",
    "sweep(70,70,1000)",
    "sweep(60,60,1000)",
    "sweep(50,50,1000)",
    "sweep(40,40,1000)",
    "sweep(30,30,1000)",
    "sweep(20,20,1000)",
    "sweep(10,10,1000)",
    "sweep(9,9,1000)",
    "sweep(8,8,1000)",
    "sweep(7,7,1000)",
    "sweep(6,6,1000)",
    "sweep(5,5,1000)",
    "sweep(4,4,1000)",
    "sweep(3,3,1000)",
    "sweep(2,2,1000)",
    "sweep(1,1,1000)",
    "sweep(100,100,5000)",
    "sweep(-50,50,1000)",
    "sweep(40,-40,1000)",
    "sweep(-30,30,1000)",
    "sweep(20,-20,1000)",
    "sweep(-10,10,1000)",
    "reset()"
]

# convert to dictionary here, so asymetric values can be added!
dir_cmd_dict = {'': 'Please Choose'}
for itm in dir_cmd_list:
    dir_cmd_dict[itm] = itm

# compute direct drive options
dir_drv_dict = {
    "": "Please Choose...",
    "F+0.1": "Fwd 0.1",
    "F+0.2": "Fwd 0.2",
    "F+0.25": "Fwd 0.25",
    "F+0.5": "Fwd 0.5",
    "+0.1|+0.1": "(+0.1, +0.1)",
    "-0.1|-0.1": "(-0.1, -0.1)",
    "+0.1|-0.1": "(+0.1, -0.1)",
    "-0.1|+0.1": "(-0.1, +0.1)",
    "+0.25|+0.25": "(+0.25, +0.25)",
    "-0.25|-0.25": "(-0.25, -0.25)",
    "+0.25|-0.25": "(+0.25, -0.25)",
    "-0.25|+0.25": "(-0.25, +0.25)",
    "+0|+0.3": "(+0, +0.3)",
    "+0|-0.3": "(+0, -0.3)",
    "+0.3|+0": "(+0.3, +0)",
    "-0.3|+0": "(-0.3, +0)",
    "+0|+0.1": "(+0, +0.1)",
    "+0|-0.1": "(+0, -0.1)",
    "+0.1|+0": "(+0.1, +0)",
    "-0.1|+0": "(-0.1, +0)",
    "1.2|1.2": "(1.2, 1.2)",
    "1.3|1.3": "(1.3, 1.3)",
    "1.4|1.4": "(1.4, 1.4)",
    "1.2|2.4": "(1.2, 2.4)",
    "1.0|1.0": "(1.0, 1.0)",
    "1.0|2.0": "(1.0, 2.0)",
    "4.0|1.0": "(4.0, 1.0)",
    "4.0|2.0": "(4.0, 2.0)",
    "4.0|3.0": "(4.0, 3.0)",
    "4.0|4.0": "(4.0, 4.0)",
    "3.0|4.0": "(3.0, 4.0)",
    "2.0|4.0": "(2.0, 4.0)",
    "1.0|4.0": "(1.0, 4.0)"
}

# robot selection and speed
cockpit_control_robot_config = [
    ToolPaneDropdown(
        'current.mower',
        None,
        'Robot',
        'Selected Robot',
        None,
        False,
        {},
        'mowers',
        'current.mower',
        {None: "None"}
    ),
    ToolPaneDropdown(
        'robot.speed',
        None,
        'Speeds',
        'Rotation and Drive Speeds [%]',
        None,
        False,
        {},
        robot_speed_opts,
        ['mower.motion.set_rotation_speed_percent',
            'mower.motion.set_drive_speed_percent'],
        {}
    )
]
# environment hotspot
cockpit_control_hotspot_config = [
    ToolPaneLabel('hotspot.name', {'class': 'subtool-label dis-label'}),
    ToolPaneButton('Enrol', None, 'Enrol', 'Enrol', None, False, {}, None),
    ToolPaneGap(),
    ToolPaneButton('Reboot', None, 'Reboot', 'Reboot', None, False, {}, None),
    ToolPaneButton('Shutdown', None, 'Shutdown',
                   'Shutdown', None, False, {}, None)
]
# direct commands
cockpit_control_direct_config = [
    ToolPaneDropdown(
        'direct.command',
        'direct-command',
        'Direct',
        'Direct Commands',
        None,
        False,
        {},
        dir_cmd_dict,
        None,
        {}
    ),
    ToolPaneSlide('Cutter.1.Enabled', 'cutter-1-slide', 'C1',
                  'Cutter Enabled', None, False, {}, False),
    ToolPaneSlide('Cutter.2.Enabled', 'cutter-2-slide', 'C2',
                  'Cutter Enabled', None, False, {}, False)
]
# driveto commands
cancel_tool_pane_button = ToolPaneButton(
    'Cancel', None, 'Cancel', 'Cancel', None, True, {}, None)
driveto_tool_pane_button = ToolPaneButton(
    'Drive', None, 'Drive', 'Drive', None, False, {}, None)
x_rdout = ToolPaneReadout(
    'Driveto.X',
    None,
    'X',
    'X Coordinate in metres',
    False,
    two_dp_opts_ro,
    0.0
)
y_rdout = ToolPaneReadout(
    'Driveto.Y',
    None,
    'Y',
    'Y Coordinate in metres',
    False,
    two_dp_opts_ro,
    0.0
)
cockpit_control_driveto_config = [
    ToolPaneReadout(
        'Navigation.Status',
        None,
        'Status',
        'Navigation Status',
        False,
        {'class': 'readonly'},
        'Initialising...'
    ),
    cancel_tool_pane_button,
    ToolPaneNewline(6),
    ToolPaneLabel('Manual', {'class': 'subtool-label'}),
    x_rdout,
    y_rdout,
    ToolPaneDropdown(
        'direct.drive',
        None,
        None,
        'Direct Commands',
        None,
        False,
        {'style': 'width: 18px'},
        dir_drv_dict,
        None,
        {}
    ),
    driveto_tool_pane_button

]

# drive commands
cockpit_control_drive_config = [
    ToolPaneLabel('Drive', {'class': 'subtool-label'}),
    ToolPaneButton('Route', None, 'Route', 'Route', None, True, {}, None),
    ToolPaneButton('Skip', None, 'Skip', 'Skip', None, True, {}, None),
    ToolPaneButton('Pause', None, 'Pause', 'Pause', None, True, {}, None),
    ToolPaneButton('Step', None, 'Step', 'Step', None, True, {}, None),
    ToolPaneButton('Reset', None, 'Reset', 'Reset', None, True, {}, None)
]
all_configs = [cockpit_control_robot_config,
               cockpit_control_hotspot_config,
               cockpit_control_direct_config,
               cockpit_control_driveto_config,
               cockpit_control_drive_config
               ]
cockpit_control_config = []
for i in all_configs:
    cockpit_control_config.extend(i + [ToolPaneNewline(4)])

cockpit_control_strategy_config = (
    cockpit_control_robot_config +              # mower, speeds
    # [cockpit_control_drive_config[0]] +         # drive label
    [cockpit_control_drive_config[1]] +         # route
    [cockpit_control_drive_config[2]] +         # skip
    [driveto_tool_pane_button] +                # drive to
    [x_rdout] +
    [y_rdout] +
    [cancel_tool_pane_button, ToolPaneGap()] +  # cancel
    cockpit_control_drive_config[3:-1] +        # pause, step
    # [ToolPaneGap()]  +                          # gap
    [cockpit_control_drive_config[-1]]          # reset
)
tp_cockpit_control_1 = HtmlToolPane(
    'cockpitctrl', None, cockpit_control_config)
tp_cockpit_control_2 = HtmlToolPane(
    'cockpitctrlstrat', None, cockpit_control_strategy_config)
