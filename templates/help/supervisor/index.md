<h2 id="supervisor">Supervisor Feature</h2>

The _supervisor_ is the control centre for mowing operations, once everything
else has been set up i.e. vision, calibration, etc.

The feature comprises:

  * A header toolbar
  * The _Arena View_ , the current top-down view of the arena
  * A monitor pane showing current system state
  * The _Controls_ toolpane with tools to manage excursions
  * The _History_ list showing the latest commands sent to the robot

### The Header Toolbar

This toolbar hosts Profile, Navigation Strategy and Mowing Pattern dropdowns.

### The Arena View

The arena view is a helicopter view of the lawn, with the route overlaid. A
marker can be dropped onto this view with a double mouse click, setting the
target destination. The robot will navigate to this destination.

### The Monitor Pane

The monitor pane sits at the top of the Arena View, and includes:

<!--{% include "help/monitor.html" %}-->

### Control Toolpane

<!--{% include "help/common_controls.html" %}-->

#### Cutter Switches

Slide switches display the current state of the cutter(s), and enable them to
be turned on or off.

#### Enrol

If robots are used in multiple locations, it may be necessary to _enrol_ them
in their local hotspot.  
Each profile can have a hotspot name specified in it's configuration, and this
is displayed beside the Enrol button. Clicking the Enrol button will initiate
a command to the robot requesting this hotspot be given priority.  

#### Reboot

This button will initiate a reboot of the proxymow-server host, if confirmed.

#### Shutdown

Clicking this button will shutdown the proxymow-server host, if confirmed.

### Direct Commands

Direct commands are low level commands sent direct to the robot, ignoring any
navigation operations in progress.

### Manual Driving Mode

Manual driving operates at a higher level than Direct Commands. A destination
can be specified by either:

  * Selecting a manouvre from the Manual dropdown list e.g. Fwd 0.2
  * Selecting an absolute location from the Manual dropdown list e.g. (1.0, 1.0)
  * Selecting a relative movement from the Manual dropdown list e.g. (-0.1, +0.1)
  * ![](/icons/map_marker.png)Double-clicking and dropping a marker on the arena view

Manual driving is different to Direct Commands, as it specifies a target
location that the navigation system must resolve.

### The History List

The history list contains a line for every command despatched to the robot.
Details include:

  * The time the command was sent
  * The snapshot id
  * The current pose
  * The percentage progress
  * The relative heading and distance to target
  * The command rule name
  * The command parameters e.g. speeds & duration
  * Any frozen status
  * Any escalation applied (+, ++, etc.)
  * In motion status when finished(...)

There is a compressed format of history list for mobile devices.  
The list can be expnded to a full tab of the underlying log by clicking the
tab title link.

