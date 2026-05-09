import Foundation
import CoreAudio
import AVFoundation
import Accelerate
import Combine

struct AudioDevice: Identifiable, Hashable, Equatable {
    let id: AudioDeviceID
    let name: String

    func supportedSampleRates() -> [Double] {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyAvailableNominalSampleRates,
            mScope: kAudioObjectPropertyScopeOutput,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(id, &address, 0, nil, &dataSize) == noErr else { return [] }
        let count = Int(dataSize) / MemoryLayout<AudioValueRange>.size
        var ranges = [AudioValueRange](repeating: AudioValueRange(), count: count)
        guard AudioObjectGetPropertyData(id, &address, 0, nil, &dataSize, &ranges) == noErr else { return [] }
        let common: [Double] = [44100, 48000, 88200, 96000, 176400, 192000]
        var result: Set<Double> = []
        for range in ranges {
            for rate in common where rate >= range.mMinimum && rate <= range.mMaximum {
                result.insert(rate)
            }
        }
        return result.sorted()
    }
}

class AudioEngine: ObservableObject {
    @Published var outputDevices: [AudioDevice] = []
    @Published var selectedDevice: AudioDevice? { didSet { deviceChanged() } }
    @Published var availableSampleRates: [Double] = []
    @Published var selectedSampleRate: Double = 44100 { didSet { restartEngine() } }
    @Published var frequency: Double = 440
    @Published var isPlaying = false
    @Published var currentScopeFrame: ScopeFrame?

    let scopeProcessor = ScopeProcessor()

    private var avEngine: AVAudioEngine?
    private var sourceNode: AVAudioSourceNode?
    private var phase: Double = 0
    private var renderSampleRate: Double = 44100
    private var scopeTimer: AnyCancellable?
    private var tapDiagCount = 0

    init() { refreshDevices() }

    // MARK: - Device enumeration

