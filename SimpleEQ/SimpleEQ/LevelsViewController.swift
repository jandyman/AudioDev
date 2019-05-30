//
//  LevelsViewController.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 5/10/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

class LevelsViewController: UIViewController {
  
  @IBOutlet weak var inputLeftLevelMeter: BasicVuMeter!
  @IBOutlet weak var inputRightLevelMeter: BasicVuMeter!
  @IBOutlet weak var outputLeftLevelMeter: BasicVuMeter!
  @IBOutlet weak var outputRightLevelMeter: BasicVuMeter!
  @IBOutlet weak var btnSave: UIButton!

  var levelTimer : Timer?
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    levelTimer = Timer.scheduledTimer(withTimeInterval: 0.1,
                                      repeats: true, block: updateMeters)
  }
  
  @objc func updateMeters(_ timer: Timer) {
    if let au = AudioPath.AU {
      inputLeftLevelMeter.SetEnvelope(au.getInputLevel(forChannel: 0))
      inputRightLevelMeter.SetEnvelope(au.getInputLevel(forChannel: 1))
      outputLeftLevelMeter.SetEnvelope(au.getOutputLevel(forChannel: 0))
      outputRightLevelMeter.SetEnvelope(au.getOutputLevel(forChannel: 1))
    }
  }
  
  @IBAction func SaveButtonPressed(_ sender: UIButton) {
    AudioPath.saveSettings(filename: "settings.txt")
  }

}
