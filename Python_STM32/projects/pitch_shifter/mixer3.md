# Mixer3

A stateless three-input weighted summer:

```
out[n] = in1[n]*gain1[n] + in2[n]*gain2[n] + in3[n]*gain3[n]
```

Gains are per-sample inputs, so time-varying crossfades are handled correctly.
All tap-level muting (dead-note, attack response, loop crossfades) is owned by
`loop_controller` upstream — this block deliberately holds no state and applies
exactly the gains it is handed (no internal ramping or smoothing).
