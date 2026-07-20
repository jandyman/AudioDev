import numpy as np
from numpy.typing import ArrayLike
from typing import List

def ramp(x: float, target: float, increment: float) -> float:
  if x == target: return x
  if x < target: return min(target, x+increment)
  if x > target: return max(0, x-increment)

def increment(fs: float, time: float) -> float:
  return 1 / (fs * time)

class Mixer:
  def __init__(s, n_channels: int, time: float, fs: float = 44100):
    s.fs = fs
    s.n_channels = n_channels
    s.set_fade_time(time)
    s.last_gains = [0] * n_channels

  def set_fade_time(s, time: float):
    s.increment = 1 / (s.fs * time)

  # inputs first, then targets
  def proc(s, inputs: [np.ndarray], outputs: [np.ndarray]):
    assert len(inputs) == s.n_channels*2
    assert len(outputs) == s.n_channels+1
    size = inputs[0].size
    assert all(x.size == size for x in inputs)
    for i in range(size):
      sum = 0
      for ch in range(s.n_channels):
        gain = ramp(s.last_gains[ch], inputs[ch+s.n_channels][i], s.increment)
        s.last_gains[ch] = gain
        outputs[ch+1][i] = gain
        sum += gain * inputs[ch][i]
      outputs[0][i] = sum

  def is_active(s) -> bool:
    return all(s.targets != s.gains)


class CrossFade:
  def __init__(s, time: float, fs: float = 44100):
    s.gains = [1,0]  # gains for channels 1 and two
    s.target = 0     # "pointer" = MUST BE EITHER ZERO OR ONE!
    s.increment = 1 / (fs * time)

  def proc(s, audio1: ArrayLike, audio2: ArrayLike) -> ArrayLike:
    t = s.target
    assert audio1.size == audio2.size
    result = np.zeros(audio1.size)
    for i in range(audio1.size):
      # fade up
      if s.gains[t] < 1: s.gains[t] = min(1, s.gains[t] + s.increment)
      # fade down
      if s.gains[t-1] > 0: s.gains[t-1] = max(0, s.gains[t-1] - s.increment)
      sig1 = s.gains[0] * audio1[i]
      sig2 = s.gains[1] * audio2[i]
      result[i] = sig1 + sig2
    return result

  def toggle_target(s):
    s.target = (1 - s.target)

  @property
  def is_active(s) -> bool:
    return s.gains[0] != 0 or s.gains[1] != 0



if __name__ == '__main__':

  from matplotlib.pyplot import plot
  from streaming import test_streaming_x_1
  sig_a = np.ones(3000)
  sig_b = np.ones(3000) * 0.5
  cross_fader = CrossFade(.01)
  result = np.zeros(3000)
  result[0:1000] = test_streaming_x_1(lambda x, y: cross_fader.proc(x, y),
                                      [sig_a[0:1000], sig_b[0:1000]], 100)
  cross_fader.target = 1
  result[1000:2000] = test_streaming_x_1(lambda x, y: cross_fader.proc(x, y),
                                         [sig_a[1000:2000], sig_b[1000:2000]], 100)
  cross_fader.target = 0
  result[2000:3000] = test_streaming_x_1(lambda x, y: cross_fader.proc(x, y),
                                         [sig_a[2000:3000], sig_b[2000:3000]], 100)
  plot(result)
  pass


