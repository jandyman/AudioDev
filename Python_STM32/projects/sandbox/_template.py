"""
Sandbox experiment template — copy me to <something>_lab.py and hack.

Run from PyCharm (scipy env). No CLI args; config vars live at the bottom.
Interactive plots only (no savefig). Never use a `test_` prefix — pytest would
collect it and block the plot window. See docs/python_experimentation.md.
"""
import sys, os

# Shared tooling. This folder is two levels under Python_STM32, so the same path
# header every demo uses works verbatim. Must precede `import matplotlib.pyplot`
# (lib.diagnostic_plot sets the backend + cache dir).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono, mark_events, out_path

import numpy as np
import matplotlib.pyplot as plt

# To drive a built C++ graph from a sibling project, add its dir and import its
# module (build it first: `cd ../pitch_shifter && make -f pitch_shifter.make`):
#   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pitch_shifter'))
#   from build.pybind_pitch_shifter import pitch_shifter

def run(in_file):
  sr, audio = load_audio_mono(in_file)           # bare name -> repo-root test_audio/
  N = len(audio); t = np.arange(N) / sr

  # ---- your experiment here -------------------------------------------------
  # Pure numpy, or drive a graph and tap probes, e.g.:
  #   ps = pitch_shifter(); ps.init(sr); ps.set_param('lc.pitch_ratio', 0.5)
  #   out = ps.process_chunk(audio.astype(np.float32))
  #   trig = ps.get_buffer('atk.trigger', N)
  result = audio
  # Save a result under test_audio_out/ with:
  #   import scipy.io.wavfile as wav
  #   wav.write(out_path(f'{os.path.splitext(in_file)[0]}_result.wav'), sr, result)
  # ---------------------------------------------------------------------------

  fig, ax = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
  ax[0].plot(t, audio, lw=0.5, color='0.6'); ax[0].set_ylabel('input')
  ax[1].plot(t, result, lw=0.6, color='C0'); ax[1].set_ylabel('result')
  # Mark discrete events across both panels, e.g.:
  #   mark_events(ax, t, trig, color='orange', label='trigger')
  ax[0].set_xlim(0, t[-1])
  for a in ax: a.grid(True, alpha=0.3)
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])   # scroll=zoom, shift+scroll=pan
  plt.show()

if __name__ == '__main__':
  in_file = "Fourth Test.wav"
  run(in_file)
