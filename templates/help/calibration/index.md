<h2 id="calibration">Calibration Feature</h2>

It is very likely that the camera will be viewing the scene at an angle.
Within reason, the camera may be mounted in a convenient location offset from
the centre of the lawn. The calibration feature is used to fix the 4 points
that translate from the undistorted camera view to the arena view. The points
are positioned either by dragging with the mouse, or by selecting and nudging
with keystrokes or tool button clicks. The point coordinates are queued and
automatically update the configuration.  
  
A rectangular target of known dimensions, and position, is needed for accurate
calibration. If the lawn happens to be rectangular or square, and its four
corners are identifiable in the image, then the lawn itself can be used as the
calibration target. In this case the calibration dimensions will be the same
as the lawn dimensions. If there is another rectangular shape that can be
constructed from objets in the image, then this can be used for calibration.
Otherwise, a temporary rectangular calibration target of known dimensions will
need to be set out on the lawn. Using this surveying technique the corner
poles can have markers at the same height as the robot's target shape,
improving the accuracy at the far edges of the lawn. The task is to supply
calibration target dimensions and set the four points, the centres of the
circles, to the corners of the lawn.

The feature comprises:

  * A header toolbar
  * A side toolbar with tools to perform the calibration
  * The _Camera View_ \- displays a snapshot of the undistorted live image from the camera
  * The _Arena View_ the top-down view of the calibrated arena

### The Header Toolbar

This toolbar has controls for setting up the calibration:

  * A capture button
  * A source selection dropdown list
  * The calibration Width input
  * The calibration Length input
  * The calibration X Offset input
  * The calibration Y Offset input

### Calibration Dimensions

There are 4 dimensions that need to be entered to specify the location and
size of the calibration rectangle: the width and height and the X and Y
offsets in metres.

### The Capture Button

Accurate calibration is not essential for automated mowing, however it does
deliver better results with certain mowing patterns, like stripes. Marking out
a calibration target can be tedious, and would need to be repeated if the
camera position or orientation were to change, however if the clibration data
was just lost or overwritten, then the previous calibration is still valid.
Using the capture button, a snapshot of the undistorted camera view can be
archived.

### The Source Selection

This dropdown has options to view the image from 3 different sources:

  * live
  * archive
  * blend

The live source should be viewed when calibrating for the first time, and an
archive image should be captured. The archive image can then be viewed at a
later date, and the calibration can be checked. The blend source mixes the
live image with the archive image to highlight any differences.

### Camera View

The camera view is a zoomable image that displays the image from the selected
source. Use the mouse scroll wheel to zoom in and out, over a part of the
image. Use the mouse to drag the image, or scroll to the area of interest.

### Camera View Toolbar

The toolbar is displayed alongside the camera view. It has the
following tools:

  * Select
  * Extend
  * Select all
  * Clear
  * Left
  * Right
  * Up
  * Down
  * Reset

#### Select

Use this tool to select each of the points in turn. Repeated use will result
in the current point being deselected and the next point being selected. A
selected point will be highlighted. Clicking a point then pressing the TAB key
is equivalent. When only one point is selected, its coordinates will be
displayed in a box at the foot of the toolbar.

#### Extend

Use this tool to select the next point without deselecting the current.
Repeated use will result in all points being selected. The SHIFT-TAB key
combination is equivalent.

#### Select All

Use this tool to select all the points in one action. The CTRL-A key
combination is equivalent.

#### Clear

Use this tool to deselect all of the points. Pressing the ESC key is
equivalent.

<!--{% include "help/nudge_tools.html" %}-->

#### Reset

This tool resets the calibration points to factory settings if confirmed, and
cannot be undone.

### Arena View

The arena view displays the top-down view of the arena using the current
calibration settings. It is refreshed if any settings change. Both the Camera
View and Arena View images can be opened in a separate tab by clicking the
links in their tab titles. This is useful for focusing on the image detail.