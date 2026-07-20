//
//  ContentView.swift
//  GainControl (iOS)
//
//  iPad remote control UI for andy.gain~
//

import SwiftUI

struct ContentView: View {
  @StateObject private var oscController = OSCController()
  @State private var gainValue: Double = 1.0
  @State private var showSettings: Bool = false

  var body: some View {
    NavigationView {
      VStack(spacing: 30) {
        // Header
        Text("andy.gain~")
          .font(.system(size: 48, weight: .bold, design: .rounded))

        // Target address display
        HStack(spacing: 10) {
          Image(systemName: "network")
            .foregroundColor(.secondary)
          Text("Target: \(oscController.host):7400")
            .font(.subheadline)
            .foregroundColor(.secondary)
        }

        Divider()
          .padding(.horizontal, 40)

        // Gain control
        VStack(spacing: 20) {
          Text("GAIN")
            .font(.headline)
            .foregroundColor(.secondary)

          // Large gain value display
          Text(String(format: "%.2f", gainValue))
            .font(.system(size: 80, weight: .ultraLight, design: .monospaced))
            .foregroundColor(.primary)

          // Vertical slider (large for touch)
          VStack {
            Slider(
              value: $gainValue,
              in: 0.0...1.0,
              onEditingChanged: { editing in
                if !editing {
                  oscController.sendGain(gainValue)
                }
              }
            )
            .onChange(of: gainValue) { newValue in
              // Live updates while dragging
              oscController.sendGain(newValue)
            }
            .accentColor(.blue)

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
          .padding(.horizontal, 40)
        }

        Divider()
          .padding(.horizontal, 40)

        // Preset buttons (larger for touch)
        VStack(spacing: 15) {
          Text("PRESETS")
            .font(.headline)
            .foregroundColor(.secondary)

          HStack(spacing: 15) {
            PresetButton(title: "Mute", value: 0.0) {
              gainValue = 0.0
              oscController.sendGain(0.0)
            }

            PresetButton(title: "Quiet", value: 0.25) {
              gainValue = 0.25
              oscController.sendGain(0.25)
            }

            PresetButton(title: "Half", value: 0.5) {
              gainValue = 0.5
              oscController.sendGain(0.5)
            }
          }

          HStack(spacing: 15) {
            PresetButton(title: "Unity", value: 1.0, isPrimary: true) {
              gainValue = 1.0
              oscController.sendGain(1.0)
            }
          }
        }

        Spacer()

        // Info footer
        VStack(spacing: 5) {
          Text("OSC Remote Control")
            .font(.caption2)
            .foregroundColor(.secondary)
          Text("Port 7400 • UDP")
            .font(.caption2)
            .foregroundColor(.secondary)
        }
        .padding(.bottom, 20)
      }
      .padding()
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Button {
            showSettings.toggle()
          } label: {
            Image(systemName: "gear")
          }
        }
      }
      .sheet(isPresented: $showSettings) {
        SettingsView(oscController: oscController)
      }
    }
  }
}

struct PresetButton: View {
  let title: String
  let value: Double
  var isPrimary: Bool = false
  let action: () -> Void

  var body: some View {
    Button(action: action) {
      VStack(spacing: 5) {
        Text(title)
          .font(.headline)
        Text(String(format: "%.2f", value))
          .font(.caption)
          .foregroundColor(.secondary)
      }
      .frame(maxWidth: .infinity)
      .padding(.vertical, 20)
      .background(isPrimary ? Color.blue : Color.secondary.opacity(0.2))
      .foregroundColor(isPrimary ? .white : .primary)
      .cornerRadius(12)
    }
  }
}

struct SettingsView: View {
  @ObservedObject var oscController: OSCController
  @Environment(\.dismiss) var dismiss
  @State private var editingIP: String = ""

  var body: some View {
    NavigationView {
      Form {
        Section(header: Text("Network")) {
          TextField("Mac IP Address", text: $editingIP)
            .keyboardType(.decimalPad)
            .autocapitalization(.none)

          Text("Port: 7400 (UDP)")
            .font(.caption)
            .foregroundColor(.secondary)
        }

        Section(header: Text("Instructions")) {
          Text("1. Find your Mac's IP address:")
            .font(.caption)
          Text("   System Preferences → Network")
            .font(.caption)
            .foregroundColor(.secondary)

          Text("2. Open andy.gain_osc.maxpat in Max")
            .font(.caption)

          Text("3. Make sure both devices are on the same WiFi network")
            .font(.caption)
        }

      }
      .navigationTitle("Settings")
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarLeading) {
          Button("Cancel") {
            dismiss()
          }
        }
        ToolbarItem(placement: .navigationBarTrailing) {
          Button("OK") {
            oscController.setHost(editingIP)
            dismiss()
          }
        }
      }
      .onAppear {
        editingIP = oscController.host
      }
    }
  }
}

#Preview {
  ContentView()
}
