#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 17:20:44 2020

@author: andy
"""

import numpy as np
import random
import soundfile as sf
import sounddevice as sd

def vector(normalized_angle):
  angle = 2 * np.pi * normalized_angle 
  real = np.sin(angle)
  imag = np.cos(angle)
  return real + 1j * imag

def flat_response_sequence(length, maxval = .5, repeats=1):
  if length % 2 != 0:
    raise ValueError('length must be a multiple of 2')
  tr_length = int(length/2+1)
  freq_domain = np.zeros(tr_length, dtype = np.complex64) 
  freq_domain[1:tr_length] = vector(np.random.random(tr_length-1))
  freq_domain[tr_length-1] = 1
  sequence = np.fft.irfft(freq_domain)
  sequence = maxval / np.max(np.abs(sequence)) * sequence
  retval = np.zeros(length * repeats)
  for x in range(repeats):
    offset = x*length
    retval[offset:offset+length] = sequence 
  return retval

def normalize(data, maxvalue = 1.0):
  output = data * maxvalue / np.max(abs(data))
  return output

def integrate(data):
  length = data.size
  output = np.zeros(length)
  for i in range(1, length):
    output[i] = output[i-1] + data[i]
  offset = np.sum(data)/length
  output = output - offset
  output = normalize(output)
  return output

def second_half(data):
  # turn matrix into a vector (in case it is a matrix)
  data = data.reshape(data.size)
  # ignore the first half
  size = data.size
  data = data[int(size/2):size]
  return data
 
def sine_wave(frequency, max = 1.0, duration = 1, fs = 44100, keep_plot = False):
  nsamps = fs * duration
  phase = np.arange(nsamps) * frequency * 2 * np.pi / fs
  return np.sin(phase) * max

def test_level(frequency, max = 1.0, fs = 44100):
  playsamps = sine_wave(frequency, max = max, fs = fs)
  recsamps = sd.playrec(playsamps, channels=1, blocking=True)
  plt.clf()
  plt.plot(recsamps)
  return recsamps

def capture_stim_signal_response(length, maxval = .9):
  stimsig = flat_response_sequence(length, repeats = 2)
  stimsig = integrate(stimsig)
  recsamps = sd.playrec(stimsig, channels=1, blocking=True)
  plt.clf()
  plt.plot(recsamps)
  return recsamps
  
import matplotlib.pyplot as plt

def get_response(fft_length, plot = True, keep_plot = False):
  playsamps = flat_response_sequence(fft_length, repeats=2)
  playsamps = integrate(playsamps)
  recsamps = sd.playrec(playsamps, channels=1, blocking=True)
  recsamps = second_half(recsamps)
  response = 20 * np.log10(abs(np.fft.rfft(recsamps)))
  sz = response.size
  freqs = np.arange(sz) * 22050/sz
  if plot:
    if not keep_plot:
      plt.clf()
    plt.semilogx(freqs, response)
    plt.grid(True, which='major')
    plt.grid(True, which='minor', linestyle="--")
  return (freqs, response)

  
  
  


  
  
  

