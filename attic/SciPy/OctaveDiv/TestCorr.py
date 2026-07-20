from Misc import *
import matplotlib.pyplot as plt

rate, data = read_wav_data("wav/Bass Notes No Gap.wav")

plt.plot(data)

corr = crosscorr_against_later(data, 4000, 20000, 2**16)

plt.figure(2)
plt.plot(corr)
plt.show()



