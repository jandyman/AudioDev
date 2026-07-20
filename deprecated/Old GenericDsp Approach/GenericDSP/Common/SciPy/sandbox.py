#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 07:42:03 2020

@author: andy
"""

import numpy as np

def get_parabola_coefs(xpoints, ypoints):
  assert (type(xpoints) == list and type(ypoints) == list
          and len(xpoints) == 3 and len(ypoints) == 3), "inputs must be of length 3"
  A = np.matrix([[xpoints[0]**2, xpoints[0], 1],
                 [xpoints[1]**2, xpoints[1], 1],
                 [xpoints[2]**2, xpoints[2], 1]])
  b = np.matrix(ypoints).T
  abc = A.I * b
  return tuple(np.array(abc).flatten())

xpoints = [0,18,36]
ypoints = [0,-.005,0]
abc = get_parabola_coefs(xpoints, ypoints)
  
def sag_at(x):
  return abc[0] * x**2 + abc[1] * x + abc[2]
  
  
  
  
  
  

                                         
  
  
    