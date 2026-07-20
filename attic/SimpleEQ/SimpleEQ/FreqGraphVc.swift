//
//  FreqGraphVc.swift
//  SP Prunable
//
//  Created by Andrew Voelkel on 8/17/17.
//  Copyright © 2017 imect. All rights reserved.
//

import UIKit

class FreqGraphVc: UIViewController {
  
  @IBOutlet weak var HostingView: CPTGraphHostingView!
  
  var traces = [FiltDataSource]()
  
  override func viewDidLoad() {
    super.viewDidLoad()
    
    SetupResponseGraph()
    let nc = NotificationCenter.default
    nc.addObserver(forName:Notification.Name(rawValue:"AudioParamChange"),
                   object:nil, queue:nil,
                   using:UpdateUi)
    
  }
  
  override func didReceiveMemoryWarning() {
    super.didReceiveMemoryWarning()
    // Dispose of any resources that can be recreated.
  }
  
  func UpdateUi(notification: Notification? = nil) {
    HostingView.hostedGraph?.reloadData()
  }
  
  func addTrace(dataSource : FiltDataSource) {
    let graph = HostingView.hostedGraph
    let plot = CPTScatterPlot(frame: CGRect.zero)
    plot.dataSource = dataSource as CPTPlotDataSource
    plot.dataLineStyle = dataSource.lineStyle
    graph!.add(plot, to: graph!.defaultPlotSpace)
    traces.append(dataSource)
  }
  
  func SetupResponseGraph() {
    // Create a CPTGraph object and add to hostView
    let graph = CPTXYGraph(frame: HostingView.bounds)
    HostingView.hostedGraph = graph;
    
    // Set padding
    graph.paddingBottom = 0.0
    graph.paddingLeft = 0.0
    graph.paddingTop = 0.0
    graph.paddingRight = 0.0
    graph.plotAreaFrame!.paddingTop = 10.0
    graph.plotAreaFrame!.paddingBottom = 60.0
    graph.plotAreaFrame!.paddingRight = 20.0
    graph.plotAreaFrame!.paddingLeft = 60.0
    
    let axisSet = graph.axisSet as! CPTXYAxisSet
    // set axes' title, labels and their text styles
    let textStyle = CPTMutableTextStyle()
    textStyle.fontName = "Helvetica"
    textStyle.fontSize = 14;
    let lineStyle = CPTMutableLineStyle()
    let dotlineStyle = CPTMutableLineStyle()
    dotlineStyle.dashPattern = [1, 4]
    lineStyle.lineWidth = 1.0
    
    // X Axis
    axisSet.xAxis!.title = "Frequency"
    axisSet.xAxis!.titleTextStyle = textStyle
    axisSet.xAxis!.titleOffset = 30.0
    axisSet.xAxis!.labelTextStyle = textStyle;
    axisSet.xAxis!.labelOffset = 3.0
    axisSet.xAxis!.axisLineStyle = lineStyle;
    axisSet.xAxis!.majorTickLineStyle = lineStyle;
    axisSet.xAxis!.labelingPolicy = CPTAxisLabelingPolicy.automatic
    axisSet.xAxis!.majorGridLineStyle = lineStyle;
    axisSet.xAxis!.minorGridLineStyle = dotlineStyle;
    axisSet.xAxis!.majorTickLength = 7.0
    axisSet.xAxis!.minorTickLineStyle = lineStyle;
    axisSet.xAxis!.minorTicksPerInterval = 10
    axisSet.xAxis!.minorTickLength = 5.0
    let numberFormatter = NumberFormatter()
    numberFormatter.positiveFormat = "0"
    axisSet.xAxis!.labelFormatter = numberFormatter
    
    // Y Axis
    axisSet.yAxis!.title = "Amplitude"
    axisSet.yAxis!.titleTextStyle = textStyle
    axisSet.yAxis!.labelTextStyle = textStyle
    axisSet.yAxis!.titleOffset = 40.0
    axisSet.yAxis!.labelOffset = 3.0
    axisSet.yAxis!.axisLineStyle = lineStyle
    axisSet.yAxis!.minorGridLineStyle = dotlineStyle
    axisSet.yAxis!.majorGridLineStyle = lineStyle
    axisSet.yAxis!.majorTickLineStyle = lineStyle
    axisSet.yAxis!.majorIntervalLength = 5
    axisSet.yAxis!.majorTickLength = 7.0
    axisSet.yAxis!.minorTickLineStyle = lineStyle
    axisSet.yAxis!.minorTicksPerInterval = 3
    axisSet.yAxis!.minorTickLength = 5.0
    axisSet.xAxis!.orthogonalPosition = -30
    // Get the (default) plotspace from the graph so we can set its x/y ranges
    let plotSpace = graph.defaultPlotSpace as! CPTXYPlotSpace
    // Note that these CPTPlotRange are defined by START and LENGTH (not START and END) !!
    plotSpace.yRange = CPTPlotRange(location: -30, length: 60)
    plotSpace.xRange = CPTPlotRange(location: 10, length: 10000)
    plotSpace.xScaleType = CPTScaleType.log
    
  }
  
}

@objc class FiltDataSource : NSObject, CPTPlotDataSource {
  
  var lineStyle = CPTMutableLineStyle()
  
  var x : [Float]?
  var y : [Float]!

  // var analyzer : FftAnalyzer?
  var enable : Bool = true
  
  // init(analyzer: FftAnalyzer) { self.analyzer = analyzer }
  
  // This method is here because this class also functions as datasource for our graph
  // Therefore this class implements the CPTPlotDataSource protocol
  
  func numberOfRecords(for plotnumberOfRecords : CPTPlot) -> UInt {
    return enable && x != nil ? UInt(x!.count) : 0
  }
  
  func getX(_ idx: Float) -> Float { return x![Int(idx)] }
  func getY(_ idx: Float) -> Float { return y![Int(idx)] }
  
  // This method is here because this class also functions as datasource for our graph
  // Therefore this class implements the CPTPlotDataSource protocol
  
  func double(for plot: CPTPlot, field fieldEnum: UInt, record idx: UInt) -> Double {
    // This method is actually called twice per point in the plot, one for the X and one for the Y value
    if fieldEnum == UInt(CPTScatterPlotField.X.rawValue) {
      let x = getX(Float(idx))
      return Double(x)
    } else {
      let y = getY(Float(idx))
      return Double(y)
    }
  }
  
}

