<h2 id="navigator">Navigator Feature</h2>

The _Navigator_ is a feature for managing the navigation strategy.

The feature comprises:

  * A header toolbar
  * The _top-down_ Arena View
  * A monitor pane showing current system state
  * A toolbar with tools to manage excursions
  * A table of _Terms_ for the current navigation strategy
  * A table of _Rules_ for the current navigation strategy

### The Header Toolbar

This toolbar hosts Profile, Navigation Strategy and Mowing Pattern dropdowns
plus a freeze button, enabling page refreshes to be frozen.  
  
Navigation pages are expensive to process, and the resource drain has a
detrimental impact on frame rate. Use the freeze button to pause page
refreshes when they are not required, or close the tab. In any case auto-
freeze will kick in after a pre-defined interval.

### The Arena View

The arena view is a helicopter view of the lawn, with the route overlaid. A
marker can be dropped onto this view with a double mouse click, setting the
target destination. The terms and rules will then refresh to reflect this
target destination, but no commands will be issued until the Drive button is
clicked.

### The Monitor Pane

This includes:

<!--{% include "help/monitor.html" %}-->

### Control Toolbar

<!--{% include "help/common_controls.html" %}-->

### Terms Table

This table displays the terms that are available to be used in navigation
strategy rules.  
  
Each term has the following properties:

  * Name - identifier used in rule formulae
  * Description - a description of the term
  * Expression - formula or constant
  * Result - evaluation of expression
  * Units - metres, radians, etc.
  * Alt Expression - an alternative way to express the term
  * Alt Result - the alternative result
  * Alt Units - metres, radians, etc.
  * Colour - used for graphical annotation

There are 3 types of terms:

  * User terms
  * Hybrid Terms
  * System Terms

#### User Terms

User terms are created, edited and deleted by the user. They are typically
used for constants like home radius, home sector, etc.  
  
User terms are also a convenient way to graphically annotate the Arena View. A
colour can be specified, which is interpreted in the following way:

  * Single value - displayed as text: name = value
  * Pair of x,y values - drawn as a point at (x, y)
  * Trio of values x, y, r - drawn as a circle of radius r and centred on (x, y)
  * Quartet of values x1, y1, x2, y2 - drawn as a dashed line from (x1, y1) to (x2, y2)

The system will aggregate different terms sharing the same colour, or
additional graphical terms can be created that group existing terms.

#### Hybrid Terms

Hybrid terms are provided by the system, so can't be deleted, but can be
edited. For example, Proxymow Server has an implementation of the Pure Pursuit
algorithm built-in, and hence available to be used in user-defined strategies.
Pure Pursuit expects a Look-Ahead distance to be defined, so this is
implemented as a Hybrid Term.

#### System Terms

System terms are terms which can't be edited or deleted. There is a rich
tapestry of system terms which can be used in navigation strategies.

User and Hybrid terms can be edited by double-clicking the relevant row to
pop-up a form.

### Rules Table

This table displays the user-defined rules that control the motion of the
robot. Rules can be edited by double-clicking the relevant row to pop-up a
form.  
  
Each rule has the following properties:

  * Name - name of the rule
  * Description - a description of the rule
  * Priority - order in which rules are processed
  * Condition - expression for rule selection
  * Left Speed Expression
  * Left Speed Result
  * Right Speed Expression
  * Right Speed Result
  * Duration/Cmd Expression
  * Duration/Cmd Result
  * Stage Complete
  * Scope

Rules are selected based on the condition expression evaluating to True. The
currently selected rule is highlighted in the table. There are 2 types of rule
that can be used: Sweep rules and Auxiliary rules.

#### Sweep Rules

Most rules will be Sweep rules, where the Left Speed[%], Right Speed[%] and
Duration[ms] expressions generate the values for a robot command.

    
    
    sweep(left, right, duration)

#### Stage Termination

A rule may have the _Stage Terminator_ flag set. When such a rule is selected,
it signals to the rules engine that the current stage is complete and we can
start navigating to the next.

#### Rule Scope

The scope of a rule can be set to one of:

  * Stationary
  * In-flight
  * Any
  * Disabled

##### Stationary Scope

Rules in stationary scope will only qualify for selection if the robot is at
rest. This is the safest setting, avoiding any issues with lag in
communications or the vision system.

##### In-flight Scope

Rules with In-flight scope, only qualify for selection if the robot is in
motion. If you are trying to maintain a straight line path, to perfect a
striped pattern, then in-flight rules in conjunction with the Pure Pursuit
algorithm, can be an effective way to keep the robot on-path.

##### Any Scope

Rules with the scope set to Any will qualify whatever the motion state of the
robot is. This may be suitable for detecting stage completion, or auxiliary
rules.

##### Disabled Scope

Rules can be disabled by setting their scope to disabled.

#### Auxiliary Rules

Auxiliary rules are needed to send _other_ commands to the robot, which are
not sweep commands. If no speed expressions are specified in the rule, then it
is interpreted as an auxiliary rule. In this case the command specified in
the Duration/Cmd field is sent to the robot. This is useful for manipulating
the cutter in a dual cutter mower.

