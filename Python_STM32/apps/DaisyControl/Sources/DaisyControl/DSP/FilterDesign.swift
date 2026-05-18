// FilterDesign.swift — Swift port of eq_design.cpp.
//
// Computes biquad cascade coefficients from FilterStage parameters, then
// evaluates the combined transfer function magnitude for frequency response
// display. Uses Double precision (computation only — not sent to firmware).
//
// Coefficient convention: a1/a2 stored negated, matching the C++ convention
// in eq_design.cpp and biquad.h. The transfer function at z = e^jω is:
//   H(z) = (b0 + b1·z⁻¹ + b2·z⁻²) / (1 − a1·z⁻¹ − a2·z⁻²)

import Foundation

// MARK: - Types

struct BiquadCoeffsD {
  var b0, b1, b2: Double
  var a1, a2: Double  // stored negated
}

// MARK: - Private helpers

private let kPi = Double.pi

// Butterworth Q for the k-th second-order section of an N-th order filter.
private func bwQ(_ k: Int, _ n: Int) -> Double {
  1.0 / (2.0 * sin(kPi * Double(2*k - 1) / Double(2*n)))
}

// ---- First-order sections --------------------------------------------------

private func lp1(_ K: Double) -> BiquadCoeffsD {
  let inv = 1 / (1 + K)
  return BiquadCoeffsD(b0: K*inv, b1: K*inv, b2: 0, a1: (1-K)*inv, a2: 0)
}

private func hp1(_ K: Double) -> BiquadCoeffsD {
  let inv = 1 / (1 + K)
  return BiquadCoeffsD(b0: inv, b1: -inv, b2: 0, a1: (1-K)*inv, a2: 0)
}

private func loshelf1(_ K: Double, _ A: Double) -> BiquadCoeffsD {
  let inv = 1 / (1 + K)
  return BiquadCoeffsD(b0: (1+A*K)*inv, b1: (A*K-1)*inv, b2: 0, a1: (1-K)*inv, a2: 0)
}

private func hishelf1(_ K: Double, _ A: Double) -> BiquadCoeffsD {
  let inv = 1 / (1 + K)
  return BiquadCoeffsD(b0: (A+K)*inv, b1: (K-A)*inv, b2: 0, a1: (1-K)*inv, a2: 0)
}

// ---- Second-order sections -------------------------------------------------

private func lp2(_ K: Double, _ Q: Double) -> BiquadCoeffsD {
  let norm = 1 + K/Q + K*K, inv = 1/norm
  return BiquadCoeffsD(b0: K*K*inv, b1: 2*K*K*inv, b2: K*K*inv,
                       a1: -(2*(K*K-1))*inv, a2: -(1-K/Q+K*K)*inv)
}

private func hp2(_ K: Double, _ Q: Double) -> BiquadCoeffsD {
  let norm = 1 + K/Q + K*K, inv = 1/norm
  return BiquadCoeffsD(b0: inv, b1: -2*inv, b2: inv,
                       a1: -(2*(K*K-1))*inv, a2: -(1-K/Q+K*K)*inv)
}

// Cookbook lo-shelf with caller-supplied alpha = sin(w0)/(2·Q).
private func loshelf2(_ w0: Double, _ A: Double, _ alpha: Double) -> BiquadCoeffsD {
  let cw = cos(w0), sqA = sqrt(A)
  let Am1 = A-1, Ap1 = A+1, tsa = 2*sqA*alpha
  let b0    =   A * (Ap1 - Am1*cw + tsa)
  let b1    = 2*A * (Am1 - Ap1*cw)
  let b2    =   A * (Ap1 - Am1*cw - tsa)
  let a0    =         Ap1 + Am1*cw + tsa
  let a1ck  =  -2  * (Am1 + Ap1*cw)
  let a2ck  =         Ap1 + Am1*cw - tsa
  return BiquadCoeffsD(b0: b0/a0, b1: b1/a0, b2: b2/a0,
                       a1: -a1ck/a0, a2: -a2ck/a0)
}

private func hishelf2(_ w0: Double, _ A: Double, _ alpha: Double) -> BiquadCoeffsD {
  let cw = cos(w0), sqA = sqrt(A)
  let Am1 = A-1, Ap1 = A+1, tsa = 2*sqA*alpha
  let b0    =    A * (Ap1 + Am1*cw + tsa)
  let b1    = -2*A * (Am1 + Ap1*cw)
  let b2    =    A * (Ap1 + Am1*cw - tsa)
  let a0    =          Ap1 - Am1*cw + tsa
  let a1ck  =   2  * (Am1 - Ap1*cw)
  let a2ck  =         Ap1 - Am1*cw - tsa
  return BiquadCoeffsD(b0: b0/a0, b1: b1/a0, b2: b2/a0,
                       a1: -a1ck/a0, a2: -a2ck/a0)
}

