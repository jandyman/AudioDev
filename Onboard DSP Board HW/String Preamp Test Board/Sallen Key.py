"""Equal-component Sallen-Key low-pass synthesis — pickup-resonance simulator.

Topology (one op-amp, non-inverting):

  In --[Rtop]--+--[Rfilt]--+---(+)\
               |           |       >-- Out
             [Rbot]      [Cshunt]  |
               |           |    (-)/
             BIAS        BIAS   |  |
                                |  +--[Rb]--+-- Out
  Cfb from the Rtop/Rfilt node -+--[Ra]--BIAS
  across to Out

Rtop/Rbot form an input attenuator whose Thevenin resistance IS the first
filter resistor, so folding it in costs one extra part and leaves f0 and Q
untouched. Both shunt legs return to the biased mid-rail node, not ground.

In the equal-component form (Rfilt = Rtop||Rbot, Cfb = Cshunt) the stage gain
is pinned by Q:  K = 3 - 1/Q,  Q = 1/(3 - K),  f0 = 1/(2*pi*R*C).
The attenuator exists solely to undo that gain. Consequences worth keeping in
mind: overall gain can never exceed K, and dQ/Q = K*Q * dK/K, so at Q = 2 a 1%
error in the Ra/Rb pair is a 5% error in Q.

Three different frequencies get called "cutoff" — they are reported separately:
  f0        natural frequency, what the component math solves for
  f_peak    resonant peak, f0*sqrt(1 - 1/(2Q^2))
  f_-3dB    where the response falls 3 dB below the passband, f0*1.485 at Q = 2

Parameters live at the bottom of the file; run from PyCharm as-is.
"""

import math
import random

# ------------------------------------------------------------ value series

# Standard IEC 60063 decade mantissas. E96/E48 are what a fab like JLCPCB
# stocks; a bench resistor kit is usually E24 or E12, so a design meant to be
# hand-stuffed from a kit has to survive the coarser grid. Use compare_series()
# to see what each one costs before committing.
_E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
        3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
_E96 = [
  1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
  1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
  1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
  2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
  3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
  4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
  5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
  7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76,
]
SERIES = {
  "E96": _E96,
  "E48": _E96[::2],
  "E24": _E24,
  "E12": _E24[::2],
  "E6":  _E24[::4],
  "E3":  _E24[::8],
}

def series_values(name: str) -> list:
  if name not in SERIES:
    raise ValueError(f"unknown series {name!r}; pick one of {', '.join(SERIES)}")
  return SERIES[name]

def snap(v: float, series: str = "E96") -> float:
  """Nearest value in the series, nearest in ratio rather than linear distance."""
  if v <= 0 or math.isinf(v): return v
  b = series_values(series)
  dec = math.floor(math.log10(v)); m = v / 10 ** dec
  if m >= math.sqrt(b[-1] * 10): return 10.0 ** (dec + 1)
  return min(b, key=lambda x: abs(math.log(x / m))) * 10 ** dec

def nearest_n(ideal: float, series: str, n: int = 24) -> list:
  """The n series values closest to `ideal` in ratio. Adapts the search window
  to how dense the series is: coarse series reach further to find a fit."""
  b = series_values(series)
  dec = math.floor(math.log10(ideal))
  cand = [m * 10 ** d for d in range(dec - 2, dec + 3) for m in b]
  return sorted(sorted(cand, key=lambda v: abs(math.log(v / ideal)))[:n])

# ------------------------------------------------- second-order descriptors

def stage_gain(q: float) -> float:
  """Non-inverting gain the equal-component form forces for a given Q."""
  return 3.0 - 1.0 / q

def peak_ratio(q: float) -> float:
  """f_peak / f0, or nan when Q <= 1/sqrt(2) and there is no peak."""
  return math.sqrt(1 - 1 / (2 * q * q)) if q > 0.70710678 else float("nan")

def peak_gain_db(q: float) -> float:
  """Height of the resonant peak above the passband, dB."""
  return 20 * math.log10(q / math.sqrt(1 - 1 / (4 * q * q))) if q > 0.70710678 else 0.0

