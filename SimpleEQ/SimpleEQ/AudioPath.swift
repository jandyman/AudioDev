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

  static var audioFormat : AVAudioFormat!
  static var engine = AVAudioEngine()
  static var AU : EqAU?
  
  init() {
    let type = OSType("aufx")
    let subtype = OSType("gain")
    let manufacturer = OSType("Demo")
    let desc = AudioComponentDescription(componentType: type,
                                         componentSubType: subtype,
                                         componentManufacturer: manufacturer,
                                         componentFlags: 0, componentFlagsMask: 0)
    AUAudioUnit.registerSubclass(EqAU.self, as: desc, name: "EQ AU", version: UInt32.max)
    AVAudioUnit.instantiate(with: desc, options: .loadOutOfProcess, completionHandler: auInstantiated)
  }
  
  private(set) var auInstantiated = false
  
  private func auInstantiated(au: AVAudioUnit?, err: Error?) {
    var audioFormat = AudioPath.audioFormat
    auInstantiated = true
    audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)
    if (au != nil) {
      AudioPath.AU = au?.auAudioUnit as? EqAU
      let engine = AudioPath.engine
      engine.attach(au!)
      engine.connect(engine.inputNode, to: au!, format: audioFormat)
      engine.connect(au!, to: engine.mainMixerNode, format: audioFormat)
      engine.prepare()
      
      do {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(AVAudioSession.Category.playAndRecord)
        try session.setPreferredIOBufferDuration(0.004)
        try engine.start()
      }
      catch let error {
        print(error.localizedDescription)
      }
    }
  }
  
}
