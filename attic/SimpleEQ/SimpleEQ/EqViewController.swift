//
//  FooViewController.swift
//  UiSandbox
//
//  Created by Andrew Voelkel on 4/1/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

class EqViewController: UIViewController {
  
  @IBOutlet weak var stageIndicator: MultiIndicator!
  @IBOutlet weak var stageSelector: UISegmentedControl!
  @IBOutlet weak var typeSelector: UISegmentedControl!
  @IBOutlet weak var orderSelector: UISegmentedControl!
  @IBOutlet weak var enableSwitch: UISwitch!
  @IBOutlet weak var frequencyCombo: LogParamCombo!
  @IBOutlet weak var boostCombo: NumericCombo2!
  @IBOutlet weak var qCombo: NumericCombo2!
  
  let nStages = 6
  var selectedStage = Int32(0)
  var eqAU : EqAU!
  var auDelegate : AuDelegate!
  var unitIdx = Int32(0)
  
  override func viewDidLoad() {
    super.viewDidLoad()
  }
  
  func updateUi() {
    for i in Int32(0) ..< Int32(nStages) {
      let enabled = eqAU.getEnabled(unitIdx, stage: i)
      stageIndicator.SetEnable(Int(i), enable: enabled)
    }
    enableSwitch.isOn = eqAU.getEnabled(unitIdx, stage: selectedStage)
    typeSelector.selectedSegmentIndex = Int(eqAU.getType(unitIdx, stage: selectedStage))
    orderSelector.selectedSegmentIndex = Int(eqAU.getOrder(unitIdx, stage: selectedStage) - 1)
    frequencyCombo.Value = Double(eqAU.getFrequency(unitIdx, stage: selectedStage))
    boostCombo.Value = Double(eqAU.getDb(unitIdx, stage: selectedStage))
    qCombo.Value = Double(eqAU.getQ(unitIdx, stage: selectedStage))
    auDelegate.AuUpdated()
  }
  
  @IBAction func selectedStageChanged(_ sender: UISegmentedControl) {
    selectedStage = Int32(sender.selectedSegmentIndex)
    updateUi()
  }
  
  @IBAction func enableSwitchChanged(_ sender: UISwitch) {
    eqAU.setEnabled(unitIdx, enable: sender.isOn, stage: selectedStage)
    updateUi()
  }
  
  @IBAction func typeChanged(_ sender: UISegmentedControl) {
    eqAU.setType(unitIdx, type: Int32(sender.selectedSegmentIndex), stage: selectedStage)
    updateUi()
  }
  
  @IBAction func orderChanged(_ sender: UISegmentedControl) {
    eqAU.setOrder(unitIdx, order: Int32(sender.selectedSegmentIndex + 1), stage: selectedStage)
    updateUi()
  }
  
  @IBAction func frequencyChanged(_ sender: LogParamCombo) {
    eqAU.setFrequency(unitIdx, frequency: Float(sender.Value), stage: selectedStage)
    updateUi()
  }
  
  @IBAction func boostChanged(_ sender: NumericCombo2) {
    eqAU.setDb(unitIdx, dB: Float(sender.Value), stage: selectedStage)
    updateUi()
  }
  
  @IBAction func qChanged(_ sender: NumericCombo2) {
    eqAU.setQ(unitIdx, q: Float(sender.Value), stage: selectedStage)
    updateUi()
  }
  
}