def m3db_ratio(q: float) -> float:
  """f_-3dB / f0."""
  b = 2 - 1 / (q * q)
  return math.sqrt((b + math.sqrt(b * b + 4)) / 2)

def f0_from_target(fc: float, q: float, mode: str) -> float:
  """Convert a cutoff spec in the chosen sense into the natural frequency f0."""
  if mode == "f0": return fc
  if mode == "peak":
    r = peak_ratio(q)
    if math.isnan(r): raise ValueError(f"Q = {q} has no resonant peak; use mode 'f0' or 'minus3db'.")
    return fc / r
  if mode == "minus3db": return fc / m3db_ratio(q)
  raise ValueError(f"unknown mode {mode!r}; use 'f0', 'peak' or 'minus3db'.")

# ------------------------------------------------------- exact network solve

def analyze(r_top: float, r_bot: float, r_filt: float, c_fb: float,
            c_shunt: float, ra: float, rb: float) -> dict:
  """Exact f0, Q and passband gain of the drawn network, from real part values.

  r_bot may be inf, meaning no attenuator (the top leg is then the plain
  filter resistor). Derived from the Sallen-Key denominator
  1 + s[C2(R1+R2) + R1*C1*(1-K)] + s^2*R1*R2*C1*C2 with R1 = Rtop||Rbot.
  """
  r1 = r_top if math.isinf(r_bot) else r_top * r_bot / (r_top + r_bot)
  atten = 1.0 if math.isinf(r_bot) else r_bot / (r_top + r_bot)
  k = 1.0 + rb / ra
  w0 = 1.0 / math.sqrt(r1 * r_filt * c_fb * c_shunt)
  inv_q = w0 * (c_shunt * (r1 + r_filt) + r1 * c_fb * (1 - k))
  # inv_q <= 0 is the stability edge: the stage oscillates rather than peaks.
  # A coarse value grid lands there easily, so report it instead of dividing.
  q = float("inf") if inv_q == 0 else 1.0 / inv_q
  return {"f0": w0 / (2 * math.pi), "q": q, "gain": atten * k,
          "k": k, "atten": atten, "r_th": r1}

# ------------------------------------------------------------------ synthesis

def _pick_gain_pair(k: float, ra_hint: float, series: str) -> tuple:
  """Pair from the series whose 1 + Rb/Ra lands closest to k, preferring Ra
  near ra_hint. Searched jointly — on a coarse grid the best ratio often does
  not come from the value nearest ra_hint."""
  best = None
  for ra in nearest_n(ra_hint, series, 40):
    for rb in nearest_n(ra * (k - 1), series, 40):
      err = abs((1 + rb / ra) - k) / k
      score = err + 1e-4 * abs(math.log(ra / ra_hint))
      if best is None or score < best[0]: best = (score, ra, rb)
  return best[1], best[2]

