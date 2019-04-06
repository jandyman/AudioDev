//
//  AvEngine.swift
//  Temp AUV3
//
//  Created by Andrew Voelkel on 11/9/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
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

var engine = AVAudioEngine()
var audioFormat : AVAudioFormat?

class AudioPath {
  
  static let engine = AVAudioEngine()
  
  init() {
    let type = OSType("aufx")
    let subtype = OSType("gain")
    let manufacturer = OSType("Demo")
    let desc = AudioComponentDescription(componentType: type,
                                         componentSubType: subtype,
                                         componentManufacturer: manufacturer,
                                         componentFlags: 0, componentFlagsMask: 0)
    AUAudioUnit.registerSubclass(GainAU.self, as: desc, name: "Gain AU demo", version: UInt32.max)
    AVAudioUnit.instantiate(with: desc, options: .loadOutOfProcess, completionHandler: auInstantiated)
  }
  
  private(set) var auInstantiated = false
  
  private func auInstantiated(au: AVAudioUnit?, err: Error?) {
    auInstantiated = true
    audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)
    if (au != nil) {
      let engine = AudioPath.engine
      engine.attach(au!)
      engine.connect(engine.inputNode, to: au!, format: audioFormat)
      engine.connect(au!, to: engine.mainMixerNode, format: audioFormat)
      engine.prepare()
      
      do { try engine.start() }
      catch let error {
        print(error.localizedDescription)
      }
    }
  }
  
}
