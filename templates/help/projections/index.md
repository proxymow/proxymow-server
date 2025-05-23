<h2 id="projections">Projections Feature</h2>

The _Projections Feature_ provides a detailed view of selected projections
from the buffer.  
  
A _projection_ is simply the best isosceles triangle that encloses the
contour. It is derived by reconstructing the vertices from the convex hull of
the contour, which will have suffered erosion during processing.  
  
The buffer will only collect a handful of samples if the robot is static, but
will add more samples once an excursion is in progress.

The feature comprises:

  * A header toolbar
  * The Display Image
  * The Analysis Image
  * A Summary of the projection's attributes and scores
  * A diagram of the projection

### The Header Toolbar

The header toolbar provides a freeze button and links to call up the first or
latest projection, and step backwards and forwards through the buffer. If you
choose _latest_ , then the page will dynamically refresh with the latest
projection processed.  
  
Projection diagrams are expensive to compute, and the resource drain has a
detrimental impact on frame rate. Use the freeze button to pause page
refreshes when they are not required, or close the tab. In any case auto-
freeze will kick in after a pre-defined interval.

### Display Image

The display image shows the contour region as seen by the camera.

### Analysis Image

The analysis image shows the contour region as processed by the vision system.
This will include filtering and edge detection.

### Projection Attributes

The projection attributes are the salient properties of the projection which
have been chosen as measures that can be scored e.g. span, isoscelicity, etc.

### Projection Diagram

The projection diagram is a plot of the source contour, with its projected
vertices.

