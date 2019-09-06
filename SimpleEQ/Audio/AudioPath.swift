//
//  AudioPath.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 4/13/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import Foundation
import AudioToolbox

extension OSType {
  init(_ string: String) {
    let utf8 = string.utf8
    precondition(utf8.count == 4, "Must be a 4 char string")
    var out: UInt32 = 0
    for char in utf8 {
      out <<= 8
      out |= UInt32(char)
    }
    self = out
  }
}

class AudioPath {

  enum AuState {
    case uninitialized
    case initializing
    case initialized
    case running
  }

  static let shared = AudioPath()

  var session = AVAudioSession.sharedInstance()
  var audioFormat : AVAudioFormat!
  var engine = AVAudioEngine()
  var avAudioUnit : AVAudioUnit?
  var au : EqAU?
  private var state = AuState.uninitialized
  var ready : Bool { return state == .initialized && state == .running}
  var running : Bool { return state == .running }
  
  private init() {
    let type = OSType("aufx")
    let subtype = OSType("gain")
    let manufacturer = OSType("Demo")
    let desc = AudioComponentDescription(componentType: type,
                                         componentSubType: subtype,
                                         componentManufacturer: manufacturer,
                                         componentFlags: 0, componentFlagsMask: 0)
    AUAudioUnit.registerSubclass(EqAU.self, as: desc, name: "EQ AU", version: UInt32.max)
    state = .initializing
    AVAudioUnit.instantiate(with: desc,
                            options: .loadOutOfProcess,
                            completionHandler: auInstantiated)

    let nc = NotificationCenter.default
    nc.addObserver(self,
                   selector: #selector(handleRouteChangeNotification),
                   name: AVAudioSession.routeChangeNotification,
                   object: nil)

    try! session.setCategory(.playAndRecord, mode: .default)
    try! session.setActive(true)
    try! session.setPreferredIOBufferDuration(0.004)
    // handleRouteChange()
  }

  @objc func handleRouteChangeNotification(notification: Notification) {
    handleRouteChange()
  }

  func handleRouteChange() {
    let inputs = session.currentRoute.inputs
    assert(inputs.count == 1)
    let nChannels = inputs[0].channels!.count
    let isUsbAudio = inputs[0].portType == AVAudioSession.Port.usbAudio

    do {
      if isUsbAudio, let avAudioUnit = self.avAudioUnit {
        print("starting engine")
        // create 2 channel layout
        let layout = AVAudioChannelLayout(layoutTag: kAudioChannelLayoutTag_Unknown | UInt32(nChannels))!
        let audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channelLayout: layout)
        engine.attach(avAudioUnit)
        engine.connect(engine.inputNode, to: avAudioUnit, format: audioFormat)
        engine.connect(avAudioUnit, to: engine.outputNode, format: audioFormat)
        try engine.start()
        state = .running
      } else {
        engine.stop()
        print("stopping engine")
      }
    } catch let error {
      print(error.localizedDescription)
    }
  }
    
  private func auInstantiated(_avAudioUnit: AVAudioUnit?, err: Error?) {
    avAudioUnit = _avAudioUnit
    au = (avAudioUnit!.auAudioUnit as! EqAU)
    setAuDefaults()
    loadSettings(baseName: "settings")
    state = .initialized
  }
  
  func setAuDefaults() {
    if let au = self.au {
      for unitIdx in 0..<Int32(2) {
        for i in 0..<Int32(6) {
          au.setEnabled(unitIdx, enable: false, stage: i)
        }
        // filter 0
        au.setType(unitIdx, type: 0, stage: 0)
        au.setOrder(unitIdx, order: 1, stage: 0)
        au.setFrequency(unitIdx, frequency: 70, stage: 0)
        au.setDb(unitIdx, dB: 0, stage: 0)
        // filter 1
        au.setType(unitIdx, type: 1, stage: 1)
        au.setFrequency(unitIdx, frequency: 70, stage: 1)
        au.setQ(unitIdx, q: 2, stage: 1)
        au.setDb(unitIdx, dB: 0, stage: 1)
        // filter 2
        au.setType(unitIdx, type: 1, stage: 2)
        au.setFrequency(unitIdx, frequency: 130, stage: 2)
        au.setQ(unitIdx, q: 2, stage: 2)
        au.setDb(unitIdx, dB: 0, stage: 2)
        // filter 3
        au.setType(unitIdx, type: 1, stage: 3)
        au.setOrder(unitIdx, order: 1, stage: 3)
        au.setFrequency(unitIdx, frequency: 500, stage: 3)
        au.setDb(unitIdx, dB: 0, stage: 3)
        // filter 4
        au.setType(unitIdx, type: 1, stage: 4)
        au.setFrequency(unitIdx, frequency: 900, stage: 4)
        au.setQ(unitIdx, q: 2, stage: 4)
        au.setDb(unitIdx, dB: 0, stage: 4)
        // filter 4
        au.setType(unitIdx, type: 2, stage: 5)
        au.setFrequency(unitIdx, frequency: 3000, stage: 5)
        au.setOrder(unitIdx, order: 1, stage: 5)
        au.setDb(unitIdx, dB: 0, stage: 5)
      }
    }
  }

  static func getPatchFilenames() -> [String] {
    let fm = FileManager.default
    let path = fm.urls(for: .documentDirectory, in: .userDomainMask)[0]
    let urls = try! fm.contentsOfDirectory(at: path, includingPropertiesForKeys: nil)
    let filtered = urls.filter { $0.pathExtension == "txt"}
    let filenames = filtered.map { $0.deletingPathExtension().lastPathComponent }
    return filenames
  }
  
  private static func getDocUrl(filename: String) -> URL {
    let fm = FileManager.default
    let path = fm.urls(for: .documentDirectory, in: .userDomainMask)
    let url = path[0].appendingPathComponent(filename)
    return url
  }
  
  func saveSettings(baseName: String) {
    let filename = baseName + ".txt"
    let url = AudioPath.getDocUrl(filename: filename)
    let eqAU = au!
    let testStr = eqAU.getSettings()!
    do {
      try testStr.write(to: url, atomically: true, encoding: String.Encoding.utf8)
    } catch {
      print(error)
    }
  }
  
  func loadSettings(baseName: String) {
    let filename = baseName + ".txt"
    let url = AudioPath.getDocUrl(filename: filename)
    do {
      let jstring = try String(contentsOf: url, encoding: .utf8)
      au!.initFromJson(jstring)
    } catch { print("can't read from \(filename)") }
  }
  
}