def design(fc: float, q: float, c: float = 5.6e-9, gain: float = 1.0,
           mode: str = "f0", ra_hint: float = 10e3, series: str = "E96",
           weights: tuple = (1.0, 1.0, 1.0)) -> dict:
  """Synthesise the filter. fc is interpreted per `mode`; gain is the overall
  passband gain including the input attenuator (1.0 = unity). `weights` is the
  relative importance of (f0, Q, gain) when the value grid forces a trade —
  it only bites on a coarse series, where the three cannot all be hit."""
  if q < 0.5:
    raise ValueError(f"Q = {q} is below 0.5; the equal-component form cannot go there "
                     "(it would need stage gain below unity). Use a divergent-cap design.")
  k_ideal = stage_gain(q)
  if gain > k_ideal * 1.0000001:
    raise ValueError(f"Overall gain {gain} exceeds the stage gain {k_ideal:.4f} that Q = {q} "
                     "forces. The attenuator can only reduce gain — lower `gain`, raise Q, "
                     "or add a second stage.")
  f0 = f0_from_target(fc, q, mode)
  ra, rb = _pick_gain_pair(k_ideal, ra_hint, series)
  k = 1 + rb / ra                     # actual stage gain after snapping
  alpha = gain / k                    # attenuation the divider must supply
  r_ideal = 1.0 / (2 * math.pi * f0 * c)
  top_ideal = r_ideal / alpha
  bot_ideal = float("inf") if alpha >= 0.9999999 else r_ideal / (1 - alpha)

  # Snapping Rtop and Rbot moves both the Thevenin resistance and the
  # attenuation, so search E96 pairs against the exact solve rather than
  # rounding each leg on its own.
  def cost(cand: dict) -> float:
    # A candidate can land past the stability edge (1/Q <= 0); reject rather
    # than let the log blow up.
    if cand["q"] <= 0 or cand["f0"] <= 0 or math.isinf(cand["q"]): return float("inf")
    wf, wq, wg = weights
    g = wg * abs(math.log(cand["gain"] / gain)) if gain > 0 else 0.0
    return wf * abs(math.log(cand["f0"] / f0)) + wq * abs(math.log(cand["q"] / q)) + g

  best = None
  for r_filt in nearest_n(r_ideal, series):
    if math.isinf(bot_ideal):
      for r_top in nearest_n(top_ideal, series):
        cand = analyze(r_top, float("inf"), r_filt, c, c, ra, rb)
        cand.update(r_top=r_top, r_bot=float("inf"), r_filt=r_filt)
        if best is None or cost(cand) < cost(best): best = cand
      continue
    for r_top in nearest_n(top_ideal, series):
      for r_bot in nearest_n(bot_ideal, series):
        cand = analyze(r_top, r_bot, r_filt, c, c, ra, rb)
        cand.update(r_top=r_top, r_bot=r_bot, r_filt=r_filt)
        if best is None or cost(cand) < cost(best): best = cand

  best.update(c=c, ra=ra, rb=rb, f0_target=f0, q_target=q, gain_target=gain,
              fc_target=fc, mode=mode, series=series,
              ideal={"r": r_ideal, "r_top": top_ideal, "r_bot": bot_ideal,
                     "k": k_ideal, "alpha": alpha})
  return best

# ------------------------------------------------------------- noise, spread

def resistor_noise(d: dict, temp_c: float = 25.0) -> float:
  """Input-referred passband noise density from the filter resistors alone,
  V/sqrt(Hz). Op-amp and dielectric contributions are NOT included."""
  kt4 = 4 * 1.380649e-23 * (temp_c + 273.15)
  r_gain = d["ra"] * d["rb"] / (d["ra"] + d["rb"])
  e_out = d["k"] * math.sqrt(kt4 * (d["r_th"] + d["r_filt"] + r_gain))
  return e_out / d["gain"]

def monte_carlo(d: dict, r_tol: float = 0.01, c_tol: float = 0.05,
                trials: int = 20000, seed: int = 1) -> dict:
  """Spread of f0, Q and gain over part tolerances. Uniform within tolerance,
  which is the pessimistic assumption for reeled parts."""
  rng = random.Random(seed)
  j = lambda v, t: v * (1 + rng.uniform(-t, t))
  f0s, qs, gs = [], [], []
  for _ in range(trials):
    a = analyze(j(d["r_top"], r_tol),
                d["r_bot"] if math.isinf(d["r_bot"]) else j(d["r_bot"], r_tol),
                j(d["r_filt"], r_tol), j(d["c"], c_tol), j(d["c"], c_tol),
                j(d["ra"], r_tol), j(d["rb"], r_tol))
    f0s.append(a["f0"]); qs.append(a["q"]); gs.append(a["gain"])
  pct = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p / 100 * len(xs)))]
  return {n: {"p2.5": pct(v, 2.5), "p50": pct(v, 50), "p97.5": pct(v, 97.5)}
          for n, v in (("f0", f0s), ("q", qs), ("gain", gs))}