    func refreshDevices() {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &dataSize) == noErr else { return }
        let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var ids = [AudioDeviceID](repeating: 0, count: count)
        guard AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &dataSize, &ids) == noErr else { return }

        var outputs: [AudioDevice] = []
        for deviceID in ids {
            guard let name = deviceName(deviceID) else { continue }
            if channelCount(deviceID, scope: kAudioObjectPropertyScopeOutput) > 0 {
                outputs.append(AudioDevice(id: deviceID, name: name))
            }
        }

        DispatchQueue.main.async {
            self.outputDevices = outputs
            if self.selectedDevice == nil { self.selectedDevice = outputs.first }
        }
    }

    // MARK: - Generator

    func togglePlay() { isPlaying ? stop() : start() }

    func start() {
        guard !isPlaying else { return }
        isPlaying = true
        restartEngine()
    }

    func stop() {
        guard isPlaying else { return }
        isPlaying = false
        restartEngine()
    }

    // MARK: - Engine lifecycle

    private func restartEngine() {
        stopEngine()
        guard selectedDevice != nil else { return }
        startEngine()
    }

    private func startEngine() {
        guard let device = selectedDevice else { return }
        renderSampleRate = selectedSampleRate
        let engine = AVAudioEngine()

        // Set device before installTap so the tap negotiates format against the right device.
        // Accessing inputNode forces the underlying AUHAL to be created.
        _ = engine.inputNode
        if let au = engine.outputNode.audioUnit {
            var id = device.id
            AudioUnitSetProperty(au, kAudioOutputUnitProperty_CurrentDevice,
                                 kAudioUnitScope_Global, 0, &id,
                                 UInt32(MemoryLayout<AudioDeviceID>.size))
        }

        // Always wire output chain so the AUHAL output side has something to drive.
        engine.connect(engine.mainMixerNode, to: engine.outputNode, format: nil)

        // Scope tap — always installed; uses the louder of the two input channels
        tapDiagCount = 0
        engine.inputNode.installTap(onBus: 0, bufferSize: 4096, format: nil) { [weak self] buffer, _ in
            guard let self, let data = buffer.floatChannelData else { return }
            let count = Int(buffer.frameLength)
            let numCh = Int(buffer.format.channelCount)
            let sr = buffer.format.sampleRate
            if self.scopeProcessor.sampleRate != sr { self.scopeProcessor.sampleRate = sr }

            var peak0: Float = 0
            vDSP_maxmgv(data[0], 1, &peak0, vDSP_Length(count))
            var ch = 0
            if numCh > 1 {
                var peak1: Float = 0
                vDSP_maxmgv(data[1], 1, &peak1, vDSP_Length(count))
                if peak1 > peak0 { ch = 1 }
                self.tapDiagCount += 1
                if self.tapDiagCount <= 5 || self.tapDiagCount % 200 == 0 {
                    print("Scope tap #\(self.tapDiagCount): ch0=\(String(format:"%.5f",peak0)) ch1=\(String(format:"%.5f",peak1)) → ch\(ch)")
                }
            }
            self.scopeProcessor.push(channelData: data[ch], count: count)
        }

        // Generator source node — only when playing
        if isPlaying {
            phase = 0
            if let format = AVAudioFormat(standardFormatWithSampleRate: renderSampleRate, channels: 2) {
                let node = AVAudioSourceNode(format: format) { [weak self] _, _, frameCount, audioBufferList -> OSStatus in
                    guard let self else { return noErr }
                    let abl = UnsafeMutableAudioBufferListPointer(audioBufferList)
                    let inc = 2.0 * Double.pi * self.frequency / self.renderSampleRate
                    for frame in 0..<Int(frameCount) {
                        let s = Float(sin(self.phase))
                        self.phase += inc
                        if self.phase >= 2.0 * Double.pi { self.phase -= 2.0 * Double.pi }
                        for buf in abl { buf.mData!.assumingMemoryBound(to: Float.self)[frame] = s }
                    }
                    return noErr
                }
                engine.attach(node)
                engine.connect(node, to: engine.mainMixerNode, format: format)
                engine.connect(engine.mainMixerNode, to: engine.outputNode, format: nil)
                sourceNode = node
            }
        }

        engine.prepare()

        do {
            try engine.start()
            avEngine = engine
            scopeTimer = Timer.publish(every: 1.0 / 15.0, on: .main, in: .common)
                .autoconnect()
                .sink { [weak self] _ in self?.currentScopeFrame = self?.scopeProcessor.analyze() }
        } catch {
            print("Engine start failed: \(error)")
        }
    }

    private func stopEngine() {
        scopeTimer?.cancel()
        scopeTimer = nil
        avEngine?.inputNode.removeTap(onBus: 0)
        avEngine?.stop()
        avEngine    = nil
        sourceNode  = nil
        currentScopeFrame = nil
    }

    private func deviceChanged() {
        guard let device = selectedDevice else { stopEngine(); return }
        let rates = device.supportedSampleRates()
        availableSampleRates = rates.isEmpty ? [44100, 48000] : rates
        if !availableSampleRates.contains(selectedSampleRate) {
            selectedSampleRate = availableSampleRates.first ?? 44100
            // selectedSampleRate.didSet calls restartEngine()
        } else {
            restartEngine()
        }
    }

    // MARK: - CoreAudio helpers

    private func channelCount(_ deviceID: AudioDeviceID, scope: AudioObjectPropertyScope) -> Int {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreamConfiguration,
            mScope: scope,
            mElement: kAudioObjectPropertyElementMain
        )
        var dataSize: UInt32 = 0
        guard AudioObjectGetPropertyDataSize(deviceID, &address, 0, nil, &dataSize) == noErr,
              dataSize > 0 else { return 0 }
        let buffer = UnsafeMutablePointer<AudioBufferList>.allocate(capacity: Int(dataSize))
        defer { buffer.deallocate() }
        guard AudioObjectGetPropertyData(deviceID, &address, 0, nil, &dataSize, buffer) == noErr else { return 0 }
        return UnsafeMutableAudioBufferListPointer(buffer).reduce(0) { $0 + Int($1.mNumberChannels) }
    }

    private func deviceName(_ deviceID: AudioDeviceID) -> String? {
        var address = AudioObjectPropertyAddress(
            mSelector: kAudioObjectPropertyName,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var cfString: Unmanaged<CFString>? = nil
        var dataSize = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
        guard withUnsafeMutablePointer(to: &cfString, {
            AudioObjectGetPropertyData(deviceID, &address, 0, nil, &dataSize, $0)
        }) == noErr else { return nil }
        return cfString?.takeRetainedValue() as String?
    }
}
