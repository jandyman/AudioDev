//
//  ViewController.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 3/27/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

protocol AuDelegate {
  func AuUpdated()
}

class ViewController: UIViewController, AuDelegate {
  
  var filtGraphVc : FreqGraphVc!
  var filtGraphDataSource = FiltDataSource()
  var eqVc : EqViewController!
  let percentHeightToGraph = CGFloat(0.60)
  var audioPath : AudioPath!
  let nFreqPoints = 300
  
  var au : EqAU { return AudioPath.AU! }

  override func viewDidLoad() {
    super.viewDidLoad()
    setupFreqGraphView()
    setupEqControlsView()
    audioPath = AudioPath()
    while !audioPath.auInstantiated {}
    eqVc.eqAU = au
    eqVc.initAu()
    eqVc.updateUi()
    au.setupFftAnalyzer(forMin: 10, max: 10000, nFreqPoints: Int32(nFreqPoints))
  }
  
  func AuUpdated() {
    updateFrequencyResponseGraph()
  }
  
  func updateFrequencyResponseGraph() {
    let x = Array(UnsafeBufferPointer(start: au.getFrequencyPoints(),
                                      count: nFreqPoints))
    filtGraphDataSource.x = x
    let y = Array(UnsafeBufferPointer(start: au.getFreqResponse(),
                                      count: nFreqPoints))
    filtGraphDataSource.y = y
    filtGraphVc.UpdateUi()
  }
  
  func setupFreqGraphView() {
    let sb = UIStoryboard(name: "Main", bundle: nil)
    filtGraphVc = sb.instantiateViewController(withIdentifier: "FreqGraph") as? FreqGraphVc
    addChild(filtGraphVc)

    let subview = filtGraphVc.view!
    view.addSubview(subview)
    subview.translatesAutoresizingMaskIntoConstraints = false
    let margins = view.layoutMarginsGuide
    // Pin the leading edge of the subview to the margin's leading edge
    subview.leadingAnchor.constraint(equalTo: margins.leadingAnchor).isActive = true
    // Pin the trailing edge of subview to the margin's trailing edge
    subview.trailingAnchor.constraint(equalTo: margins.trailingAnchor).isActive = true
    // Pin the top edge of subview to the margin's top edge
    subview.topAnchor.constraint(equalTo: margins.topAnchor).isActive = true
    // make the subview height a percentage times the height of
    subview.heightAnchor.constraint(equalTo: margins.heightAnchor,
                                    multiplier: percentHeightToGraph).isActive = true
    filtGraphVc.addTrace(dataSource: filtGraphDataSource)
  }

  func setupEqControlsView() {
    let sb = UIStoryboard(name: "Main", bundle: nil)
    eqVc = sb.instantiateViewController(withIdentifier: "EqControls") as? EqViewController
    addChild(eqVc)
    eqVc.auDelegate = self
    
    let subview = eqVc.view!
    view.addSubview(subview)
    subview.translatesAutoresizingMaskIntoConstraints = false
    let margins = view.layoutMarginsGuide
    // Pin the leading edge of the subview to the margin's leading edge
    subview.leadingAnchor.constraint(equalTo: margins.leadingAnchor).isActive = true
    // Pin the trailing edge of subview to the margin's trailing edge
    subview.trailingAnchor.constraint(equalTo: margins.trailingAnchor).isActive = true
    // Pin the top edge of subview to the margin's top edge
    subview.bottomAnchor.constraint(equalTo: margins.bottomAnchor).isActive = true
    // make the subview height a perentage times the height of
    subview.heightAnchor.constraint(equalTo: margins.heightAnchor,
                                    multiplier: 1 - percentHeightToGraph).isActive = true
  }


  
}

