from math import pi as pi

def ring_area(od: float, id: float):
  return pi * (pow(od/2, 2) - pow(id/2, 2))

def bobbin_volume(od: float, id: float, depth: float):
  return depth * ring_area(od, id)