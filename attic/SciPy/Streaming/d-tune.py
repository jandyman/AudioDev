import numpy as np
from mixers import Mixer
from resample import Resampler, JosFractDelay
from env import FollowPeaks, AttRel, ButterRms
from filters import BiquadChain64
from enum import Enum
from math_and_logic import EdgeDetector, ZeroCrossingDetector
from block_streaming import pybind_blk
from scipy.signal import butter
from math_and_logic import Square, Sqrt, Log, Exp, Sub, Abs, Mult, Comparator
from typing import List
from delaybuf import Delays
from dataclasses import dataclass

"""
Three states: Idle, Attack, and Sustain. 
Idle -> Attack: On reception of attack
Attack -> Sustain: Expiration of Attack Timer
Attack -> Idle: Detection of Note End
Sustain -> Idle: Good question, lack of periodicity and/or envelope below certain level

During Idle, look for zero crossings of the same polarity and cross fade - no need to resample
Onset of Attack mode starts resampling and Attack timer
If Sustain mode is entered, look for splice points. Try zero crossings, look at period consistency, or ??

There are two delay generators because during Sustain we will need to crossfade between two delayed streams
at splice points, so we use a ping pong approach between the generators

Switching from Idle to Attack triggers a down fade on the live stream. Delay generator A is initialized with 
zero delay (or filtLength/2) and an upfade is started.

Switching to Sustain is a pure state shift, we start looking for splice points. If we do a splice during 
Sustain mode, we set up a down fade on the active delay generator. We initialize the other delay generator 
and start an up fade. That generator can now be considered active one. When the down face on the now inactive 
generator, it can be disabled to save cycles

If a note end is detected, both delay generators are set to fade down, even though only one may be active. 
live stream is set to up fade. We enter Idle mode.

If Attack is detected during Idle when fading is still happening, there is no hazard because the down fading 
generator is already marked as inactive.

"""

class NoteStates(Enum):
  Idle = 0         # note end detected
  Attack = 2      # attack detected
  Sustain = 1      # attack timer expired

class DTune:

  def __init__(s, interval: int, filt_length: int, fs: float=44100, bufsiz=128):
    s.state = NoteStates.Idle
    s.note_thresh = .75
    s.fs = fs
    s.bufsiz = bufsiz
    s.dly_increment = 1 - 2 ** (-interval / 12)
    s.resampler = Resampler(JosFractDelay(10000/fs, filt_length, 3), dly_len=50000)
    s.abs = Abs()
    s.abs.out = s.get_zeros()
    s.att_rel = AttRel(attTime=.004, relTime=10, fs=fs)
    s.att_rel.out = s.get_zeros()
    s.env_det1 = ButterRms(100, fs)
    s.env_det1.out = s.get_zeros()
    s.env_det2 = ButterRms(20, fs)
    s.env_det2.out = s.get_zeros()
    s.env2_dly = Delays(bufsiz+3000, [2000])
    s.env2_dly.out = s.get_zeros()
    s.track_maxs = TrackMaxs()
    s.track_maxs.outs = [s.get_zeros(), s.get_zeros()]
    # s.atk_div = Div()
    # s.atk_div.out = s.get_zeros()
    # s.noise_det = AttRel(attTime=1, relTime=.02, fs=fs)
    # s.noise_det.out = s.get_zeros()
    # s.noise_div = Div()
    # s.noise_div.out = s.get_zeros()
    s.note_detect = NoteStateDetect()
    s.note_detect.out = s.get_zeros()

    s.t_active = 0  # 0 or 1 depending on the active delay channel
    s.t_delay = [0,0]
    s.filt_length = filt_length
    s.prev_sample = 0
    s.attack_timer = 0

  def enter_idle(s):
    s.state = NoteStates.Idle

  def enter_attack(s):
    s.state = NoteStates.Attack
    s.mixer.set_fade_time(.005)
    s.t_delay[s.t_active] = s.filt_length/2 + 1
    s.attack_timer = s.fs * 2

  def enter_sustain(s):
    s.state = NoteStates.Sustain

  def get_zeros(s):
    return np.zeros(s.bufsiz, dtype='float32')

  # inputs are sig, a,
  def proc(s, bufs: List[np.ndarray]):
    input = bufs[0]
    bufsize = input.size
    sbuf = np.zeros(bufsize)
    sbuf[0] = s.state.value
    s.env_det1.proc([input, s.env_det1.out])
    s.env_det2.proc([input, s.env_det2.out])
    s.env2_dly.proc([s.env_det2.out, s.env2_dly.out])
    s.att_rel.proc([s.env_det2.out, s.att_rel.out])
    s.track_maxs.proc([s.env_det1.out] + s.track_maxs.outs)
    s.abs.proc([input, s.abs.out])
    # s.atk_div.proc([s.abs.out, s.att_rel.out, s.atk_div.out])
    # s.noise_det.proc([s.abs.out, s.noise_det.out])
    # s.noise_div.proc([s.abs.out, s.noise_det.out, s.noise_div.out])
    s.note_detect.proc([s.abs.out, s.track_maxs.outs[0], s.att_rel.out, s.note_detect.out])


    #r = s.follow_peaks_out[0]/s.att_rel_out[0]
    s.env_mult.proc([s.env_det1.out, s.env_mult.out])

    s.env_cmp([s.env_mult.out, abs.out, a])
    #e = s.note_end_detect.proc(r)
    dlys = [np.zeros(bufsize) for _ in [0,1]]
    mix_targets = [np.zeros(bufsize) for _ in [0,1,2]]

    for i in range(bufsize):
      match s.state:
        case NoteStates.Idle:
          if a[i] != 0: s.enter_attack()
          else:
            mix_targets[0][i] = 1
            mix_targets[1][i] = 0
        case NoteStates.Attack:
          s.attack_timer -= 1
          if s.attack_timer <= 0:  s.enter_sustain()
          if e[i] != 0:  s.enter_idle()
          else:
            mix_targets[0][i] = 0
            mix_targets[1 + s.t_active][i] = 1
            mix_targets[2 - s.t_active][i] = 0
        case NoteStates.Sustain:
          # should be looking for splice points
          if a[i] != 0:  s.enter_attack()

      dlys[s.t_active][i] = s.t_delay[s.t_active]
      s.t_delay[s.t_active] += s.dly_increment
      sbuf[i] = s.state.value

    t = [np.zeros(input.size) for _ in dlys]
    s.resampler.proc([input]+dlys, t)
    mixin = [input] + t + mix_targets
    mixout = [bufs[1]] + [np.zeros(input.size) for _ in mix_targets]
    s.mixer.proc(mixin, mixout)



