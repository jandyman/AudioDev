// FilterStripView.swift — Compact control row for one filter stage.

import SwiftUI

struct FilterStripView: View {
  let stage: FilterStage
  let onChanged: (ParamField) -> Void

  var body: some View {
    HStack(spacing: 8) {

      // Enable toggle
      Toggle("", isOn: Binding(get: { stage.enabled },
                               set: { stage.enabled = $0; onChanged(.enabled) }))
        .labelsHidden()
        .toggleStyle(.checkbox)
        .frame(width: 18)

      // Filter type label
      Text(stage.type.label)
        .frame(width: 72, alignment: .leading)
        .foregroundStyle(stage.enabled ? .primary : .secondary)

      // Fc slider (log scale) — binding setter calls onChanged(.fcHz), no .onChange needed
      HStack(spacing: 4) {
        Text("Fc")
          .frame(width: 18, alignment: .trailing)
          .foregroundStyle(.secondary)
          .font(.caption)
        Text(fcLabel)
          .frame(width: 68, alignment: .trailing)
          .monospacedDigit()
          .foregroundStyle(.secondary)
          .font(.caption)
        Slider(value: fcPositionBinding, in: 0...1)
      }

      // Order stepper (LP / HP / shelf only)
      if stage.type.hasOrder {
        HStack(spacing: 3) {
          Text("Ord")
            .font(.caption)
            .foregroundStyle(.secondary)
          Stepper("", value: Binding(
            get: { stage.order },
            set: { stage.order = $0; onChanged(.order) }
          ), in: 1...4)
          .labelsHidden()
          .frame(width: 36)
          Text("\(stage.order)")
            .frame(width: 12)
            .monospacedDigit()
            .font(.caption)
        }
        .frame(width: 90)
      } else {
        Spacer().frame(width: 90)
      }

      // Gain slider (shelf + peak)
      if stage.type.hasGain {
        HStack(spacing: 4) {
          Text("Gain")
            .frame(width: 30, alignment: .trailing)
            .foregroundStyle(.secondary)
            .font(.caption)
          Text(gainLabel)
            .frame(width: 58, alignment: .trailing)
            .monospacedDigit()
            .foregroundStyle(.secondary)
            .font(.caption)
          Slider(value: Binding(
            get: { Double(stage.gainDb) },
            set: { stage.gainDb = Float($0); onChanged(.gainDb) }
          ), in: -24...24)
          .frame(width: 100)
        }
      } else {
        Spacer().frame(width: 192)
      }

      // Q field (peak only)
      if stage.type.hasQ {
        HStack(spacing: 4) {
          Text("Q")
            .font(.caption)
            .foregroundStyle(.secondary)
          Slider(value: qPositionBinding, in: 0...1)
            .frame(width: 70)
          Text(String(format: "%.2f", stage.q))
            .frame(width: 38, alignment: .trailing)
            .monospacedDigit()
            .foregroundStyle(.secondary)
            .font(.caption)
        }
        .frame(width: 130)
      } else {
        Spacer().frame(width: 130)
      }
    }
    .padding(.horizontal, 12)
    .padding(.vertical, 5)
    .opacity(stage.enabled ? 1 : 0.5)
  }

  // MARK: - Fc log-scale position binding (20 Hz – 20 kHz)

  private let fcMin = 20.0, fcMax = 20000.0

  private var fcPositionBinding: Binding<Double> {
    Binding(
      get: { log10(Double(stage.fc) / fcMin) / log10(fcMax / fcMin) },
      set: { stage.fc = Float(fcMin * pow(fcMax / fcMin, $0)); onChanged(.fcHz) }
    )
  }

  private var fcLabel: String {
    Double(stage.fc) >= 1000
      ? String(format: "%.1f kHz", stage.fc / 1000)
      : String(format: "%.0f Hz", stage.fc)
  }

  // MARK: - Q log-scale position binding (0.1 – 10)

  private let qMin = 0.1, qMax = 10.0

  private var qPositionBinding: Binding<Double> {
    Binding(
      get: { log10(Double(stage.q) / qMin) / log10(qMax / qMin) },
      set: { stage.q = Float(qMin * pow(qMax / qMin, $0)); onChanged(.q) }
    )
  }

  // MARK: - Gain label

  private var gainLabel: String {
    String(format: "%+.1f dB", stage.gainDb)
  }
}