// MARK: - Public API

/// Compute biquad sections for one filter stage. Returns 1 or 2 sections.
func filterDesign(_ stage: FilterStage, fs: Double = 48000) -> [BiquadCoeffsD] {
  let fc   = max(10, min(Double(stage.fc), fs * 0.499))
  let K    = tan(kPi * fc / fs)
  let w0   = 2 * kPi * fc / fs
  let N    = stage.type.hasOrder ? stage.order : 2
  let n1   = N & 1        // 1 if odd order — first-order section needed
  let n2   = N / 2        // number of second-order sections

  var s: [BiquadCoeffsD] = []

  switch stage.type {

  case .lp:
    if n1 == 1 { s.append(lp1(K)) }
    if n2 > 0  { for k in 1...n2 { s.append(lp2(K, bwQ(k, N))) } }

  case .hp:
    if n1 == 1 { s.append(hp1(K)) }
    if n2 > 0  { for k in 1...n2 { s.append(hp2(K, bwQ(k, N))) } }

  case .ls:
    let g = Double(stage.gainDb)
    if n1 == 1 {
      s.append(loshelf1(K, pow(10, g / Double(N) * 0.025)))
    }
    if n2 > 0 {
      for k in 1...n2 {
        let A     = pow(10, g * 2.0 / Double(N) * 0.025)
        let alpha = sin(w0) / (2 * bwQ(k, N))
        s.append(loshelf2(w0, A, alpha))
      }
    }

  case .hs:
    let g = Double(stage.gainDb)
    if n1 == 1 {
      s.append(hishelf1(K, pow(10, g / Double(N) * 0.025)))
    }
    if n2 > 0 {
      for k in 1...n2 {
        let A     = pow(10, g * 2.0 / Double(N) * 0.025)
        let alpha = sin(w0) / (2 * bwQ(k, N))
        s.append(hishelf2(w0, A, alpha))
      }
    }

  case .bp:
    let A     = pow(10, Double(stage.gainDb) * 0.025)
    let sw0   = sin(w0), cw0 = cos(w0)
    let alpha = sw0 / (2 * max(0.01, Double(stage.q)))
    let a0    = 1 + alpha / A
    let inv   = 1 / a0
    s.append(BiquadCoeffsD(
      b0:  (1 + alpha * A) * inv,
      b1:  (-2 * cw0)      * inv,
      b2:  (1 - alpha * A) * inv,
      a1:  (2 * cw0)       * inv,
      a2: -(1 - alpha / A) * inv
    ))
  }

  return s
}

/// Combined magnitude in dB at `freqHz` for a channel's filter stages.
/// Disabled stages contribute 0 dB (unity gain).
func combinedMagnitudeDb(stages: [FilterStage], freqHz: Double,
                         fs: Double = 48000) -> Double {
  var hRe = 1.0, hIm = 0.0

  for stage in stages where stage.enabled {
    for c in filterDesign(stage, fs: fs) {
      let w   = 2 * kPi * freqHz / fs
      let cw  = cos(w),  sw  = sin(w)
      let c2w = cos(2*w), s2w = sin(2*w)

      // Numerator: b0 + b1·e^{-jω} + b2·e^{-2jω}
      let nRe =  c.b0 + c.b1*cw  + c.b2*c2w
      let nIm =        -c.b1*sw  - c.b2*s2w

      // Denominator: 1 − a1·e^{-jω} − a2·e^{-2jω}  (a1/a2 stored negated)
      let dRe = 1 - c.a1*cw  - c.a2*c2w
      let dIm =    c.a1*sw   + c.a2*s2w

      // Multiply running product H by (num/den)
      let dMag2 = dRe*dRe + dIm*dIm
      let rRe = (nRe*dRe + nIm*dIm) / dMag2
      let rIm = (nIm*dRe - nRe*dIm) / dMag2
      (hRe, hIm) = (hRe*rRe - hIm*rIm, hRe*rIm + hIm*rRe)
    }
  }

  return 20 * log10(max(sqrt(hRe*hRe + hIm*hIm), 1e-10))
}
