// ContentView.swift — Root view: connection bar, L/R tab pages, log.

import SwiftUI

struct ContentView: View {
  @State private var model = EQModel()

  var body: some View {
    VStack(spacing: 0) {
      ConnectionBar(model: model)
      Divider()

      TabView {
        ChannelPageView(model: model, channel: 0)
          .tabItem { Label("Left", systemImage: "l.circle") }
        ChannelPageView(model: model, channel: 1)
          .tabItem { Label("Right", systemImage: "r.circle") }
      }
      .frame(maxWidth: .infinity, maxHeight: .infinity)

      Divider()
      LogView(entries: model.log)
        .frame(height: 90)
    }
    .frame(minWidth: 820, minHeight: 580)
    .onReceive(NotificationCenter.default.publisher(
      for: NSApplication.willTerminateNotification)) { _ in
      model.disconnect()
    }
  }
}
