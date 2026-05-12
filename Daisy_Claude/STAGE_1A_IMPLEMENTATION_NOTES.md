# Stage 1a Implementation Notes — EQ + Remote Parameter Control

## Current State (Working, but with Scaling Issue)

**Firmware:**
- `seed_h750/src/eq.c`: Biquad coefficient computation (hi-shelf + LPF)
- `seed_h750/src/params.c`: Hierarchical parameter tree in DTCMRAM
- `seed_h750/src/audio.c:process_audio()`: Calls `eq_update_from_params()` every ISR (~1 kHz)

**Host Tool:**
- `seed_h750/tools/param_walker.py`: Reads parameter tree via OpenOCD telnet
- `seed_h750/tools/OPENOCD_RECIPE.md`: Complete workflow documentation
- Auto-resumes halted CPU on connection

## The Problem: CPU Load in ISR

**Current flow (audio.c line 105):**
```c
static void process_audio(uint32_t offset) {
  eq_update_from_params();  // ← CALLED EVERY ISR
  // ... then filter sample-by-sample
}
```

**What `eq_update_from_params()` does (every ISR):**
1. Read 6 parameter values from the tree (floats in DTCMRAM)
2. Compare against cached previous values
3. If any changed:
   - Call `compute_hishelf()` (trig, multiply, divide, sqrt)
   - Call `compute_lpf_biquad()` (trig, multiply, divide)
4. Update the live biquad coefficients in `eq_ch[0]` and `eq_ch[1]`

**Cost at 48 kHz sample rate:**
- ISR fires ~500 times/sec (HT + TC events, 2 per 96-sample block)
- Each ISR: potentially trigonometry + coefficient writes
- At full DSP load (e.g., multichannel pitch shifter), this will cause audio glitches

## Desired Architecture: Background Parameter Update

**Separate concerns:**

1. **ISR (audio.c):**
   - Just process samples with current coefficients
   - Check if `params_dirty` flag is set
   - If set: atomically swap in new coefficients and clear the flag

2. **Background task (new):**
   - Poll `params_dirty` flag
   - When set: compute new coefficients (trig is OK here, slow is fine)
   - Atomically update `eq_new_ch[0]` and `eq_new_ch[1]`
   - Signal ISR that new coefficients are ready
   - ISR swaps them in and clears `params_dirty`

3. **Host (macOS app):**
   - Walk the parameter tree
   - When user changes a parameter: write new value, set `params_dirty` flag
   - Can't write parameters again until `params_dirty` is cleared

## Handshaking Protocol

**Flag: `params_dirty` (in DTCMRAM)**
- Bit 0: dirty (host has written parameters, needs recompute)
- Bit 1: ready (background task has new coefficients, waiting for ISR to apply)

**Sequence:**
```
Host:       Write param_value → Set params_dirty bit 0
            (param_walker/app loop)

Background: Poll params_dirty bit 0
            If set: compute coefficients → Update eq_new_ch → Set bit 1
            
ISR:        Check bit 1
            If set: swap eq_ch ← eq_new_ch
                   Clear both bits 0 & 1
                   (now safe for host to write again)
```

**Why two separate flags?**
- Bit 0 tells background task: "recompute, user changed something"
- Bit 1 tells ISR: "new coefficients are ready, please apply them"
- Prevents race: background task can't start if ISR is mid-swap

## Files to Modify

### eq.c / eq.h
- Add `EqChannel eq_new_ch[2]` (staging buffer for new coefficients)
- Keep `eq_process_biquad()` in ISR (fast path, no changes)
- Move coefficient computation to background task (new function: `eq_recompute_from_params()`)
- Add `eq_apply_new_coefficients()` called from ISR when ready

### params.h / params.c
- Add `params_dirty` flag in DTCMRAM (next to param_anchor)
- Bit 0: host has written (needs recompute)
- Bit 1: background has new coefficients (needs apply)

### audio.c
- In `process_audio()`: check `params_dirty` bit 1
- If set: call `eq_apply_new_coefficients()` and clear bits
- Remove `eq_update_from_params()` call

### main.c
- Add foreground loop (after DMA startup, replace bare spinloop)
- Poll `params_dirty` bit 0
- If set: call `eq_recompute_from_params()`, set bit 1

### param_walker.py (host)
- Add `write_param()` function
- After write: set `params_dirty` bit 0 via OpenOCD
- Wait for bit to clear (host feedback that DSP applied the change)

## Testing Strategy

1. **Unit test:** `eq_recompute_from_params()` computes coefficients correctly
2. **Integration test:** Write parameter, watch flag transitions: bit 0 → bit 1 → clear
3. **Audio test:** Adjust EQ via param_walker.py, verify audio changes in real-time without clicks/dropouts

## Backward Compatibility

None needed — this is still Stage 1a (single-channel EQ proof-of-concept). When we expand to multichannel, this pattern scales cleanly.

## References

- RM0433: STM32H7 reference manual (memory, interrupts, synchronization primitives if we add them)
- Audio EQ Cookbook: Biquad coefficient formulas (already implemented correctly)
