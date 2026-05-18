// ChannelPageView.swift — Full EQ page for one channel.
// Layout: frequency response plot (top) + five filter strips (bottom).

import SwiftUI

struct ChannelPageView: View {
  let model: EQModel
  let channel: Int   // 0 = left, 1 = right

  private var stages: [FilterStage] { model.stages[channel] }

  var body: some View {
    VStack(spacing: 0) {

      FreqResponseView(stages: stages)
        .frame(height: 220)
        .padding(.horizontal, 12)
        .padding(.top, 10)

      Divider()
        .padding(.vertical, 6)

      VStack(spacing: 0) {
        ForEach(stages.indices, id: \.self) { i in
          FilterStripView(stage: stages[i]) {
            model.stageChanged(channel: channel, filter: i)
          }
          if i < stages.count - 1 {
            Divider().padding(.horizontal, 12)
          }
        }
      }

      Spacer(minLength: 8)
    }
    .disabled(!model.isConnected)
  }
}
