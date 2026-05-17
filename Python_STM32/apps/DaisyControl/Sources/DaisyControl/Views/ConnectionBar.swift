// ConnectionBar.swift — status indicator, connect/disconnect, ping.

import SwiftUI

struct ConnectionBar: View {
  var model: EQModel

  var body: some View {
    HStack(spacing: 10) {
      Circle()
        .fill(statusColor)
        .frame(width: 9, height: 9)

      Text(statusLabel)
        .foregroundStyle(.secondary)
        .animation(nil, value: model.connectionState)

      Spacer()

      Button("Ping") {
        Task { await model.ping() }
      }
      .disabled(!model.isConnected)

      Button(model.isConnected ? "Disconnect" : "Connect") {
        Task {
          if model.isConnected {
            model.disconnect()
          } else {
            await model.connect()
          }
        }
      }
      .keyboardShortcut("k", modifiers: .command)
    }
    .padding(.horizontal)
    .padding(.vertical, 8)
  }

  private var statusColor: Color {
    switch model.connectionState {
    case .connected:    .green
    case .connecting:   .yellow
    case .disconnected: .secondary
    case .failed:       .red
    }
  }

  private var statusLabel: String {
    switch model.connectionState {
    case .connected:         "Connected to JLinkGDBServer :19021"
    case .connecting:        "Connecting..."
    case .disconnected:      "Disconnected"
    case .failed(let msg):   "Error: \(msg)"
    }
  }
}
