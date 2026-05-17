// ParamSlider.swift — labeled slider supporting linear and logarithmic scales.

import SwiftUI

struct ParamSlider: View {
  enum Scale { case linear, logarithmic }

  let label: String
  @Binding var value: Float
  let range: ClosedRange<Float>
  let scale: Scale
  let unit: String

  var body: some View {
    HStack(spacing: 8) {
      Text(label)
        .frame(width: 108, alignment: .leading)
      Slider(value: positionBinding, in: 0...1)
      Text(formattedValue)
        .frame(width: 80, alignment: .trailing)
        .monospacedDigit()
        .foregroundStyle(.secondary)
    }
  }

  // MARK: Scale conversions

  private var positionBinding: Binding<Double> {
    Binding(
      get: { valueToPosition(Double(value)) },
      set: { value = Float(positionToValue($0)) }
    )
  }

  private func valueToPosition(_ v: Double) -> Double {
    let lo = Double(range.lowerBound)
    let hi = Double(range.upperBound)
    switch scale {
    case .linear:
      return (v - lo) / (hi - lo)
    case .logarithmic:
      return (log10(v) - log10(lo)) / (log10(hi) - log10(lo))
    }
  }

  private func positionToValue(_ t: Double) -> Double {
    let lo = Double(range.lowerBound)
    let hi = Double(range.upperBound)
    switch scale {
    case .linear:
      return lo + t * (hi - lo)
    case .logarithmic:
      return lo * pow(hi / lo, t)
    }
  }

  // MARK: Display formatting

  private var formattedValue: String {
    switch unit {
    case "dB":
      return String(format: "%+.1f dB", value)
    case "Hz":
      return value >= 1000
        ? String(format: "%.1f kHz", value / 1000)
        : String(format: "%.0f Hz", value)
    default:
      return "\(value) \(unit)"
    }
  }
}
