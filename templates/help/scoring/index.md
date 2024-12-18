<h2 id="scoring">Scoring Measures Feature</h2>

The _Scoring Measures_ feature allows the user to change the way projections
are scored.  
  
The goal is to reward the target shape representing the mower, and penalise
noise.  
  
The user can't configure new measures, but can change the setpoints, upper and
lower ranges and maximum points scored. The default values should be suitable
for most use cases.

The feature comprises:

  * A projection sample to experiment with
  * The Scoring Measures Editor
  * The Scorecard

There are five properties of the projection that can be scored:

  * Span
  * Area
  * Isoscelicity
  * Solidity
  * Fitness

### Span

The span is the derived distance from the base of the isosceles triangle to
its tip.

### Area

The area is the area of the isosceles triangle.  
  
Both Span and Area are _scaled_ measures. Rather than entering a fixed
setpoint, the user provides a scale factor which is multiplied by the expected
vlaue taken from the the mower configuration.

### Isoscelicity

This is a ratio derived from the relative side lengths of the isosceles
triangle.

### Solidity

This is a ratio derived from the relative areas of the isosceles triangle and
contour convex hull.

### Fitness

Fitness is a measure of how well the derived projection fits the original
contour.

Unlike Span and Area, Isoscelicity, Solidity and Fitness are setpoint
measures. This means the setpoints configured should work with targets of any
size.

There are four values for each scoring measure:

  * Setpoint
  * Lower Range
  * Upper Range
  * Maximum Score

The maximumum score is an arbritrary number of points for the measure.
Measures can be _weighted_ by allocating different maximum scores. The maximum
score is awarded if the projection property matches the setpoint. The score
reduces to zero as the projection property approaches the threshold in either
direction, i.e. the lower range below the setpoint, or the upper range above
the setpoint. It is important to note that any property with a value beyond
the upper or lower thresholds scores zero, and makes the total for that
projection zero. Hence it will not be considered a viable target. The final
confidence value for the projection is expressed as a percentage, calculated
as:

    
    
    100 * sum of the scores / sum of maximum scores

When changing scoring measures the best way to validate the change is to hover
over the relevant widget in the scorecard and check that the calculation meets
your requirements, before commiting the change by clicking the Save button.

