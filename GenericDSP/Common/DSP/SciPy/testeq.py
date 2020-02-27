import numpy as np
import soundfile as sf

def write_wavfile(filename, data):
  sf = soundfile.SoundFile(filename, mode='w', format = 'WAV',
                           samplerate=44100, channels=2, subtype='FLOAT')
  sf.write(data.astype(np.float32))
  sf.close()
  
  
# tf = EQ.lf_shelf_12(1000,18,44100)
# tf2 = EQ.peaking(2000,18,10,44100)

# EQ.freq_plot_db(tf,44100)
# EQ.freq_plot_db(tf2,44100)

import EQ
x = EQ.hf_shelf_6(3000, 12, 44100)

from ctypes import *
import numpy as np
coeflib = cdll.LoadLibrary('coefgen.dylib')
coeflib.AddTwo.argtypes = [c_double, c_double * 2]
result_type = c_double * 2
result = result_type(0, 0)
npresult = np.ctypeslib.as_array(result)
coeflib.EqCoefs.argtypes = [c_double*5, c_int32, c_int32, c_double, c_double, c_double, c_double]
coeflib.EqCoefs.restype = c_int32