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
  
  @IBOutlet weak var btnStart: UIButton!
  @IBOutlet weak var btnStop: UIButton!
  
  var session = AVAudioSession.sharedInstance()
  var engine = AVAudioEngine()
  
  var player = AVAudioPlayerNode()
  
  var audioFormat: AVAudioFormat?
  
  var audioFile: AVAudioFile? {
    didSet {
      if let audioFile = audioFile {
        audioFormat = audioFile.processingFormat
      }
    }
  }
    
  var audioFileURL: URL? {
    didSet {
      if let audioFileURL = audioFileURL {
        audioFile = try? AVAudioFile(forReading: audioFileURL)
      }
    }
  }
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    //        do {
    //        try session.setCategory(.playback, mode: .default)
    //        try session.setActive(true)
    //        } catch {
    //            print("error in viewDidLoad")
    //        }
    
    audioFileURL  = Bundle.main.url(forResource: "Intro", withExtension: "mp4")
    
    engine.attach(player)
    engine.connect(player, to: engine.mainMixerNode, format: audioFormat)
    //audioFormat = AVAudioFormat(standardFormatWithSampleRate: 44100, channels: 2)
    //engine.connect(engine.inputNode, to: engine.mainMixerNode, format: audioFormat)

    engine.prepare()
    
    do {
      try engine.start()
    } catch let error {
      print(error.localizedDescription)
    }
    
  }
  
  @IBAction func startBtnPressed(_ sender: Any) {
    guard let audioFile = audioFile else { return }
    player.scheduleFile(audioFile, at: nil)
    player.play()
  }
  
  @IBAction func stopBtnPressed(_ sender: Any) {
    engine.stop()
  }
  
}

