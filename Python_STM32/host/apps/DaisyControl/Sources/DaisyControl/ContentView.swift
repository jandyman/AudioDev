// ContentView.swift — root view: connection bar, two channel strips, log.

import SwiftUI

struct ContentView: View {
  @State private var model = EQModel()

  var body: some View {
    VStack(spacing: 0) {
      ConnectionBar(model: model)
      Divider()
      HStack(alignment: .top, spacing: 0) {
        ChannelView(model: model, channel: 0, label: "Left")
          .frame(maxWidth: .infinity)
        Divider()
        ChannelView(model: model, channel: 1, label: "Right")
          .frame(maxWidth: .infinity)
      }
      Divider()
      LogView(entries: model.log)
        .frame(height: 110)
    }
    .frame(minWidth: 700, minHeight: 400)
    .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
      model.disconnect()
    }
  }
}
