// CQHold — menu bar app that keeps a silent Core Audio output stream open to
// a USB interface (e.g. Allen & Heath CQ-20B), so the device's stream never
// tears down and the macOS 26+ "looped last buffer" buzz can't trigger.
//
// Build with build-cqhold.sh (produces CQHold.app). No Xcode project needed.

import Cocoa
import CoreAudio
import AudioToolbox

// MARK: - Core Audio helpers

struct OutputDevice {
    let id: AudioDeviceID
    let name: String
    let channels: Int
}

func propAddr(_ selector: AudioObjectPropertySelector,
              _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal) -> AudioObjectPropertyAddress {
    AudioObjectPropertyAddress(mSelector: selector, mScope: scope,
                               mElement: kAudioObjectPropertyElementMain)
}

func allDeviceIDs() -> [AudioDeviceID] {
    var addr = propAddr(kAudioHardwarePropertyDevices)
    var size: UInt32 = 0
    let sys = AudioObjectID(kAudioObjectSystemObject)
    guard AudioObjectGetPropertyDataSize(sys, &addr, 0, nil, &size) == noErr else { return [] }
    var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
    guard AudioObjectGetPropertyData(sys, &addr, 0, nil, &size, &ids) == noErr else { return [] }
    return ids
}

func deviceName(_ id: AudioDeviceID) -> String {
    var addr = propAddr(kAudioObjectPropertyName)
    var name: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    guard AudioObjectGetPropertyData(id, &addr, 0, nil, &size, &name) == noErr,
          let n = name else { return "?" }
    return n.takeRetainedValue() as String
}

func outputChannelCount(_ id: AudioDeviceID) -> Int {
    var addr = propAddr(kAudioDevicePropertyStreamConfiguration, kAudioObjectPropertyScopeOutput)
    var size: UInt32 = 0
    guard AudioObjectGetPropertyDataSize(id, &addr, 0, nil, &size) == noErr, size > 0 else { return 0 }
    let raw = UnsafeMutableRawPointer.allocate(
        byteCount: Int(size), alignment: MemoryLayout<AudioBufferList>.alignment)
    defer { raw.deallocate() }
    let abl = raw.bindMemory(to: AudioBufferList.self, capacity: 1)
    guard AudioObjectGetPropertyData(id, &addr, 0, nil, &size, abl) == noErr else { return 0 }
    return UnsafeMutableAudioBufferListPointer(abl).reduce(0) { $0 + Int($1.mNumberChannels) }
}

func outputDevices() -> [OutputDevice] {
    allDeviceIDs()
        .map { OutputDevice(id: $0, name: deviceName($0), channels: outputChannelCount($0)) }
        .filter { $0.channels > 0 }
}

func isDeviceAlive(_ id: AudioDeviceID) -> Bool {
    var addr = propAddr(kAudioDevicePropertyDeviceIsAlive)
    var alive: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    return AudioObjectGetPropertyData(id, &addr, 0, nil, &size, &alive) == noErr && alive != 0
}

// Render callback: zero every buffer, every cycle.
let renderSilence: AURenderCallback = { _, _, _, _, _, ioData in
    if let ioData = ioData {
        for buf in UnsafeMutableAudioBufferListPointer(ioData) {
            if let p = buf.mData { memset(p, 0, Int(buf.mDataByteSize)) }
        }
    }
    return noErr
}

// MARK: - Silent output engine

final class SilentOutput {
    private var unit: AudioUnit?
    private var aliveListener: AudioObjectPropertyListenerBlock?
    private(set) var deviceID: AudioDeviceID = 0
    var onDeviceLost: (() -> Void)?

    var isRunning: Bool { unit != nil }

    func start(device: AudioDeviceID) -> OSStatus {
        stop()

        var desc = AudioComponentDescription(
            componentType: kAudioUnitType_Output,
            componentSubType: kAudioUnitSubType_HALOutput,
            componentManufacturer: kAudioUnitManufacturer_Apple,
            componentFlags: 0, componentFlagsMask: 0)
        guard let comp = AudioComponentFindNext(nil, &desc) else { return -1 }

        var newUnit: AudioUnit?
        var err = AudioComponentInstanceNew(comp, &newUnit)
        guard err == noErr, let u = newUnit else { return err }

        var dev = device
        err = AudioUnitSetProperty(u, kAudioOutputUnitProperty_CurrentDevice,
                                   kAudioUnitScope_Global, 0,
                                   &dev, UInt32(MemoryLayout<AudioDeviceID>.size))
        if err == noErr {
            var cb = AURenderCallbackStruct(inputProc: renderSilence, inputProcRefCon: nil)
            err = AudioUnitSetProperty(u, kAudioUnitProperty_SetRenderCallback,
                                       kAudioUnitScope_Input, 0,
                                       &cb, UInt32(MemoryLayout<AURenderCallbackStruct>.size))
        }
        if err == noErr { err = AudioUnitInitialize(u) }
        if err == noErr { err = AudioOutputUnitStart(u) }
        if err != noErr {
            AudioUnitUninitialize(u)
            AudioComponentInstanceDispose(u)
            return err
        }

        unit = u
        deviceID = device

        // Stop and notify if the device is unplugged or powered off.
        let block: AudioObjectPropertyListenerBlock = { [weak self] _, _ in
            guard let self = self, self.isRunning else { return }
            if !isDeviceAlive(self.deviceID) {
                self.stop()
                self.onDeviceLost?()
            }
        }
        var addr = propAddr(kAudioDevicePropertyDeviceIsAlive)
        AudioObjectAddPropertyListenerBlock(device, &addr, DispatchQueue.main, block)
        aliveListener = block

        return noErr
    }

