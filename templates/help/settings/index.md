<h2 id="settings">Settings Feature</h2>

The _Settings Feature_ provides a number of forms to enable the configuration
to be managed.

The feature comprises:

  * A Menu pane - hosts an expanding tree menu
  * A Form pane - holds the form to enable items to be edited

Not every element in the configuration can be edited here, and whilst some
can, there are often better ways to accomplish the task.  
  
For example, Fence points and Calibration points cannot be changed outside of
the Calibration and Fence features, due to their graphical context.  
  
Camera device settings can be changed, but it may be better to adjust them in
the Vision feature where the effect is immediately apparent.

These are the main items that can be managed:

  * Profiles
  * Mowers
  * Navigation Strategies
  * Pairings

### Profiles

A profile is a convenient grouping of configuration items: Lawn, Calibration,
Device, Connection and Hotspot. You may only require one profile per Proxymow
server, but you can have more. You may need additional profiles for different
cameras, or different fence definitions. The values in the Lawn, Calibration
and Device groups are probably better managed in the Fence Editor, Calibration
and Vision features respectively. The Connection is for an external logging
database and is entirely optional. Hotspot allows the default hotspot to be
specified, the one used by the Enrol command.

#### Adding a new Profile

![](images/new-profile.png)

The device channel can be set to one of the following options:

  * Virtual Camera
  * Remote Pi
  * Pi Camera
  * Linux USB
  * Windows USB

The options may be limited to just those applicable to the host operating
system.

##### Virtual Camera

This channel is always available, and is the default if no other cameras are
available.

##### Remote Pi

Remote Pi fetches camera images from a remote pi camera, but does everything
else locally. The aim is to share the resource load. If you select this option
you need to enter the endpoint url of the remote pi.

##### Pi Camera

This option is only available on raspberry pi computers. It is the recommended
option due to the superior performance of the pi camera.

##### Linux USB

Raspberry Pi can support USB cameras in addition to native cameras. Proxymow
Server allows for multiple cameras to be connected which can be associated
with different profiles. It is worth noting that USB cameras can't match the
pi camera for performance, but may be easier to install. This is due to their
small round cables as opposed to the ribbon connector on the pi camera.

##### Windows USB

This is a good camera option for testing and sytem familiarisation, but is
unlikely to meet the demanding requirements for successful navigation, without
significant lag. This stems from the underlying video frame capture mechanism.

### Mowers

Mower settings are divided into four groups: Identity, Dimensions, Motion and
Battery.

#### Identity

The IP Address and Port need to be entered to identify the robot mower on the
network. Virtual mowers are hosted by the Proxymow Server, so their ip address
is 127.0.0.1 i.e. localhost. The type can be selected: virtual, hybrid or
physical.

#### Dimensions

The Target Width and Height refers to the base and the span of the idealised
isosceles triangle enclosing the target shape. The Target Radius refers to the
radius of the circle, centred on the vertices, that defines the truncation
points. It is only used by Virtual mowers. The Target Offset is necessary for
robots where the target is not centred on the turning point, i.e. the centre
of the Axle Track. This is normally 50%. The diameters of up to two cutters
can be configured. Mowing Patterns will be supplied with the mean diameter.
The Body Width and Body Length are not used by the vision system, only the
Target dimensions, however they are used for Virtual mowers to provide
background contrast to the target.

#### Motion

The Axle Track is the distance between the wheels. From the values for Wheel
Diameter and Motor Speed, the system calculates an idealised Linear Velocity
in m/s. This is available to Navigation Strategies, along with the Set Speeds,
so they can calculate the duration for sweep commands to achieve movement
towards the destination.

#### Sensors

Sensors are the analogue channels coming from the robot. As there can be a
variable number of sensor channels, depending on device type, sensors are
represented by two comma-separated lists: Names and Scale Factors. Analogue
values are standardised into the range 0..1023 irrespective of device type, so
the displayed value is the scale factor multiplied by the value. The first
channel is assumed to be the main Battery Voltage and is the channel
represented by the battery icon, 0..100%.

### Navigation Strategies

Strategy desciption, Terms and Rules can be managed here, but the best way to
make changes is within the context of the Navigation feature.

### Pairings

Pairings are combinations of Profile and Mower. Mowers may be used on
different lawns, and hence under different profiles. The user can add a
Pairing that sets the Mowing Pattern and Navigation Strategy for any
Mower/Profile combination, including wildcards.

In general, most configuration items can be viewed, edited, created,
duplicated and deleted. Viewing and Editing is accomplished by clicking the
relevant item in the menu, to open the form. Changes can be saved using the
Save button, or the Cancel button can be used to dismiss the form. Create new
items by clicking the 'Add ...' hyperlink at the bottom of the list of current
items. Items can be duplicated by clicking the Duplicate Icon
![](/icons/copy.svg) and deleted by clicking the Delete icon
![](/icons/bin.svg).