def compare_series(fc: float, q: float, c: float = 5.6e-9, gain: float = 1.0,
                   mode: str = "f0", ra_hint: float = 10e3,
                   which: tuple = ("E96", "E48", "E24", "E12", "E6"),
                   weights: tuple = (1.0, 1.0, 1.0)) -> None:
  """Same target synthesised on each value series, so the cost of a coarse
  bench kit is visible before ordering one. Errors are of the realised
  response, not of any single resistor — the search trades the three resistors
  against each other, so a 10%-spaced grid does not cost 10% of accuracy."""
  print(f"\nSame target on each series  (fc = {fc:.6g} Hz as '{mode}', Q = {q:.4g}, "
        f"gain {gain:.4g}, C = {c * 1e9:.4g} nF)")
  print(f"  {'series':<7} {'top':>9} {'bottom':>9} {'filter':>9} {'Rb/Ra':>15}"
        f" {'f0 err':>8} {'Q err':>8} {'gain err':>9}")
  for name in which:
    try: d = design(fc, q, c=c, gain=gain, mode=mode, ra_hint=ra_hint, series=name,
                    weights=weights)
    except ValueError as e: print(f"  {name:<7} {e}"); continue
    ef = (d["f0"] / d["f0_target"] - 1) * 100
    eq = (d["q"] / d["q_target"] - 1) * 100
    eg = (d["gain"] / d["gain_target"] - 1) * 100
    print(f"  {name:<7} {ohms(d['r_top']):>9} {ohms(d['r_bot']):>9} {ohms(d['r_filt']):>9}"
          f" {ohms(d['rb']) + '/' + ohms(d['ra']):>15}"
          f" {ef:>+7.2f}% {eq:>+7.2f}% {eg:>+8.2f}%")
  print("  A parallel pair of kit values is the escape hatch if one column is")
  print("  the only thing missing the target.")

# ---------------------------------------------------------------- reporting

def ohms(v: float) -> str:
  if math.isinf(v): return "open (no divider)"
  if v >= 1e6: return f"{v / 1e6:.4g} MΩ"
  if v >= 1e3: return f"{v / 1e3:.4g} kΩ"
  return f"{v:.4g} Ω"

def report(d: dict, mc: dict = None, temp_c: float = 25.0) -> None:
  q, f0 = d["q"], d["f0"]
  print("=" * 68)
  print(f"  Target   {d['fc_target']:.6g} Hz as '{d['mode']}', Q = {d['q_target']:.4g}, "
        f"overall gain {d['gain_target']:.4g} ({20 * math.log10(d['gain_target']):+.2f} dB)")
  print(f"  f0 this implies : {d['f0_target']:.2f} Hz")
  print(f"  Stage gain forced by Q : {d['ideal']['k']:.4f}  "
        f"-> attenuator must supply {d['ideal']['alpha']:.4f}")
  print("=" * 68)
  print("\nIdeal values")
  print(f"  filter resistance (Rtop||Rbot = Rfilt) : {ohms(d['ideal']['r'])}")
  print(f"  divider top leg  : {ohms(d['ideal']['r_top'])}")
  print(f"  divider bottom leg : {ohms(d['ideal']['r_bot'])}")

  print(f"\n{d['series']} values to build")
  print(f"  divider top leg    : {ohms(d['r_top'])}")
  print(f"  divider bottom leg : {ohms(d['r_bot'])}      (returns to mid-rail bias)")
  print(f"  filter resistor    : {ohms(d['r_filt'])}")
  print(f"  both capacitors    : {d['c'] * 1e9:.4g} nF")
  print(f"  Q network          : {ohms(d['rb'])} feedback / {ohms(d['ra'])} to bias  "
        f"-> K = {d['k']:.4f}")
  print(f"  Thevenin of divider: {ohms(d['r_th'])}  (should equal the filter resistor)")

  print("\nRealised response")
  print(f"  f0        : {f0:.2f} Hz   ({(f0 / d['f0_target'] - 1) * 100:+.2f}%)")
  print(f"  Q         : {q:.4f}     ({(q / d['q_target'] - 1) * 100:+.2f}%)")
  print(f"  passband  : {20 * math.log10(d['gain']):+.3f} dB")
  if q > 0.70710678:
    print(f"  peak      : {f0 * peak_ratio(q):.2f} Hz at {peak_gain_db(q):+.2f} dB "
          f"rel passband ({peak_gain_db(q) + 20 * math.log10(d['gain']):+.2f} dB rel input)")
  else:
    print("  peak      : none (Q <= 0.707)")
  print(f"  -3 dB     : {f0 * m3db_ratio(q):.2f} Hz  ({m3db_ratio(q):.3f} x f0)")
  print(f"  noise     : {resistor_noise(d, temp_c) * 1e9:.1f} nV/sqrt(Hz) input-referred, "
        "resistors only")

  print("\nSensitivity")
  print(f"  Q to the Ra/Rb ratio : {d['k'] * q:.2f}x  "
        f"(1% ratio error -> {d['k'] * q:.1f}% Q error)")
  print("  f0 to capacitance    : 1.0x  — cap tolerance dominates f0, not the snap")
  print("  Q to capacitance     : 0x    — matched caps cancel; Q is resistor-only")

  if mc:
    print("\nTolerance spread (95% of builds)")
    for n, lbl, sc in (("f0", "f0   ", 1), ("q", "Q    ", 1), ("gain", "gain ", 1)):
      v = mc[n]
      print(f"  {lbl}: {v['p2.5'] * sc:9.4f} .. {v['p97.5'] * sc:9.4f}   "
            f"(median {v['p50'] * sc:.4f})")

