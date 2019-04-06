//
//  FooViewController.swift
//  UiSandbox
//
//  Created by Andrew Voelkel on 4/1/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

class FooViewController: UIViewController {
  
  @IBOutlet weak var stageIndicator: MultiIndicator!
  @IBOutlet weak var dbCombo: NumericCombo2!
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    stageIndicator.SetEnable(2, enable: true)
  }
  
  
  /*
   // MARK: - Navigation
   
   // In a storyboard-based application, you will often want to do a little preparation before navigation
   override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
   // Get the new view controller using segue.destination.
   // Pass the selected object to the new view controller.
   }
   */
  
}
