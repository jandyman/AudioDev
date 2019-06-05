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
  @IBOutlet weak var masterLevelMeter: BasicVuMeter!
  @IBOutlet weak var leftMuteSwitch: LabeledSwitch!
  @IBOutlet weak var rightMuteSwitch: LabeledSwitch!
  @IBOutlet weak var rightDbSlider: VerticalSlider!
  @IBOutlet weak var masterDbSlider: VerticalSlider!
  @IBOutlet weak var phaseInvertSwitch: LabeledSwitch!
  @IBOutlet weak var btnSave: UIButton!

  var levelTimer : Timer?
  
  override func viewDidLoad() {
    super.viewDidLoad()
    levelTimer = Timer.scheduledTimer(withTimeInterval: 0.05
      ,
                                      repeats: true, block: updateMeters)
    updateUi()
  }
  
  func updateUi() {
    if let au = AudioPath.AU {
      leftMuteSwitch.isOn = !au.getLeftEnable()
      rightMuteSwitch.isOn = !au.getRightEnable()
      phaseInvertSwitch.isOn = !au.getInPhase()
      rightDbSlider.value = CGFloat(au.getRightGainDb())
      masterDbSlider.value = CGFloat(au.getMasterGainDb())
    }
  }
  
  @objc func updateMeters(_ timer: Timer) {
    if let au = AudioPath.AU {
      inputLeftLevelMeter.SetEnvelope(au.getLevelForIdx(0))
      inputRightLevelMeter.SetEnvelope(au.getLevelForIdx(1))
      outputLeftLevelMeter.SetEnvelope(au.getLevelForIdx(2))
      outputRightLevelMeter.SetEnvelope(au.getLevelForIdx(3))
      masterLevelMeter.SetEnvelope(au.getLevelForIdx(4))
    }
  }
  
  @IBAction func leftMuteButtonPressed(_ sender: LabeledSwitch) {
    AudioPath.AU!.setLeftEnable(!sender.isOn)
  }
  
  @IBAction func rightMuteButtonPressed(_ sender: LabeledSwitch) {
    AudioPath.AU!.setRightEnable(!sender.isOn)
  }
  
  @IBAction func phaseInvertSwitchPressed(_ sender: LabeledSwitch) {
    AudioPath.AU!.setInPhase(!sender.isOn)
  }
  
  @IBAction func rightDbSliderChanged(_ sender: VerticalSlider) {
    AudioPath.AU!.setRightGainDb(Float(sender.value))
  }
  
  @IBAction func masterDbSliderChanged(_ sender: VerticalSlider) {
    AudioPath.AU!.setMasterGainDb(Float(sender.value))
  }
  
  @IBAction func SaveButtonPressed(_ sender: UIButton) {
    AudioPath.saveSettings(filename: "settings.txt")
  }

}
