# Audio Testing with Python and BlackHole

This system allows Python to capture and analyze audio output from Max via BlackHole virtual audio device.

## Setup

### 1. Install Dependencies

```bash
conda activate your_env
pip install sounddevice scipy matplotlib
```

(You already have `pythonosc` installed)

### 2. Configure Max Audio Output

In Max:
1. Open **Options → Audio Status**
2. Set **Output Device** to **BlackHole 2ch** (or 16ch)
3. Keep **Input Device** as your normal audio interface (for monitoring)

### 3. Find BlackHole Device Index

```bash
python list_audio_devices.py
```

Look for BlackHole in the output and note its device index (e.g., `2`).

Example output:
```
BlackHole Devices Found:
  Index 2: BlackHole 2ch
    Max Input Channels: 2
    Max Output Channels: 2
    Default Sample Rate: 48000.0
```

## Usage

### Basic Audio Capture

Capture 5 seconds of audio and save to WAV file:

```bash
python capture_from_blackhole.py --device 2 --duration 5.0 --save
```

Options:
- `--device <index>`: BlackHole device index (required)
- `--duration <seconds>`: Recording duration (default: 5.0)
- `--rate <Hz>`: Sample rate (default: 48000)
- `--channels <n>`: Number of channels (default: 2)
- `--save`: Save recording to WAV file
- `--output <filename>`: Output filename (auto-generated if not specified)

### Real-Time FFT Monitoring

Live visualization of Max's audio output:

```bash
python monitor_audio_fft.py --device 2
```

This shows:
- **Time domain**: Waveform display
- **Frequency domain**: FFT spectrum (20 Hz - 24 kHz)

Close the plot window to stop monitoring.

### Automated DSP Testing

Test andy.gain~ external automatically:

```bash
python test_dsp_gain.py --device 2
```

**Setup for testing:**
1. Open `andy.gain_osc.maxpat` in Max
2. Turn on audio (DSP)
3. Add a test tone generator (e.g., `cycle~ 440`)
4. Connect test tone → `andy.gain~` → `dac~`
5. Set Max audio output to BlackHole
6. Run the test script

The script will:
- Test unity gain (1.0)
- Test mute (0.0)
- Test gain scaling (0.0, 0.25, 0.5, 0.75, 1.0)
- Verify that RMS scales proportionally with gain

## Workflow Examples

### Example 1: Verify Gain External

```bash
# 1. Find BlackHole device
python list_audio_devices.py

# 2. Set up Max:
#    - Open andy.gain_osc.maxpat
#    - Add: cycle~ 440 → andy.gain~ → dac~
#    - Set audio output to BlackHole
#    - Turn on audio

# 3. Run automated test
python test_dsp_gain.py --device 2
```

### Example 2: Frequency Response Analysis

```bash
# 1. Set up Max with sine sweep generator
#    - Use plugin~ or custom sweep generator
#    - Output through your filter to BlackHole

# 2. Monitor live FFT
python monitor_audio_fft.py --device 2

# 3. Or capture and analyze
python capture_from_blackhole.py --device 2 --duration 10.0 --save --output filter_sweep.wav

# 4. Analyze in Python
ipython
>>> from scipy.io import wavfile
>>> rate, data = wavfile.read('filter_sweep.wav')
>>> # Perform frequency response analysis...
```

### Example 3: Impulse Response Capture

```bash
# 1. Set up Max with impulse generator
#    - bang → click~ → reverb/delay/filter → dac~

# 2. Capture IR
python capture_from_blackhole.py --device 2 --duration 2.0 --save --output impulse_response.wav

# 3. Analyze characteristics in Python/scipy
```

## Monitoring While Working

You can monitor Max's audio output in real-time while developing:

**Terminal 1:**
```bash
python monitor_audio_fft.py --device 2
```

**Terminal 2:**
```bash
python diagnose_osc.py  # Send OSC commands
```

This gives you visual feedback on audio output while controlling parameters via OSC.

## Tips

### Hearing the Audio

Since Max outputs to BlackHole (not speakers), you won't hear it directly. Options:

1. **Use Max's audio output routing:**
   - In Max, add a `send~ myaudio` after your external
   - Create a `receive~ myaudio` → `dac~` pair on a separate output
   - Set that output to your speakers

2. **Use Audio MIDI Setup (Mac):**
   - Create a Multi-Output Device combining BlackHole + Speakers
   - Set Max output to Multi-Output Device
   - Now audio goes to both BlackHole (for Python) and speakers

3. **Monitor in Python:**
   - Modify `monitor_audio_fft.py` to play audio via sounddevice
   - (More complex, adds latency)

### Sample Rate Matching

Make sure Max's sample rate matches Python's (default 48000 Hz):
- Check Max: **Options → Audio Status → Sample Rate**
- Use `--rate` flag in Python scripts to match

### Troubleshooting

**No audio captured in Python:**
- Check Max audio output is set to BlackHole
- Verify audio is ON in Max (DSP button)
- Check signal is reaching `dac~` (meters should show activity)
- Verify correct device index with `list_audio_devices.py`

**Distorted/clipped audio:**
- Check levels in Max (should be < 1.0)
- Reduce test signal amplitude

**High latency:**
- Reduce block size: `--block 1024` (monitor_audio_fft.py)
- Use smaller capture durations

## Next Steps

This system can be extended to:
- Automated unit tests for all DSP externals
- CI/CD integration (headless testing)
- Frequency response plotting
- THD (Total Harmonic Distortion) measurement
- Impulse response analysis
- Cross-correlation between input/output

The foundation is now in place for comprehensive DSP testing!
