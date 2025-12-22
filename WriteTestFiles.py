# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 19:59:30 2019

@author: Andy
"""

from scipy.io import wavfile as wf
import numpy as np
import math

def write_impulse_file(): 
  data = np.zeros(8192)
  data[0] = .5 
  data = data.astype(float32)   
  wf.write('impulse.wav', 44100, data)
  
def write_sine_file():
  SR = 44100
  x = np.arange(0, SR)
  freq = 1000
  y = sin(x * 2 * math.pi * freq / SR)
  y = y.astype(float32)
  wf.write('sine.wav', SR, y)
  
def read_wav_data(filename):
  rate, data = wf.read(filename)
  flData = data.astype(float)
  return rate, flData