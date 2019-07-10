//
//  ViewController.swift
//  AVAudioEngine Wire iOS
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

import UIKit
import AVFoundation

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

class ViewController: UIViewController {
  
  var session = AVAudioSession.sharedInstance()
  var engine = AVAudioEngine()
  var audioUnit : AVAudioUnit?
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    createAU()
    
    let nc = NotificationCenter.default
    nc.addObserver(self,
                   selector: #selector(handleRouteChange),
                   name: AVAudioSession.routeChangeNotification,
                   object: nil)
    
    do {
      try session.setCategory(.playAndRecord, mode: .default)
      try session.setActive(true)
    } catch let error {
      print(error.localizedDescription)
    }
    
  }
  
  func createAU() {
    let type = OSType("aufx")
    let subtype = OSType("thru")
    let manufacturer = OSType("Demo")
    let desc = AudioComponentDescription(componentType: type,
                                         componentSubType: subtype,
                                         componentManufacturer: manufacturer,
                                         componentFlags: 0, componentFlagsMask: 0)
    AUAudioUnit.registerSubclass(ThruAudioUnit.self, as: desc, name: "Wire AU demo", version: UInt32.max)
    AVAudioUnit.instantiate(with: desc, options: .loadOutOfProcess, completionHandler: auInstantiated)
  }
  
  private func auInstantiated(au: AVAudioUnit?, err: Error?) {
    audioUnit = au!
  }

  
  @objc func handleRouteChange(notification: Notification) {
    let inputs = session.currentRoute.inputs
    assert(inputs.count == 1)
    let nChannels = inputs[0].channels?.count
    
    do {
      if nChannels == 4 && audioUnit != nil {
        print("starting engine")
        // create 4 channel layout
        let layout = AVAudioChannelLayout(layoutTag: kAudioChannelLayoutTag_Unknown | 4)!
//        let layout = AVAudioChannelLayout(layoutTag: kAudioChannelLayoutTag_Stereo)!
        let audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channelLayout: layout)
//        let audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)
        engine.attach(audioUnit!)
        engine.connect(engine.inputNode, to: audioUnit!, format: audioFormat)
        engine.connect(audioUnit!, to: engine.outputNode, format: audioFormat)
        try engine.start()
      } else {
        engine.stop()
        print("stopping engine")
      }
    } catch let error {
      print(error.localizedDescription)
    }
  }
}

