#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 16:43:42 2020

@author: andy
"""

import EQ
import numpy as np
from scipy.signal import freqz, lfilter

n = 32768
tf = EQ.peaking(1000, 12, 2, 44100)
x = (np.random.rand(n) - .5) * np.hanning(n)
y = lfilter(tf[0], tf[1], x)
fx = np.fft.rfft(x)
fy = np.fft.rfft(y)


