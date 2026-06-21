<h2 id="contours">Contours Feature</h2>

The _Contours feature_ highlights the contours found in the camera image, and
tabulates their assessments.

The feature comprises:

  * A header toolbar
  * The Contour View
  * The Assessment Table

### The Header Toolbar

This toolbar hosts a freeze button, enabling page refreshes to be frozen.  
  
Contour pages are expensive to process, and the resource drain has a
detrimental impact on frame rate. Use the freeze button to pause page
refreshes when they are not required, or close the tab. Hovering over a row in the assessment table will also trigger a freeze. In any case auto-
freeze will kick in after a pre-defined interval.

### The Contour View

This displays the undistorted camera image. Qualifying contours are then overlaid in orange, labelled with
their index and point count. If a contour is not displayed in orange, then it
won't be considered as a potential target. The tracking viewport is also
displayed as a dashed box.

### The Assessment Table

The assessment table displays a row of information about each contour found in the camera image. There is one column for every assessment, displaying the analog result. The qualifying contours will appear at the top, highlighted in green, and disqualified contours will follow highlighted red.

Every contour is progressively assessed by each plug-in module's _assess_ function, found in the contour_assessments directory.  Assessments may not be performed, if short-circuiting is enabled, and the contour fails early. Failed assessments are signified by their results appearing in the strikethough font. Assessments may provide a tooltip which gives details of the thresholds and qualification when you hover over the relevant cell. Hovering also highlighs the contour in the image, and freezes refreshing until the freeze button is clicked to cancel.