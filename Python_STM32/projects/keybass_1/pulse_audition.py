"""
Audition the keybass_1 pulse generator (no plots — just listen).

Run from PyCharm (scipy env). Generates a longer, level-reduced buffer and plays
it to an explicitly named output device. NOTE: the system-default output here is
BlackHole (a virtual loopback) — playing to the default makes no sound, so set
`device` to a real output below ("MacBook Pro Speakers", "Scarlett", ...).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.audio_buf_tools import play

from pulse_generator import pulse

def run(freq, duty, transition, sr, dur, amp, device):
  n = int(dur * sr)
  y = pulse(freq, n, sr=sr, duty=duty, transition=transition) * amp
  print(f"playing {freq:g} Hz, duty {duty:g}, N={transition}, {dur:g}s -> {device!r}")
  play(y, sr, device=device)

if __name__ == '__main__':
  sr         = 48000
  freq       = 110.0   # A2
  duty       = 0.5
  transition = 5       # N: raised-cosine edge width in samples
  dur        = 2.0     # seconds — long enough to actually judge the tone
  amp        = 0.2     # a full-scale pulse is harsh; back it off for listening
  device     = "MacBook Pro Speakers"   # or "Scarlett 2i2", or a device index
  run(freq, duty, transition, sr, dur, amp, device)
