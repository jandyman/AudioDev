import math

def drop(radius, x):
  """Depth of the arc below its crown at horizontal offset x."""
  return radius - math.sqrt(radius ** 2 - x ** 2)

def inner_pole_length(outer, radius, spacing):
  """Inner (A, D) pole length for a 4-string bass with radiused pole tops.

  outer   -- outer (E, G) pole length
  radius  -- fretboard radius
  spacing -- adjacent string spacing, center-to-center
  All arguments in the same unit; the result is in that unit.
  """
  return outer + drop(radius, 1.5 * spacing) - drop(radius, 0.5 * spacing)