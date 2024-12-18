<h2 id="vision">Vision Feature</h2>

The vision feature is used to configure the camera to get the best image of
the lawn.  
Different settings can be tried, before commiting. Once committed, the
configuration will be updated and these settings will be used in all
operations.

The feature comprises:

  * A header toolbar
  * The _Camera View_ \- displays the live image from the camera using current settings
  * The _Settings Pane_ \- a toolpane with tools to adjust the settings
  * The _Info Pane_ \- an information pane with various details about the camera/image displayed

### The Header Toolbar

This toolbar hosts a Profile dropdown, enabling the profile to be changed.

### Camera View

The camera view displays the live image from the camera, updated every 5
seconds.

### Camera Settings

The camera settings include action buttons and various widgets to change the
image.

#### Action Buttons

  * Save
  * Freeze

#### Save

Save the settings so they are used by the system to detect the mower.

#### Freeze

Freeze the image refresh so the camera information can be analysed.

### Property Settings

The available property settings will vary depending on the type of camera. For
numerical settings coarse adjustments can be made using sliders, and fine
adjustments with the up/down arrows. If you make changes to the settings to
see the effect on the image, and need to reset to the current settings, you
can refresh the page. Note that this may require a hard refresh in some
browsers.  
  
The parameters that can be adjusted may include the following:

  * Annotation
  * Display Colour
  * Horizontal Flip
  * Vertical Flip
  * Automatic White Balance (AWB) Mode
  * Blue Gain
  * Red Gain
  * Resolution
  * Undistort Strength
  * Undistort Zoom

#### Annotation

Annotates the image with the current time. This is useful for checking camera
operation.

#### Display Colour

Only grayscale images are used for detection, but the images displayed in
features can be colour.  
Colour images can help when setting up the vision system, but do use more
resources.

#### Horizontal Flip

Flips the image horizontally.

#### Vertical Flip

Flips the image vertically.

#### AWB Mode

The automatic white balance mode can be specified if the camera supports it.
The 'Auto' setting will be best in most applications. If the AWB mode is set
to 'Off', then the individual Blue and Red gains can be specified. This may be
useful in low light situations.

#### Blue Gain/Red Gain

The Blue and Red Gain settings are only available when the AWB mode is set to
'Off'.

#### Resolution

The resolution is a critical setting. At higher resolutions the mower target
can be resolved more reliably, but the resources needed to process the image
are higher. Not all modes will work on every hardware configuration, and some
modes may crop the field of view. These are marked with an asterisk in the
list.

#### Undistort Strength

A Wide Angle Lens may be needed to get all of the lawn in the image.
Invariably this will introduce distortion (and a rectangular lawn will look
like a barrel!). The effects of distortion can be reduced by increasing the
Undistort Strength setting. Unlike the other Vision property settings the
Undistort Strength does not change the camera view image _in this feature_ ,
but overlays the outline of the lawn as a dashed rectangle which can be
aligned with the image.

#### Undistort Zoom

Undistort Zoom zooms the image to compensate for any changes in scale
introduced by increased strength. Fine tuning the distortion settings may be
easier with Display Colour turned on. This provides a white outline on a
colour background, as opposed to a black outline on a greyscale background.

