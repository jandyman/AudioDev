# AudioDev - Claude Context

Cross-project configuration for audio development work.

## Python Environment

Always activate the conda environment before running Python scripts:
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate scipy
```
This environment has numpy, matplotlib, dawdreamer, and other dependencies needed for testing Faust modules and audio processing.

## Project Structure

- **max_externals/** - Max/MSP external objects (C++)
- **dsp_library/** - Shared DSP code including Faust modules
- **audio-graph-python/** - Python testing framework
- **Max Experiments/** - Max patchers and documentation
- **PitchShifter/** - Pitch shifter algorithm development

## Current Task: Dual Tap Delay Pitch Shift Test

Create a Python test using the dual tap delay with:

1. **Buffer size**: Already increased to 10 seconds (1920000 samples) in `dsp_library/faust/dual_tap_delay.dsp`

2. **Input file**: `audio-graph-python/test_audio/Bass Notes.wav`

3. **Control signals**: Two delay ramps that increment over time
   - Tap 1: Pitch shift down a **fourth** (ratio 3/4 = 0.75)
     - Delay increment = 0.25 samples/sample
   - Tap 2: Pitch shift down an **octave** (ratio 1/2 = 0.5)
     - Delay increment = 0.5 samples/sample

4. **Output**: Save both outputs to `test_audio_out/` folder as wav files

5. **Math reference**:
   - For pitch ratio R (where R < 1 = lower pitch):
   - Read speed relative to write = R
   - Delay increment per sample = (1 - R)
   - Convert to ms: delay_increment_ms = (1 - R) / sample_rate * 1000

This is foundation work for a pitch shifter - looping and attack detection will come later.
