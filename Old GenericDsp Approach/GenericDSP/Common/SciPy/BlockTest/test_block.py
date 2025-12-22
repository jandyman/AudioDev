#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  9 12:59:39 2020

@author: andy
"""

import numpy as np
import block_test as bt

def test_block(data, bufsiz):
  buffer_list = split_into_buffers(data, bufsiz)
  n_chans = data.shape[1]
  ws = bt.WireSpec(n_chans, 44100, bufsiz)
  tf = bt.TestFixture(ws)
  output = np.empty((0,n_chans))
  for buf in buffer_list:
    y = tf.Process(buf)
    output = np.append(output, y, axis=0)
  return output
    

def split_into_buffers(data, bufsiz):
  if type(data) != np.ndarray:
    raise Exception("first parameter must be a numpy array")
  if type(bufsiz) != int:
    raise Exception("second parameter must be an int")
  start_idx = 0
  end_idx = bufsiz
  output = []
  if data.ndim == 1:  # if it is a vector, make it a matrix
    data = data.reshape(data.shape[0], 1)
  n_samps = data.shape[0]
  n_chans = data.shape[1]
  while True:
    buffer = np.zeros((bufsiz, n_chans))
    bufidx = min(bufsiz, n_samps - start_idx)
    buffer[0:bufidx,:] = data[start_idx:end_idx,:]
    output.append(buffer)
    if end_idx >= n_samps: 
      break
    start_idx += bufsiz
    end_idx += bufsiz
  return output