    func stop() {
        if let block = aliveListener {
            var addr = propAddr(kAudioDevicePropertyDeviceIsAlive)
            AudioObjectRemovePropertyListenerBlock(deviceID, &addr, DispatchQueue.main, block)
            aliveListener = nil
        }
        guard let u = unit else { return }
        AudioOutputUnitStop(u)
        AudioUnitUninitialize(u)
        AudioComponentInstanceDispose(u)
        unit = nil
    }
}

// MARK: - Menu bar app

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    private let menu = NSMenu()
    private let output = SilentOutput()
    private let defaultsKey = "deviceName"

    /// The device the user picked from the menu (remembered across launches).
    private var preferredName: String? {
        get { UserDefaults.standard.string(forKey: defaultsKey) }
        set { UserDefaults.standard.set(newValue, forKey: defaultsKey) }
    }

    /// The picked device, if it's currently connected. No automatic fallback.
    private func targetDevice(in devices: [OutputDevice]) -> OutputDevice? {
        guard let name = preferredName else { return nil }
        return devices.first { $0.name == name }
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        menu.delegate = self
        statusItem.menu = menu
        output.onDeviceLost = { [weak self] in self?.updateIcon() }
        updateIcon()
    }

    func applicationWillTerminate(_ notification: Notification) {
        output.stop()
    }

    private func updateIcon() {
        let symbol = output.isRunning ? "speaker.wave.2.fill" : "speaker.slash"
        let image = NSImage(systemSymbolName: symbol, accessibilityDescription: "CQ Hold")
        image?.isTemplate = true
        statusItem.button?.image = image
        statusItem.button?.toolTip = output.isRunning
            ? "CQ Hold: on (\(deviceName(output.deviceID)))"
            : "CQ Hold: off"
    }

    // Rebuild the menu each time it opens so the device list is current.
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let devices = outputDevices()
        let target = targetDevice(in: devices)

        let toggle = NSMenuItem(title: "Hold Silent Output",
                                action: #selector(toggleHold), keyEquivalent: "")
        toggle.target = self
        toggle.state = output.isRunning ? .on : .off
        if target == nil && !output.isRunning { toggle.isEnabled = false }
        menu.addItem(toggle)

        if target == nil && !output.isRunning {
            let hint = NSMenuItem(
                title: preferredName == nil ? "Choose a device below"
                                            : "\(preferredName!) not connected",
                action: nil, keyEquivalent: "")
            hint.isEnabled = false
            menu.addItem(hint)
        }

        menu.addItem(.separator())
        let header = NSMenuItem(title: "Device", action: nil, keyEquivalent: "")
        header.isEnabled = false
        menu.addItem(header)

        if devices.isEmpty {
            let none = NSMenuItem(title: "No output devices", action: nil, keyEquivalent: "")
            none.isEnabled = false
            menu.addItem(none)
        }
        for d in devices {
            let item = NSMenuItem(title: d.name, action: #selector(selectDevice(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = d.name
            item.state = (d.name == target?.name) ? .on : .off
            item.indentationLevel = 1
            menu.addItem(item)
        }

        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Quit CQ Hold", action: #selector(quit), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)
    }

    @objc private func toggleHold() {
        if output.isRunning {
            output.stop()
        } else {
            startOnTarget()
        }
        updateIcon()
    }

    @objc private func selectDevice(_ sender: NSMenuItem) {
        guard let name = sender.representedObject as? String else { return }
        preferredName = name
        if output.isRunning { startOnTarget() }   // move the hold to the new device
        updateIcon()
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    private func startOnTarget() {
        guard let d = targetDevice(in: outputDevices()) else {
            alert("No device selected", "Pick a connected device from the menu.")
            return
        }
        let err = output.start(device: d.id)
        if err != noErr {
            alert("Couldn't start output", "\(d.name): OSStatus \(err)")
        }
    }

    private func alert(_ title: String, _ text: String) {
        let a = NSAlert()
        a.messageText = title
        a.informativeText = text
        NSApp.activate(ignoringOtherApps: true)
        a.runModal()
    }
}

// MARK: - Entry point

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)   // menu bar only, no Dock icon
app.run()