def plot(d: dict, decades: float = 2.5) -> None:
  """Magnitude response with f0, peak and -3 dB marked. Needs matplotlib."""
  import matplotlib.pyplot as plt
  f0, q, g = d["f0"], d["q"], d["gain"]
  fs = [f0 * 10 ** (e / 400 * decades * 2 - decades) for e in range(401)]
  mag = []
  for f in fs:
    x = f / f0
    mag.append(20 * math.log10(g / math.sqrt((1 - x * x) ** 2 + (x / q) ** 2)))
  fig, ax = plt.subplots(figsize=(8, 4.5))
  ax.semilogx(fs, mag, lw=2)
  ax.axvline(f0, ls=":", c="0.5"); ax.axhline(20 * math.log10(g), ls=":", c="0.5")
  if q > 0.70710678:
    fp = f0 * peak_ratio(q)
    ax.plot([fp], [peak_gain_db(q) + 20 * math.log10(g)], "o", c="C3")
    ax.annotate(f"{fp:.0f} Hz\n{peak_gain_db(q):+.1f} dB", (fp, peak_gain_db(q) + 20 * math.log10(g)),
                textcoords="offset points", xytext=(8, 6), color="C3")
  f3 = f0 * m3db_ratio(q)
  ax.plot([f3], [20 * math.log10(g) - 3], "s", c="C2")
  ax.annotate(f"-3 dB\n{f3:.0f} Hz", (f3, 20 * math.log10(g) - 3),
              textcoords="offset points", xytext=(8, -22), color="C2")
  ax.set_xlabel("Hz"); ax.set_ylabel("dB"); ax.grid(True, which="both", alpha=0.3)
  ax.set_title(f"Equal-component Sallen-Key — f0 {f0:.0f} Hz, Q {q:.2f}")
  fig.tight_layout(); plt.show()

# ------------------------------------------------------------------ run me

if __name__ == "__main__":
  FC          = 1941.0    # cutoff target, interpreted per MODE
  Q           = 2.0       # resonant Q (equal-component form needs Q >= 0.5)
  MODE        = "f0"      # "f0" | "peak" | "minus3db"
  C           = 5.6e-9    # both capacitors, matched
  GAIN        = 1.0       # overall passband gain, V/V (1.0 = unity)
  RA_HINT     = 10e3      # preferred scale for the Q-setting network
  SERIES_USED = "E96"     # "E96" | "E48" | "E24" | "E12" | "E6" | "E3"
  WEIGHTS     = (1., 1., 1.)  # relative importance of (f0, Q, gain) on a coarse grid
  COMPARE     = True      # also print the same target on every series

  R_TOL       = 0.01      # resistor tolerance for the Monte Carlo
  C_TOL       = 0.05      # capacitor tolerance
  TRIALS      = 20000
  TEMP_C      = 25.0
  DO_PLOT     = True

  d = design(FC, Q, c=C, gain=GAIN, mode=MODE, ra_hint=RA_HINT, series=SERIES_USED,
             weights=WEIGHTS)
  report(d, monte_carlo(d, R_TOL, C_TOL, TRIALS), TEMP_C)
  if COMPARE: compare_series(FC, Q, c=C, gain=GAIN, mode=MODE, ra_hint=RA_HINT,
                             weights=WEIGHTS)
  if DO_PLOT: plot(d)
