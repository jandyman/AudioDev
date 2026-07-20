from block_streaming import *
from env import *
from filters import BiquadChain64
import numpy as np

import matplotlib.pyplot as plt
plt.ion()

fs, data = read_wav_data("../OctaveDiv/wav/Bass Notes.wav")
fc = 100
num, den = butter(4, fc / (fs / 2))
biquad_chain = pybind_blk(BiquadChain64(num, den))
out = np.zeros(len(data), dtype=np.float64)
biquad_chain.proc([data, out])
pass

