"""Buffer-centric helpers for Faust+Python experimentation (shared tooling).

Load a WAV once, work on numpy buffers, play them in-process via sounddevice,
save when you want a snapshot. run_faust is a one-shot dawdreamer round-trip.
Import as `from lib.audio_buf_tools import run_faust, load_wav, play, output_path`.
"""

import os
import numpy as np
import soundfile as sf
import sounddevice as sd
import dawdreamer as daw

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "test_audio_out")


def load_wav(path):
  data, sr = sf.read(path, dtype="float32", always_2d=False)
  if data.ndim > 1:
    data = data.mean(axis=1).astype(np.float32)
  return data, sr


def save_wav(path, buf, sr=48000):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  sf.write(path, buf.astype(np.float32), sr)


def output_path(input_path, tag, out_dir=DEFAULT_OUT_DIR):
  """Build an output WAV path of the form <out_dir>/<input_stem>_<tag>.wav.

  Preserves spaces and capitalization of the input stem.
  Example: output_path("/.../Longer Bass Notes.wav", "varispeed_85pct")
           -> ".../test_audio_out/Longer Bass Notes_varispeed_85pct.wav"
  """
  stem = os.path.splitext(os.path.basename(input_path))[0]
  return os.path.join(out_dir, f"{stem}_{tag}.wav")


def play(buf, sr=48000):
  sd.play(buf, sr)
  sd.wait()


def run_faust(input_buf, dsp_path, params=None, sr=48000, bs=128, out_duration=None,
              all_outputs=False):
  """Render input_buf through a Faust .dsp and return the output.

  input_buf:    mono numpy array of input samples.
  dsp_path:     path to the Faust .dsp file; its directory is added to the Faust
                library search path so sibling .lib/.dsp imports resolve.
  params:       dict setting the .dsp's Faust UI controls BY LABEL — key = the
                label string from hslider/nentry/button/... (the leaf label, not
                the full group path), value = the raw value in that control's
                range, held for the whole render. e.g. hslider("thresh",0.3,...)
                -> {"thresh": 0.3}. Unknown keys raise, listing valid labels.
  sr:           sample rate in Hz.
  bs:           render block size in samples.
  out_duration: render length in seconds; defaults to the input duration. For
                varispeed with ratio < 1, use len(input_buf)/sr/ratio.
  all_outputs:  if False (default), return the first output channel as a 1-D
                array. If True, return ALL output channels as a 2-D array of
                shape (n_outputs, n_samples) — e.g. for a `process` that emits
                several probes, unpack them as `a, b = run_faust(..., all_outputs=True)`.
  """
  if out_duration is None:
    out_duration = len(input_buf) / sr

  engine = daw.RenderEngine(sr, bs)

  in_2d = np.expand_dims(input_buf.astype(np.float32), axis=0)
  src = engine.make_playback_processor("src", in_2d)

  faust = engine.make_faust_processor("faust")
  # Let Faust resolve sibling .dsp imports (e.g. triple_tap_delay.dsp) regardless of cwd.
  faust.faust_libraries_paths = [os.path.dirname(os.path.abspath(dsp_path))] + list(faust.faust_libraries_paths)
  if not faust.set_dsp(dsp_path):
    raise RuntimeError(f"Faust failed to compile: {dsp_path}")

  engine.load_graph([
    (src, []),
    (faust, ["src"]),
  ])

  # Look up parameters by short label, set by integer index. The string-path form
  # of set_parameter requires dawdreamer's path table to have been primed by some
  # earlier parameter access; using indices sidesteps that quirk entirely.
  if params:
    label_to_idx = {d["label"]: d["index"] for d in faust.get_parameters_description()}
    for name, val in params.items():
      if name not in label_to_idx:
        raise RuntimeError(f"parameter {name!r} not found. Available: {sorted(label_to_idx)}")
      faust.set_parameter(label_to_idx[name], val)

  engine.render(out_duration)

  out = engine.get_audio()              # (n_outputs, n_samples)
  if all_outputs:
    return out
  return out[0] if out.ndim > 1 else out
