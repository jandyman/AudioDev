from scipy.fft import fft, ifft
from numpy import conj
import numpy as np

def crosscorr(data1, data2):
  if len(data1) != len(data2):
    raise(Exception("length of vectors must be the same"))
  l = len(data1)
  fd = fft(pad_end(data1, l*2))
  fdc = conj(fft(pad_end(data2, l*2)))
  prod = fd * fdc
  return ifft(prod) 

def pad_end(data, length):
  if len(data) > length:
    raise(Exception("len must be >= len(data)"))
  return np.append(data, np.zeros(length - len(data)))

def crosscorr_against_later(data, len, delay, len2):
  in1 = pad_end(data[0:len], len2)
  in2 = data[delay:delay+len2]
  return crosscorr(in1, in2)



