//
//  ViewController.swift
//  AVAudioEngine Wire iOS
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

import UIKit
import AVFoundation

class ViewController: UIViewController {
  
  var session = AVAudioSession.sharedInstance()
  var engine = AVAudioEngine()
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
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
  
  @objc func handleRouteChange(notification: Notification) {
    let inputs = session.currentRoute.inputs
    assert(inputs.count == 1)
    let nChannels = inputs[0].channels?.count
    
    do {
      if nChannels == 4 {
        print("starting engine")
        // create 4 channel layout
        let layout = AVAudioChannelLayout(layoutTag: kAudioChannelLayoutTag_Unknown | 4)!
        let audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channelLayout: layout)
        engine.connect(engine.inputNode, to: engine.outputNode, format: audioFormat)
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