class Div:
  def proc(s, bufs: List[np.ndarray]):
    log_blk = pybind_blk(Log())
    buf3 = np.zeros(bufs[0].size, dtype='float32')
    exp_blk = pybind_blk(Exp())
    buf4 = np.zeros(bufs[0].size, dtype='float32')
    sub_blk = Sub()
    log_blk.proc([bufs[0], buf3])
    log_blk.proc([bufs[1], buf4])
    sub_blk.proc([buf3, buf4, buf3])
    exp_blk.proc([buf3, bufs[2]])



# If in attack mode, only a transition to Idle via the TrackMaxs level can transition to
# Idle. If in sustain mode, a transition to Attack Mode can occur directly if the level
# is substantially above the noise detector level. It's probably not possible to detect
# a transition from sustain to idle for a gradually decreasing string vibration. Transition
# from attack to sustain is via timer.
#
# inputs
#   Track Maxs - detects note ends except fade out, triggers Idle
#   Attack Div - detects note starts in Idle or sustain
#   Noise Div - detects note starts in Sustain (fade out situation)
# output
#   Mode - Attack, Sustain, Idle. The point of Attack I guess is to avoid a double or noise
#   div trigger. Also in sustain we look for loop opportunities with the delay

class NoteStateDetect:
  def __init__(s):
    s.state = NoteStates.Sustain
    s.atk_timer = 0
    s.atk_ampl = 0

  def enter_attack(s):
    s.state = NoteStates.Attack
    s.atk_timer = 4400

  def proc(s, bufs):
    abs = bufs[0]
    mx = bufs[1]
    att_rel = bufs[2]
    for i in range(bufs[0].size):
      match s.state:
        case NoteStates.Attack:
          if s.atk_timer == 0:
            s.state = NoteStates.Sustain
          else:
            if s.atk_timer == 3400:
              s.atk_ampl = att_rel[i]
            s.atk_timer -= 1
        case NoteStates.Sustain:
          if abs[i]/2 > mx[i] and abs[i] > att_rel[i] / 8:
            s.enter_attack()
      bufs[3][i] = s.state.value

q

class TrackMinMax:
  def __init__(s):
    s.x1 = 0
    s.x2 = 0
    s.last_min_max = 0

  def proc(s, bufs):
    for i in range(bufs[0].size):
      x = bufs[0][i]
      if s.cond(x):
        s.last_min_max = x
      bufs[1][i] = s.last_min_max
      bufs[2][i] = x / s.last_min_max
      s.x2 = s.x1
      s.x1 = x

  def cond(s,x):
    assert False, "TrackMinMax is an abstract class"

class TrackMaxs(TrackMinMax):
  def cond(s,x):
    return s.x2 < s.x1 and x < s.x1

class TrackMins(TrackMinMax):
  def cond(s,x):
    return s.x2 > s.x1 and x > s.x1



if __name__ == '__main__':
  from block_streaming import spool_proc
  from block_streaming import read_wav_data
  import matplotlib.pyplot as plt
  from EQ.EQ import freq_plot_db
  plt.ion()
  #import sounddevice as sd
  rate, data = read_wav_data("../OctaveDiv/wav/Bass Notes No Gap.wav")

  # test Div block
  div = Div()
  a = np.linspace(1,10,10, dtype='float32')
  b = 2 * np.ones(len(a), dtype='float32')
  div_out = np.zeros(len(a), dtype='float32')
  div.proc([a, b, div_out])

  s = data[120000:]
  bufsiz = 100000
  d_tune = DTune(interval=2, filt_length=8, fs=rate, bufsiz=bufsiz)
  spool_proc(d_tune, [data], 1, bufsiz)

  plt.plot(y[0])
  sd.play(s, 44100, blocking=True)
  sd.play(y, 44100, blocking=True)
  pass










