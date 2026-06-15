# Triple-Tap Delay

A single shared delay buffer (300 ms max at 48 kHz) with three independent read
taps, each at its own fractional delay. Taps 1 and 2 are the ping-pong loop
pair; tap 3 is dedicated to the attack response. Reads use 4th-order Lagrange
interpolation so a tap delay can be modulated smoothly without zipper noise.

The three `delayN_ms` inputs (clamped to the buffer range) are driven by
`loop_controller`. Sharing one buffer across all taps is far more
memory-efficient than a buffer per tap — important for the STM32 target.
