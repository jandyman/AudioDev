//
//  ContentView.swift
//  GainControl
//
//  Main UI for gain control
//

import SwiftUI

struct ContentView: View {
  @StateObject private var oscController = OSCController()
  @State private var gainValue: Double = 1.0
  @State private var isConnected: Bool = false

  var body: some View {
    VStack(spacing: 20) {
      // Header
      Text("andy.gain~ Remote Control")
        .font(.title)
        .fontWeight(.bold)

      // Connection status
      HStack {
        Circle()
          .fill(isConnected ? Color.green : Color.red)
          .frame(width: 12, height: 12)
        Text(isConnected ? "Connected to localhost:7400" : "Disconnected")
          .font(.caption)
          .foregroundColor(.secondary)
      }

      Divider()

      // Gain control
      VStack(spacing: 10) {
        Text("Gain")
          .font(.headline)

        // Gain value display
        Text(String(format: "%.2f", gainValue))
          .font(.system(size: 48, weight: .light, design: .monospaced))
          .foregroundColor(.primary)

        // Vertical slider
        VStack {
          Slider(
            value: $gainValue,
            in: 0.0...1.0,
            onEditingChanged: { editing in
              if !editing {
                // Send OSC message when slider is released
                oscController.sendGain(gainValue)
              }
            }
          )
          .onChange(of: gainValue) { newValue in
            // Live updates while dragging
            oscController.sendGain(newValue)
          }

          // Min/Max labels
          HStack {
            Text("0.0")
              .font(.caption)
              .foregroundColor(.secondary)
            Spacer()
            Text("1.0")
              .font(.caption)
              .foregroundColor(.secondary)
          }
        }
        .frame(width: 300)
      }

      Divider()

      // Preset buttons
      VStack(spacing: 10) {
        Text("Presets")
          .font(.headline)

        HStack(spacing: 15) {
          Button("Mute") {
            gainValue = 0.0
            oscController.sendGain(0.0)
          }
          .buttonStyle(.bordered)

          Button("Quiet") {
            gainValue = 0.25
            oscController.sendGain(0.25)
          }
          .buttonStyle(.bordered)

          Button("Half") {
            gainValue = 0.5
            oscController.sendGain(0.5)
          }
          .buttonStyle(.bordered)

          Button("Unity") {
            gainValue = 1.0
            oscController.sendGain(1.0)
          }
          .buttonStyle(.borderedProminent)
        }
      }

      Divider()

      // Info
      VStack(alignment: .leading, spacing: 5) {
        Text("Instructions:")
          .font(.caption)
          .fontWeight(.semibold)
        Text("1. Open andy.gain_osc.maxpat in Max")
          .font(.caption)
        Text("2. Lock patcher (Cmd+E) and enable audio")
          .font(.caption)
        Text("3. Move slider to control gain")
          .font(.caption)
      }
      .frame(maxWidth: .infinity, alignment: .leading)
      .padding()
      .background(Color.secondary.opacity(0.1))
      .cornerRadius(8)
    }
    .padding(30)
    .frame(width: 400)
    .onAppear {
      // Test connection
      isConnected = oscController.testConnection()
    }
  }
}

#Preview {
  ContentView()
}
