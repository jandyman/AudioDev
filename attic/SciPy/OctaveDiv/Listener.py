import octave_div
import matplotlib
# trigger interactive support in PyCharm
from EQ import *

# read wave data, produce and write transposed file
from Misc import read_wav_data, write_wav_data

rate, data = read_wav_data("wav/Bass Notes No Gap.wav")
trans_data = octave_div.octave_resample(data)
write_wav_data(trans_data, "wav/bass notes no gap transposed.wav")

# convert to energy and normalize
eng = data**2
eng = eng/max(eng)

# find notes in original signal
notes, ratio = octave_div.extract_notes_from_sig(eng)
# patch transposed signal into output according to original notes
transposed = octave_div.insert_transposed_notes(notes, trans_data, data)

# plot and write wav file
plt.plot(transposed)
write_wav_data(transposed, "bass notes octave divided")

tf = peaking(1500, 8, 1, 44100)
tr_filt = sig.lfilter(tf[0], tf[1], transposed)
write_wav_data(tr_filt, 'test.wav')


