// ChannelView.swift — three param sliders for one EQ channel.

import SwiftUI

struct ChannelView: View {
  var model: EQModel
  let channel: Int   // 0 = left, 1 = right
  let label: String

  // Param IDs for this channel (matches ParamID enum layout: 0/1/2 = left, 3/4/5 = right)
  private var gainID:    Int { channel * 3 + 0 }
  private var shelfFcID: Int { channel * 3 + 1 }
  private var lpFcID:    Int { channel * 3 + 2 }

  var body: some View {
    VStack(alignment: .leading, spacing: 14) {
      Text(label)
        .font(.headline)

      ParamSlider(
        label: "Hi-Shelf Gain",
        value: Binding(get: { model.values[gainID] },
                       set: { model.setValue(gainID, $0) }),
        range: -24...24,
        scale: .linear,
        unit: "dB"
      )

      ParamSlider(
        label: "Hi-Shelf Fc",
        value: Binding(get: { model.values[shelfFcID] },
                       set: { model.setValue(shelfFcID, $0) }),
        range: 1000...20000,
        scale: .logarithmic,
        unit: "Hz"
      )

      ParamSlider(
        label: "LP Cutoff",
        value: Binding(get: { model.values[lpFcID] },
                       set: { model.setValue(lpFcID, $0) }),
        range: 20...20000,
        scale: .logarithmic,
        unit: "Hz"
      )
    }
    .padding()
    .disabled(!model.isConnected)
  }
}
