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

class EqViewContainer: UIViewController, AuDelegate {
  
  var filtGraphVc : FreqGraphVc!
  var totalResponseDataSource = FiltDataSource()
  var selectedResponseDataSource = FiltDataSource()
  var eqVc : EqViewController!
  let percentHeightToGraph = CGFloat(0.60)
  let nFreqPoints = 300

  let au = AudioPath.shared.au
  let audioPath = AudioPath.shared
  
  @objc var EQ_idx: NSNumber!
  var unitIdx : Int32!
  
  override func viewDidLoad() {
    super.viewDidLoad()
    unitIdx = Int32(truncating: EQ_idx)
    setupFreqGraphView()
    setupEqControlsView()
    while !audioPath.ready {}
    eqVc.eqAU = au
    eqVc.updateUi()
    au!.setupFftAnalyzer(unitIdx, min: 10, max: 10000, nFreqPoints: Int32(nFreqPoints))
  }

  override func viewDidAppear(_ animated: Bool) {
    super.viewDidAppear(animated)
    eqVc.updateUi()
  }
  
  func AuUpdated() {
    updateFrequencyResponseGraph()
  }
  
  func updateFrequencyResponseGraph() {
    let x = Array(UnsafeBufferPointer(start: au!.getFrequencyPoints(unitIdx),
                                      count: nFreqPoints))
    totalResponseDataSource.x = x
    selectedResponseDataSource.x = x
    totalResponseDataSource.y = Array(UnsafeBufferPointer(start: au!.getFreqResponse(unitIdx),
                                                          count: nFreqPoints))
    let y = Array(UnsafeBufferPointer(start: au!.getFreqResponse(unitIdx,
                                                                stage: eqVc.selectedStage),
                                      count: nFreqPoints))
    selectedResponseDataSource.y = y
    filtGraphVc.UpdateUi()
  }
  
  func setupFreqGraphView() {
    let sb = UIStoryboard(name: "Main", bundle: nil)
    filtGraphVc = sb.instantiateViewController(withIdentifier: "FreqGraph") as? FreqGraphVc
    addChild(filtGraphVc)
    filtGraphVc.didMove(toParent: self)

    let subview = filtGraphVc.view!
    subview.translatesAutoresizingMaskIntoConstraints = false
    view.addSubview(subview)
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
    let color = CPTColor(componentRed: 128/256.0, green: 158/256.0, blue: 140/256.0,
                         alpha: 1)
    totalResponseDataSource.lineStyle.lineWidth = 3
    totalResponseDataSource.lineStyle.lineColor = color
    filtGraphVc.addTrace(dataSource: totalResponseDataSource)
    selectedResponseDataSource.lineStyle.lineWidth = 5
    selectedResponseDataSource.lineStyle.dashPattern = [8, 8]
    selectedResponseDataSource.lineStyle.lineColor = CPTColor(cgColor: UIColor.orange.cgColor)
    filtGraphVc.addTrace(dataSource: selectedResponseDataSource)
  }

  func setupEqControlsView() {
    let sb = UIStoryboard(name: "Main", bundle: nil)
    eqVc = sb.instantiateViewController(withIdentifier: "EqControls") as! EqViewController
    eqVc.unitIdx = unitIdx
    addChild(eqVc)
    eqVc.auDelegate = self
    
    let subview = eqVc.view!
    subview.translatesAutoresizingMaskIntoConstraints = false
    view.addSubview(subview)
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

