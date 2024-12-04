# Navigation Strategy Tutorial
In this tutorial we will cover the following topics:

* [Creating a new Strategy](#creating-a-new-strategy)
* [Adding a Term](#adding-a-term)
* [Adding a Rule](#adding-a-rule)
* [Dropping a Pin to set manual destination](#setting-manual-destination)
* [Adding a Forward Drive Rule](#adding-a-forward-drive-rule)
* [Adding a Stage Completion Rule](#adding-a-stage-completion-rule)
* [Driving the Route](#driving-the-route)
* [Adding a Reverse Drive Rule](#reverse-driving)

## Creating a new Strategy
Head over to the Settings feature and expand the *Strategies* Branch of the hierarchical menu. Click the *Add Strategy* link and enter a name and description for your strategy e.g. *Tutorial* and *Introduction to Navigation*. The name must be at least 6 characters long, but the description is optional. Click Save and confirm that your strategy has been added to the menu.

## Adding a Term
Switch to the Navigator feature, which displays the arena view, a grid of Terms, and a grid of Rules. Select your strategy from the Navigation Strategy dropdown list. Once we have created a strategy, and selected it, we can add, edit and test terms and rules here. 

The first term we want to add is a constant representing the Home Sector. As we are about to create a rule that rotates the robot so it points towards the destination, we need to know when to stop. This is the purpose of the Home Sector term.

You will see the Terms grid already has a number of entries, which are maintained by the system and are not user-editable, but we need a user term that we can adjust.

Click the Add Term button to open the form, and populate the following fields:

### Name 
Most single characters have been reserved for system terms, so it is recommended to use at least 2 characters, but overly-long term names tend to make the rules less readable. Enter *hs* for the term name.

### Description
Enter *Home Sector Angle* for the description.

### Expression
Strategy calculations use plain Python expressions. All angles are assumed to be in radians, but these can be difficult to visualise, so we can enter ```radians(9)``` for our expression which is more readable, and the parameter will be converted to radians.

### Units
Enter *radians* for the units.

### Alt Expression
Each term can have an alternative expression for display purposes only. We could enter ```9``` here as our angle in degrees.

### Alt Units
Enter *degrees* as the alternative units.

### Colour
The colour selection is used to annotate the arena view. As our term is one-dimensional, then setting a colour would display the term on the arena view as text. If the term was changing then text annotation would be helpful, but as our term is a constant then the colour is not really necessary.

Click Save to save the term, and confirm that it appears at the top of the grid. Note that as this is a user term it has a Delete button. You can also double-click the entry to edit it.

Be mindful of features that have Freeze capability. Auto-Freeze may be enabled and if it has kicked in you may have to cancel it to refresh the feature.

## Adding a Rule
The first rule we want to add is one that rotates the robot counter-clockwise so it points to the destination. Rules normally consist of four expressions:

* Condition
* Left Speed
* Right Speed
* Duration

We will focus on the Condition initially, and when we can see our rule is being matched we can add the other expressions.

It is perfectly feasible to define a strategy containing one gigantic rule that does everything. This is not recommended. It will be difficult to debug, and the visual feedback from matching different conditions will not be available.

We are going to define one rule to rotate counter-clockwise, and one to rotate clockwise. Our aim is to perform the quickest manoeuvre that achieves the desired heading. If we only had one rule, that rotated in one direction, then the robot might have to take the long way around. 

To ascertain the direction of rotation, we need to know what the error is between our current heading angle and the angle of the path to our destination. If this is greater than our Home Sector constant then we need to act to reduce it. Fortunately, there is a system term named ```u``` *shortest delta angle [+/- 0-pi]*  which we can use. u will be positive if a counter-clockwise correction is required and negative if a clockwise correction is required.

Click the Add Rule button and enter the following:

### Name
Enter a name: *Rotate CCW*
### Description
Enter a description: *Rotate shortest way CCW*
### Condition
Enter the following expression for the condition:
```u > hs```

Leave the other fields as their defaults.

Click Save and confirm your rule has been added to the grid.

Add a second rule named *Rotate CW* with the following condition:
```u < -hs```

We are now in a position to test rule selection, but as we have no Speed or Duration expressions configured then Driving the Route is not practical.

## Setting Manual Destination
When testing new strategies it is convenient to be able set a temporary destination to see how the strategy responds, before driving a larger circuit. If you examine the terms you will see most are set at -1, because the system has no target destination to reference. We can set a target destination by double-clicking the arena view image. A map pin will be dropped, and the system will update its terms and attempt to match rules. 

Note that dropping a pin on the Navigator Arena View just sets a destination, you have to click *Drive* if you want to drive to it. This is different to dropping a pin on the Supervisor Arena View, where a double-click plans and executes the manoeuvre.

## Debugging Rule conditions
Click the *Reset* button to make sure your virtual robot is initialised at the centre of the lawn, and is heading North.

If your rules are working, you should now be able to drop a pin to the left of the robot and see the CCW rule condition turn green, and drop a pin to the right of the robot to see the CW rule condition turn green. Dropping a pin above the robot should clear both conditions, as no rotation is required.

What if your rule conditions don't work as expected?.

If you hover your mouse over any condition a tooltip will be displayed which summarises the values of the terms used in the expression, and the result: matched or unmatched.

## Adding Rule Command Expressions
Now we have rules being matched we can flesh out the remaining expressions: Left Speed, Right Speed and Duration, but what values should we use?

We might be tempted to define the wheel speeds as constant terms, however, they may need to be adjusted during an excursion. The strategy has access to the set speeds from the Controls:

* set rotation speed % ```n```
* set driving speed %  ```s```

So we can use ```n``` and ```-n``` for clockwise left and right speeds and ```-n``` and ```n``` for counter-clockwise. But what about the duration?

It can be shown that for a perfect machine the following formula holds:

```duration [ms] = angle [radians] * axle track [m] * 50000 / (velocity [m/s] * speed [%])```

Fortunately, we have access to:

* absolute shortest delta [radians] ```a```
* axle track [m] ```w```
* full speed velocity [m/s] ```v```

So our duration expression is:

```a * w * 50000 / (v * n)```

and this holds for clockwise and counter-clockwise rotations.

Enter these expressions into both rules.

Now if you drop a pin around the robot, *and click Drive* each time, you should see the virtual robot executing the rules and rotating.

## Navigator v Supervisor Feature
At this point you might want to switch to the Supervisor feature for more testing. The Supervisor feature has better facilities for run-time operations:

* dropping a pin plans *and* executes manoeuvre in one go
* the History Pane shows the commands that are despatched to the robot

Note that selecting a feature from the Site Navigation Menu by right-clicking will open the feature in a new tab, so both features can be displayed side-by-side.

## Debugging Rule Expressions
The values of the Left Speed, Right Speed and Duration expressions will be displayed in the respective Results columns of the rules grid, for the matched rule, and dynamically update.

What if your rule expressions don't work as expected?.

You can use the Pause and Step buttons to pause a navigation and single-step it.

If you hover your mouse over any expression a tooltip will be displayed which summarises the values of the terms used in the matched expression. Freezing the display refresh when the suspect rule is matched can provide more time to analyse the expression terms to better understand the problem.

## Adding a Forward Drive Rule
We should now have a strategy that aims our robot in the right direction, so the next rule needs to drive it towards the destination. The rotation rules corrected the heading error, with a conditions that matched when we were outside the range of the home sector, so the drive condition is simply the inverse i.e. when ```u``` is between ```-hs``` and ```hs```. This condition can be simplified if we use absolute shortest delta [radians] ```a``` instead of signed ```u```. 

Add a new rule named *Drive Forward* and enter ```a < hs``` as the condition. We can use set driving speed ```s``` as both left and right speeds, but what about the duration?

It can be shown that for a perfect machine the following formula holds:

```duration [ms] = distance [m] * 100000 / (velocity [m/s] * speed [%])```

Fortunately, we have access to:

* distance to target [m] ```d```

So our duration expression is:

```d * 100000 / (v * s)```

and this holds for forward and reverse driving.

Add the speed and duration expressions and save the rule. Drop a pin and click Drive to test it.

When testing this new rule you may notice a problem. The robot doesn't stop when it gets to its destination!. It will either keep going, or rotate aimlessly around the destination. We need a mechanism to stop driving when we reach our goal. We need another user term to define the radius of a home circle. Click Cancel to cancel the drive.

Add a new term named ```hr``` and set the description to *Home Radius*, the Expression to ```0.1``` and the units to ```metres```. Now modify the driving rule condition to only match if we are outside of the home circle:

```a < hs and d > hr```

## Driving the Route
Now we may be in a position to attempt driving the Route. Click Reset to home the robot, and then click Route to send it on its first excursion. If you receive a warning about incomplete previous excursions just choose Cancel to restart the route from scratch.

If your strategy is working you should reach the first node of the route, then stop. We haven't equipped the strategy with any rules that detect when a node has been reached, and the robot is ready to move to the next.

## Adding a Stage Completion Rule
We have already used the check ```d > hr``` in our driving condition, and we can also use it to detect Stage Completion. Add another rule named ```Stage Complete```, set the condition to ```d <= hr``` and check the stage complete checkbox. Save the rule, Reset the robot and drive the route again. 

## Nones, Nulls and Nils
There are no Nones, Nulls or Nils in the system terms. This is a conscious decision to try to keep expressions as simple as possible. Instead, the terms default to an out-of-range value. For example, a distance might be -1, which is not a valid distance, and a point might be (-1, -1). Sometimes a check needs to be included to ensure a term is valid.

## Rule Processing Order
Rules are processed from top to bottom until one matches, then processing stops.
Stage complete should be highest priority, at the top of the list, so it gets immediate attention.  We can re-order rules by clicking the arrows in the priority column of the grid.

## Annotations
All the terms are displayed in the grid, and constantly updated, but often you need to highlight a single value, or you may want to plot calculated points or draw path lines. Annotations are a very simple way to achieve this.

Terms have a colour property, and depending on the *dimensionality* of the *colour group*, a different annotation will be applied. For example, if we set the colour for our simple constant term *Home Sector Angle* to red, than it is one-dimensional as it is the only term in the red colour group. One dimensional terms are overlaid onto the arena view as text.

If we annotate a term with 2 dimensions, maybe the path end point, then it will be drawn as a filled point. This could be a tuple (x, y) or separate terms representing x and y independently, but sharing the same colour.

If we annotate a term with 3 dimensions, maybe the home radius, then it will be drawn as a circle, the centre (x, y) and the radius in metres. Again this could be a single complex term (x, y, r) or separate terms representing x, y and r independently, but sharing the same colour.

If we annotate a term with 4 dimensions, maybe the path start and end point, then it will be drawn as a line. This could be a single complex term (x1, y1, x2, y2) or separate terms representing each value independently, but sharing the same colour.

What would be useful is to annotate our destination home with a yellow circle, and our path with a blue line.

Add a new term with the following properties:

* name: ```home```
* description: ```home annotation```
* expression: ```x2, y2, hr```
* colour: ```yellow```

Add a second annotation term with the following properties:

* name: ```path```
* description: ```path annotation```
* expression: ```x1, y1, x2, y2```
* colour: ```blue```

Now, when you have an active destination, you should see these symbols displayed.

## Performance Review
With the 4 rules we have defined so far, we should be able to navigate the route, but you may have discovered that the robot is pretty poor at sticking to the path. You may have tried to tune the Home Sector Angle, but that was probably unsuccessful. It is not credible to assume that we can set off at the correct angle, and travel many metres without straying, given the technology we have at our disposal. We will look at 3 ways to improve the performance:

* Maximum Hop
* Veering
* Pure Pursuit

### Maximum Hop
This is a simple concept that just involves limiting the distance we travel in each manoeuvre. This forces the strategy to be re-evaluated with an updated current location. Replace your duration expression in the driving rule with the following: ```min(1000, d * 100000 / (v * s))```

Try another excursion and see if the performance has improved.

### Veering
This approach accepts that we won't be pointing straight at the destination when we set off, so adjusts the relative wheel speeds so we *veer* towards the destination. We need another drive rule for this approach, so we have a *Veer Left* rule and a *Veer Right* rule.

Delete the current *Drive Forward* rule and add a new rule:

* name: ```Veer Left```
* description: ```veer ccw```
* condition: ```0 < u < hs```
* left speed: ```j * s```
* right speed: ```s```
* duration: ```l * 100000 / (v * s)```

Add a second rule...

* name: ```Veer Right```
* description: ```veer cw```
* condition: ```0 > u > -hs```
* left speed: ```s```
* right speed: ```j * s```
* duration: ```l * 100000 / (v * s)```

Fortunately, the system has already calculated terms that are useful for veering:

* Velocity Ratio ```j```
* Arc Length [m] ```l```

Try another excursion and see if the performance has improved.

### Pure Pursuit
Pure Pursuit is an algorithm that uses a point (the look-ahead point) on the desired path which is a fixed distance ahead of the robot. The distance is called the look-ahead distance, and it can be tuned to smooth the robot's behaviour.

Staying on the path, and getting back on the path if we stray, are fundamental behaviours if we want to mow neat stripes, but all mowing patterns benefit.

Fortunately, the system has a Pure Pursuit algorithm built-in, but we need to enable it by setting the look-ahead distance (which is zero by default). The look-ahead distance term is a *Hybrid* term, which is part user part system term. It can't be deleted, or renamed, but its expression can be edited, so the look-ahead distance can be specified. Double-click the look-ahead distance term and set the expression to ```0.5```

We don't need to do anything else, because our existing veer rules should work, albeit with a velocity ratio and arc length that have now been calculated using the look-ahead point, and not the final destination.

It is useful to annotate the look-ahead point. Fortunately, the system has a term for this ```lap```

Add the following term:

* name: ```look-ahead pt```
* description: ```look-ahead pt annotation```
* expression: ```lap```
* colour: ```red```

## Virtual Mower Realism
You may have noticed that the virtual robot is not a *perfect machine* as implied earlier. There are a number of variables that can be changed in the Virtual Mower python code to make the virtual mower more realistic. By default these are all turned off, except for one: the load factor. This represents the inefficiency of the machine, e.g. friction, and has a default value of 0.85. The effect of load factor can be seen when rotating, as the robot needs 2 manoeuvres to achieve its goal.

## Reverse Driving
The strategy we have built has driven the robot around the route in a forward direction. We may not always want this. For example, if we mow up to the edge of the lawn, there may be insufficient solid ground to perform a 180 degree rotation, and we need to back off before rotating.

Fortunately, the system has the following terms:

* reverse absolute shortest delta angle [radians] ```ra```
* reverse shortest delta angle [radians] ```ru```

If you replace ```a``` with ```ra``` and ```u``` with ```ru``` in your rule expressions, and reverse the driving wheel speeds, you should be able to navigate the route backwards.

## Rule Scope
Up until now, we have exclusively used *stationary* rules. A stationary rule is only considered a candidate if the robot is stationary. The vision system will always have some degree of lag, so the Governor Loop predicts when a manoeuvre will complete, and does not issue a new command until it believes it is working with up-to-date location information. The upshot of this is that progress can appear stilted. 

There are occasions when we can overlook this constraint. The robot can accept new *sweep* commands before the existing one is complete. If we are driving a long straight path and get thrown off course, then we need to correct as soon as possible. The visual information may be slightly out of date, but the correction is likely still valid.

If you set a rule's scope to *In-Flight* then it will be considered for selection if the robot is moving. It is wise to limit in-flight rules to the middle phase of a path i.e. after the robot has left the start zone, and before the robot reaches the destination zone. In fact, a stationary rule will always be needed in order to get the robot moving at the outset.