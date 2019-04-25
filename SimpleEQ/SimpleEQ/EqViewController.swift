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
  
  override func viewDidLoad() {
    super.viewDidLoad()
  }
  
  func updateUi() {
    for i in Int32(0) ..< Int32(nStages) {
      let enabled = eqAU.getEnabledAt(i)
      stageIndicator.SetEnable(Int(i), enable: enabled)
    }
    enableSwitch.isOn = eqAU.getEnabledAt(selectedStage)
    typeSelector.selectedSegmentIndex = Int(eqAU.getTypeAt(selectedStage))
    orderSelector.selectedSegmentIndex = Int(eqAU.getOrderAt(selectedStage) - 1)
    frequencyCombo.Value = Double(eqAU.getFrequencyAt(selectedStage))
    boostCombo.Value = Double(eqAU.getDbAt(selectedStage))
    qCombo.Value = Double(eqAU.getQAt(selectedStage))
    auDelegate.AuUpdated()
  }
  
  func initAu() {
    for i in 0..<Int32(nStages) {
      eqAU.setEnabled(false, at: i)
      eqAU.setType(0, at: i)
      eqAU.setOrder(1, at: i)
      eqAU.setFrequency(1000.0, at: i)
      eqAU.setDb(0.0, at: i)
      eqAU.setQ(1.0, at: i)
    }
  }
  
  @IBAction func selectedStageChanged(_ sender: UISegmentedControl) {
    selectedStage = Int32(sender.selectedSegmentIndex)
    updateUi()
  }
  
  @IBAction func enableSwitchChanged(_ sender: UISwitch) {
    eqAU.setEnabled(sender.isOn, at: selectedStage)
    updateUi()
  }
  
  @IBAction func typeChanged(_ sender: UISegmentedControl) {
    eqAU.setType(Int32(sender.selectedSegmentIndex), at: selectedStage)
    updateUi()
  }
  
  @IBAction func orderChanged(_ sender: UISegmentedControl) {
    eqAU.setOrder(Int32(sender.selectedSegmentIndex + 1), at: selectedStage)
    updateUi()
  }
  
  @IBAction func frequencyChanged(_ sender: LogParamCombo) {
    eqAU.setFrequency(Float(sender.Value), at: selectedStage)
    updateUi()
  }
  
  @IBAction func boostChanged(_ sender: NumericCombo2) {
    eqAU.setDb(Float(sender.Value), at: selectedStage)
    updateUi()
  }
  
  @IBAction func qChanged(_ sender: NumericCombo2) {
    eqAU.setQ(Float(sender.Value), at: selectedStage)
    updateUi()
  }
  
}
