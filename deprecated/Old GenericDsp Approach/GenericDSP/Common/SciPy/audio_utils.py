import numpy as np
import soundfile as sf
import sounddevice as sd

def write_wavfile(filename, data, sampleRate=44010, channels=1):
  sf = soundfile.SoundFile(filename, mode='w', format = 'WAV',
                           samplerate=sampleRate, channels=channels, subtype='FLOAT')
  sf.write(data.astype(np.float32))
  sf.close()
  
def choose_sound_device():
  print(sd.query_devices())
  sd.default.device = int(input("choose device:"))
  
  
    