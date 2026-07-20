import numpy as np
import scipy.signal as sig

from numpy import zeros, ones

def octave_resample(input):
  out = zeros(len(input) * 2)
  out[0::2] = input
  ir = sig.firwin2(64, [0, .25, .75, 1], [2, 2, 0, 0])
  out = sig.lfilter(ir, 1, out)
  return out
  
def att_rel_coef(Tc, Fs):
  return 1 - np.exp(-1 / (Fs * Tc))
  
def att_rel(input, attTime, relTime, Fs):
  attCoef = att_rel_coef(attTime, Fs)
  relCoef = att_rel_coef(relTime, Fs)
  out = np.zeros(np.shape(input))
  lastout = 0;
  for idx, samp in enumerate(input):
    if samp > lastout:
      lastout = attCoef * (samp - lastout) + lastout
    else:
      lastout = relCoef * (samp - lastout) + lastout
    out[idx] = lastout
  return out
  
def follow_peaks(input, Fs, attTime=.01, div=4000000):
  out = np.zeros(np.shape(input))    
  attCoef = att_rel_coef(attTime, Fs)
  lastpeak = 0
  lastout = 0
  sampSincePeak = 0;
  for idx, samp in enumerate(input):
    if samp > lastout:
      lastout = attCoef * (samp - lastout) + lastout
      lastpeak = lastout
      sampSincePeak = 0
      out[idx] = lastout
    else:
      incr = lastpeak * sampSincePeak / div
      lastout = lastout - incr
      if lastout < 0: 
        lastout = 0
      sampSincePeak += 1
      out[idx] = lastout
  return out   
  
def extract_notes_by_thresh(sig, thresh):
  state = False
  compOut = sig > (thresh * np.ones(np.shape(sig)))
  result = []
  for idx, val in enumerate(compOut):
    if val == state:
      continue
    elif val == True:
      risingEdge = idx
      state = val
    else:
      result.append([risingEdge, idx])
      state = val
  return result  
        
def extract_notes_from_sig(input):
  engEnv = att_rel(input, .004, .4, 44100)
  pks = follow_peaks(input, 44100, .001, 1500000)
  ratio = pks/engEnv
  return extract_notes_by_thresh(ratio, .3), ratio
      
def insert_transposed_notes(notes, transposed, orig):
  output = np.zeros(np.shape(orig))
  for note in notes:
    idx, end = note
    srcidx = idx*2 - 200
    srcidx = max(0, srcidx)
    insert_note(transposed, srcidx, output, idx, end - idx)
  return output
  
def insert_note(src, srcidx, dst, dstidx, len):
  # first the fade in
  fadeInLen = 200
  fadeEnv = np.linspace(1/fadeInLen, 1, fadeInLen)
  end = fadeInLen 
  dst[dstidx:dstidx+end] = fadeEnv * src[srcidx:srcidx+end]
  # now the middle part
  pos = fadeInLen
  fadeOutLen = 500
  end = len - fadeOutLen
  dst[dstidx+pos:dstidx+end] = src[srcidx+pos:srcidx+end]
  # now the fade out
  fadeEnv = np.linspace(1, 0, fadeOutLen)
  pos = end
  dst[dstidx+pos:dstidx+len] = fadeEnv * src[srcidx+pos:srcidx+len]
  
  
  
  
  