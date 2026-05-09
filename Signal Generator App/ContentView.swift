import SwiftUI

struct ContentView: View {
    @StateObject private var engine = AudioEngine()
    @State private var sliderValue: Double = 0.5
    @State private var lowerLimit: Double = 10
    @State private var upperLimit: Double = 20000
    @State private var lowerText: String = "10"
    @State private var upperText: String = "20000"

    private var nyquist: Double { engine.selectedSampleRate / 2 }

    private var sliderBinding: Binding<Double> {
        Binding(
            get: { sliderValue },
            set: { v in
                sliderValue = v
                engine.frequency = sliderToFreq(v)
            }
        )
    }

    var body: some View {
        VStack(spacing: 16) {
            // Device + sample rate
            HStack {
                Picker("Device", selection: $engine.selectedDevice) {
                    Text("None").tag(Optional<AudioDevice>.none)
                    ForEach(engine.outputDevices) { d in
                        Text(d.name).tag(Optional(d))
                    }
                }
                .pickerStyle(.menu)
                .frame(maxWidth: .infinity)

                Picker("Sample Rate", selection: $engine.selectedSampleRate) {
                    ForEach(engine.availableSampleRates, id: \.self) { rate in
                        Text(formatSampleRate(rate)).tag(rate)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 120)
            }

            // Frequency limits
            HStack(spacing: 16) {
                HStack {
                    Text("Low:")
                    TextField("Hz", text: $lowerText)
                        .frame(width: 70)
                        .textFieldStyle(.squareBorder)
                        .onSubmit { applyLowerLimit() }
                    Text("Hz").foregroundColor(.secondary)
                }
                Spacer()
                HStack {
                    Text("High:")
                    TextField("Hz", text: $upperText)
                        .frame(width: 70)
                        .textFieldStyle(.squareBorder)
                        .onSubmit { applyUpperLimit() }
                    Text("Hz").foregroundColor(.secondary)
                }
            }

            Slider(value: sliderBinding, in: 0...1)

            Text(formatFrequency(engine.frequency))
                .font(.system(size: 52, weight: .light, design: .monospaced))
                .frame(maxWidth: .infinity)
                .multilineTextAlignment(.center)

            Button(engine.isPlaying ? "Stop" : "Play") {
                engine.togglePlay()
            }
            .keyboardShortcut(.space, modifiers: [])
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            Divider()
            ScopeView(frame: engine.currentScopeFrame)
        }
        .padding(24)
        .frame(minWidth: 420, minHeight: 560)
        .onAppear {
            engine.frequency = sliderToFreq(sliderValue)
        }
        .onChange(of: engine.selectedSampleRate) { _, _ in
            if upperLimit > nyquist {
                upperLimit = nyquist
                upperText = formatHz(nyquist)
            }
            sliderValue = freqToSlider(engine.frequency)
        }
    }

    // MARK: - Frequency mapping

    private func sliderToFreq(_ t: Double) -> Double {
        exp(log(lowerLimit) + t * (log(upperLimit) - log(lowerLimit)))
    }

    private func freqToSlider(_ f: Double) -> Double {
        let clamped = max(lowerLimit, min(upperLimit, f))
        return (log(clamped) - log(lowerLimit)) / (log(upperLimit) - log(lowerLimit))
    }

    // MARK: - Limit validation

    private func applyLowerLimit() {
        guard let value = Double(lowerText.trimmingCharacters(in: .whitespaces)),
              value >= 10, value < upperLimit else {
            lowerText = formatHz(lowerLimit)
            return
        }
        lowerLimit = value
        lowerText  = formatHz(value)
        sliderValue = freqToSlider(engine.frequency)
    }

    private func applyUpperLimit() {
        guard let value = Double(upperText.trimmingCharacters(in: .whitespaces)),
              value > lowerLimit, value <= nyquist else {
            upperText = formatHz(upperLimit)
            return
        }
        upperLimit = value
        upperText  = formatHz(value)
        sliderValue = freqToSlider(engine.frequency)
    }

    // MARK: - Formatters

    private func formatFrequency(_ f: Double) -> String {
        f >= 1000 ? String(format: "%.3f kHz", f / 1000) : String(format: "%.1f Hz", f)
    }

    private func formatHz(_ v: Double) -> String {
        v == v.rounded() ? String(Int(v.rounded())) : String(format: "%.1f", v)
    }

    private func formatSampleRate(_ rate: Double) -> String {
        String(format: "%g kHz", rate / 1000)
    }
}
