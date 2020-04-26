import numpy as np
import soundfile as sf

def write_wavfile(filename, data):
  sf = soundfile.SoundFile(filename, mode='w', format = 'WAV',
                           samplerate=44100, channels=2, subtype='FLOAT')
  sf.write(data.astype(np.float32))
  sf.close()
  
# =============================================================================
# def write_wavfile(filename, data, length = 10.0):
#   SR = 44100
#   file = sf.SoundFile(filename, mode='w', format = 'WAV',
#                            samplerate=SR, channels=1)
#   nsamps = length * SR
#   nreps = int(nsamps / data.size)
#   for x in range(nreps):
#     file.write(data.astype(np.float32))
#   file.close()
#   
# =============================================================================
  
# tf = EQ.lf_shelf_12(1000,18,44100)
# tf2 = EQ.peaking(2000,18,10,44100)

# EQ.freq_plot_db(tf,44100)
# EQ.freq_plot_db(tf2,44100)

import EQ
x = EQ.hf_shelf_6(3000, 12, 44100)

# Test of using ctypes to access a C library

from ctypes import *
import numpy as np
coeflib = cdll.LoadLibrary('coefgen.dylib')

# test a really simple add function
# void AddTwo(double in, double* out) // two output values
coeflib.AddTwo.argtypes = [c_double, c_double * 2]
result_type = c_double * 2
result = result_type(0, 0)
npresult = np.ctypeslib.as_array(result) 

# now set up the prototype for the coefs function itself
coef_func = coeflib.EqCoefs
# int EqCoefs(double *coefs /* 5 elements */, uint32_t type, uint32_t order, 
#             double fc, double boost, double q, double fs)
coef_func.argtypes = [c_double*5, c_int32, c_int32, c_double, c_double, c_double, c_double]
coef_func.restype = c_int32

# wrapper function to deal with the C function more conveniently
def get_coefs(fs = 41000, type = 0, order = 2, fc = 1000, boost = 6, q = 1):
  result_type = c_double * 5
  result = result_type()
  coef_func(result, type, order, fc, boost, q, fs)
  np_result = np.ctypeslib.as_array(result)
  num = np_result[0:3]
  den = np.zeros(3)
  den[0] = 1
  den[1:3] = np_result[3:5]
  return (num, den)

