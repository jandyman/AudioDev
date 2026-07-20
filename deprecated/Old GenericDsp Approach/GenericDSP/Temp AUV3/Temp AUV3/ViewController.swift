//
//  ViewController.swift
//  Temp AUV3
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

import UIKit
import AudioToolbox

class ViewController: UIViewController {
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    let audioPath = AudioPath()
    while !audioPath.auInstantiated {}
  }
  
  
}

