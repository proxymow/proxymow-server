<h2 id="contours">Contours Feature</h2>

The _Contours feature_ highlights the contours found in the camera image, and
tabulates their scores.

The feature comprises:

  * A header toolbar
  * The Contour View
  * The Scorecard Table

### The Header Toolbar

This toolbar hosts a freeze button, enabling page refreshes to be frozen.  
  
Contour pages are expensive to process, and the resource drain has a
detrimental impact on frame rate. Use the freeze button to pause page
refreshes when they are not required, or close the tab. In any case auto-
freeze will kick in after a pre-defined interval.

### The Contour View

This displays the undistorted camera image, with all found contours overlaid
in yellow. Qualifying contours are then overlaid in orange, labelled with
their index and point count. If a contour is not displayed in orange, then it
won't be considered as a potential target. The tracking viewport is also
displayed as a dashed box.

### The Scorecard Table

The scorecard table displays projections that have been obtained from
qualifying contours. Projections are idealised isosceles triangles that
enclose each contour. The highest scoring projection will appear at the top.
Ideally, there will only ever be one row in this table, corresponding to the
robot mower target, but other noise contours may be discovered. The challenge
is to ensure that the real mower always scores highest.

#### Scoring Measures

These are displayed as a sub-heading of the table. Each measure has a name and
is represented by a set of four numbers:

  1. The lower range
  2. The setpoint
  3. The upper range
  4. The maximum score in points

#### Projections

Each qualifying projection is displayed as a row in the table. The thumbnail
image shows the portion of the scene analysed, and the Ident helps with cross-
referencing. The calculated centre is also displayed. Each column represents a
scoring measure of the projection, and contains a meter widget. You can hover
your mouse over this widget to get more information about how the projection
score was calculated. The final column shows the overall percentage confidence
that the projection _is_ the target we are looking for.

