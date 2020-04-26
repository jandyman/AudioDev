from matplotlib.pyplot import semilogx, ylim, grid, xlabel, ylabel, title
from numpy import pi, poly, array, abs, sqrt, conj, log10, arctan, tan, append, zeros
import numpy as np
from scipy.signal import bilinear, freqz, lfilter
import aifc

def db(x) :
  return 20 * log10(x)

def prewarp(freq, Fs):
  """Frequency pre-warping function for bilinear transform"""
  T = 1/Fs
  return (2/T) * tan(freq * (T/2))

def norm_freq(freq, Fs):
  """Convert frequency in Hz to prewarped frequency in radians/sec""" 
  freq = freq * 2 * pi
  if Fs != 0:
    freq = prewarp(freq, Fs)
  return freq

def __cond_bilinear(num, den, Fs):
  """If Fs == 0 return input. Otherwise, return bilinear(num, den, Fs) """
  if Fs == 0:
    return num, den
  else:
    return bilinear(num, den, Fs)

def lf_shelf_6(Fc, dBboost, Fs=0):
  """(num, den) = transfer function of first order low frequency shelfing filter"""
  freq = norm_freq(Fc, Fs)
  boost = 10 ** (abs(dBboost)/20)
  sing1 = array([-freq])
  sing2 = sing1 * boost
  if dBboost >= 0:
    sden = poly(sing1)
    snum = poly(sing2)
  else:
    sden = poly(sing2)
    snum = poly(sing1)
  return __cond_bilinear(snum, sden, Fs)

def hf_shelf_6(Fc, dB_boost, Fs=0):
  """(num, den) = transfer function of first order high frequency shelfing filter"""
  freq = norm_freq(Fc, Fs)
  boost = 10 ** (-abs(dB_boost)/20)
  sing1 = array([-freq])
  sing2 = sing1 * boost
  if dB_boost >= 0:
    sden = poly(sing1)
    snum = poly(sing2) / boost
  else:
    sden = poly(sing2)
    snum = poly(sing1) * boost
  return __cond_bilinear(snum, sden, Fs)

def hf_shelf_6_new():
  boost = 10 ** (-abs(dB_boost)/20)
  sing1 = array([-1])
  sing2 = sing1 * boost
  if dB_boost >= 0:
    sden = poly(sing1)
    snum = poly(sing2) / boost
  else:
    sden = poly(sing2)
    snum = poly(sing1) * boost
  return __cond_bilinear_new(snum, sden, Fc, Fs)

def hf_shelf_12(Fc, dbBoost, Fs=0):
  """(num, den) = transfer function of a second order high frequency shelfing filter"""
  freq = norm_freq(Fc, Fs)
  irt2 = 1 / sqrt(2)
  s1 = freq * irt2 * (-1 + 1j)
  pair1 = array([s1 , conj(s1)])
  boost = (10 ** (dbBoost/20))**.5
  if boost > 1: 
    pair2 = pair1 / boost
    snum = boost**2 * poly(pair2)
    sden = poly(pair1)
  else: 
    pair2 = pair1 * boost
    snum = boost**2 * poly(pair1)
    sden = poly(pair2)
  return __cond_bilinear(snum, sden, Fs)

def lf_shelf_12(Fc, dBboost, Fs=0):
  """(num, den) = transfer function of a second order low frequency shelfing filter"""
  freq = norm_freq(Fc, Fs)
  irt2 = 1 / sqrt(2)
  s1 = freq * irt2 * (-1 + 1j)
  boost = ((10 ** (dBboost/20))**.5)
  pair1 = array([s1, conj(s1)])
  if boost > 1:
    pair2 = pair1 * boost
    snum = poly(pair2)
    sden = poly(pair1)
  else:
    pair2 = pair1 / boost
    snum = poly(pair1)
    sden = poly(pair2)
  return __cond_bilinear(snum, sden, Fs)
  
def peaking(Fc, dBboost, q, Fs=0):
  """(num, den) = transfer function of a second order peaking filter"""
  freq = norm_freq(Fc, Fs)
  boost = 10 ** (dBboost/20)
  if boost >= 1:
    sden = array([freq**-2, 1/(freq * q), 1])
    snum = array([freq**-2, boost/(freq * q), 1])
  else:
    sden = array([freq**-2, (1/boost)/(freq * q), 1])
    snum = array([freq**-2, 1/(freq * q), 1])
  return __cond_bilinear(snum, sden, Fs)
    
def freq_plot_db(tf, Fs, minDb=-20, maxDb=20, impulseResponse=False):
  """Plot frequency response of a digital transfer function in form (num, den)"""
  if impulseResponse:
    resp = np.fft.rfft(tf)
    freqs = np.linspace(0, Fs/2, len(resp))
  else:
    resp = freqz(tf[0], tf[1], worN=16384)
    freqs = Fs / (2 * pi) * resp[0]
    resp = resp[1]
  semilogx(freqs, db(abs(resp)))
  grid(True, which='major')
  grid(True, which='minor', linestyle="--")
  ylim(minDb, maxDb)
  xlabel("Frequency")
  ylabel("dB")
  title("Frequency Response")
  
def freqs_plot_db(tf, minDb=-20, maxDb=20):
  """Plot frequency response of a analog transfer function in form (num, den)"""
  resp = freqs(tf[0], tf[1])
  semilogx(resp[0] / (2 * pi), db(abs(resp[1])))
  grid(True, which='major')
  grid(True, which='minor', linestyle="--")
  ylim(minDb, maxDb)
  
def impulse(n):
  return append(array(1.0), zeros(n-1))
  
def imp_resp(tf, n):
  """Compute impulse response of transfer function in the form (num, den"""
  imp = impulse(n)
  return lfilter(tf[0], tf[1], imp)

  
  

