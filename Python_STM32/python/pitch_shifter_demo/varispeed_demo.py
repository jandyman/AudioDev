"""Varispeed demo around triple_tap_delay via a thin Faust wrapper.

Run in PyCharm debug mode with a breakpoint on the `pass` at the bottom.
From the console:
  play(audio)                                 # original file
  play(note)                                  # default-sliced note
  play(shifted)                               # default-ratio shift
  play(varispeed(note, 0.7))                  # try a different ratio
  play(varispeed(slice_note(audio, 2.0, 0.5), 0.6))

  # snapshot to test_audio_out/ with input-stem-aware naming:
  save_wav(output_path(SRC_PATH, "varispeed_85pct"), shifted)

300 ms delay cap in triple_tap_delay constrains input length:
  ratio 0.5  -> ~0.3 s input max
  ratio 0.7  -> ~0.7 s input max
  ratio 0.85 -> ~1.7 s input max
  ratio 0.9  -> ~2.7 s input max
"""

import os
import numpy as np

from audio_buf_tools import load_wav, play, save_wav, run_faust, output_path

HERE = os.path.dirname(os.path.abspath(__file__))
DSP_PATH = os.path.join(HERE, "varispeed_wrapper.dsp")

def slice_note(buf, start_s, dur_s):
  s = int(start_s * sr)
  e = s + int(dur_s * sr)
  return buf[s:e]

def varispeed(buf, ratio):
  out_dur = len(buf) / sr / ratio
  return run_faust(buf, DSP_PATH, params={"ratio": ratio}, sr=sr, out_duration=out_dur)

# --- knobs (edit these) ---
SRC_PATH = "/Users/andy/Dropbox/Developer/AudioDev/test_audio/longer bass notes.wav"
NOTE_START_S = 0.0
NOTE_DUR_S = 1.0
RATIO = 0.85

# --- setup ---
audio, sr = load_wav(SRC_PATH)         # sr follows the file (Faust is rate-agnostic)
note = slice_note(audio, NOTE_START_S, NOTE_DUR_S)
shifted = varispeed(note, RATIO)

# Set a breakpoint on the next line. Then in the PyCharm console try play(...).
pass
