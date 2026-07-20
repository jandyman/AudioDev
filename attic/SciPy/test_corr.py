import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
import soundfile

def autocorr(data, n_samps, offset=0):
  data_len = data.size
  ref = data[offset:offset+n_samps]
  result = np.zeros(n_samps)
  assert offset + n_samps < data_len
  for i in range(n_samps):
    cmp = data[offset:offset+n_samps]
    result[i] = np.sum(cmp * ref)
    offset += 1
  return result

def get_xyz(two_d_array):
  lx = len(two_d_array)
  ly = len(two_d_array[0])
  lz = lx * ly
  x = np.zeros(lz)
  y = np.zeros(lz)
  z = np.zeros(lz)
  z_idx = 0
  for x_idx in range(lx):
    for y_idx in range(lx):
      x[z_idx] = x_idx
      y[z_idx] = y_idx
      z[z_idx] = two_d_array[x_idx][y_idx]
      z_idx += 1
  return x,y,z

if __name__ == '__main__':

  bass_data, rate = soundfile.read("OctaveDiv/wav/Bass Notes No Gap.wav")
  r = range(11000, 15000, 500)
  data = []
  for i in r:
    c = autocorr(bass_data, 1000, i)
    data.append(c)

  # start = 11000
  # len = 2000
  # c = autocorr(bass_data, len, start)

  ax = plt.figure().add_subplot(projection='3d')
  # X, Y, Z = axes3d.get_test_data(0.05)
  X, Y, Z = get_xyz(data)

  # Plot the 3D surface
  ax.plot_trisurf(X, Y, Z)

  two_d_data = [[1,3],[10, 11]]

  plt.figure(2)
  plt.plot(bass_data)
  plt.show()
  pass