//
//  FreqGraph.swift
//  GraphTest
//
//  Created by Andrew Voelkel on 6/4/18.
//  Copyright © 2018 Setpoint Medical. All rights reserved.
//

import Cocoa
import CorePlot

class FreqGraph: NSView {
  
  var hostingView: CPTGraphHostingView!

  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }

  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }

  func commonInit() {
    self.wantsLayer = true
    hostingView = CPTGraphHostingView()
    addSubview(hostingView)
    SetupResponseGraph()
  }

  open override func layout() {
    super.layout()
    let size = self.frame.size
    hostingView.setFrameSize(size)
  }

  override func prepareForInterfaceBuilder() {
  }

  override func awakeFromNib() {
  }

  var graph : CPTXYGraph!
  var dataSources = [FreqResponseDataSource]()

  func SetupResponseGraph() {
    // Create a CPTGraph object and add to hostView
    graph = CPTXYGraph(frame: hostingView.bounds)
    hostingView.hostedGraph = graph;

    // Set padding
    graph.paddingBottom = 0.0
    graph.paddingLeft = 0.0
    graph.paddingTop = 0.0
    graph.paddingRight = 0.0
    graph.plotAreaFrame!.paddingTop = 10.0
    graph.plotAreaFrame!.paddingBottom = 60.0
    graph.plotAreaFrame!.paddingRight = 20.0
    graph.plotAreaFrame!.paddingLeft = 70.0

    let axisSet = graph.axisSet as! CPTXYAxisSet
    // set axes' title, labels and their text styles
    let textStyle = CPTMutableTextStyle()
    textStyle.fontName = "Helvetica"
    textStyle.fontSize = 14;
    let lineStyle = CPTMutableLineStyle()
    let dotlineStyle = CPTMutableLineStyle()
    dotlineStyle.dashPattern = [1, 4]
    let ydotlineStyle = CPTMutableLineStyle()
    ydotlineStyle.dashPattern = [4, 4]

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
    axisSet.yAxis!.title = "Amplitude (dB)"
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
    axisSet.xAxis!.orthogonalPosition = -20
    // Get the (default) plotspace from the graph so we can set its x/y ranges
    let plotSpace = graph.defaultPlotSpace as! CPTXYPlotSpace
    // Note that these CPTPlotRange are defined by START and LENGTH (not START and END) !!
    plotSpace.yRange = CPTPlotRange(location: -20, length: 40)
    plotSpace.xRange = CPTPlotRange(location: 10, length: 19990)
    plotSpace.xScaleType = CPTScaleType.log

  }

  func addTrace(dataSource: FreqResponseDataSource,
                lineColor: CPTColor = CPTColor.black(),
                title: String? = nil) {
    let plot = CPTScatterPlot(frame: CGRect.zero)
    plot.dataSource = dataSource
    plot.title = title
    let ls1 = CPTMutableLineStyle(style: plot.dataLineStyle)
    ls1.lineColor = lineColor
    ls1.lineWidth = 2.0
    plot.dataLineStyle = ls1
    graph.add(plot, to: graph.defaultPlotSpace)
    dataSources.append(dataSource)
    graph.reloadData()
  }

  var yTitle : String? {
    get { return (graph.axisSet as! CPTXYAxisSet).yAxis!.title }
    set(value) { (graph.axisSet as! CPTXYAxisSet).yAxis!.title = value }
  }

  var xTitle : String? {
    get { return (graph.axisSet as! CPTXYAxisSet).xAxis!.title }
    set(value) { (graph.axisSet as! CPTXYAxisSet).xAxis!.title = value }
  }


}

class FreqResponseDataSource : NSObject, CPTPlotDataSource {

  var nPoints: UInt = 500
  var minVal = 10.0
  var maxVal = 20000.0
  var analyzer : FftAnalyzer?
  var enable = true
  var sampleRate: Float = 44100

  init(analyzer: FftAnalyzer, sampleRate: Float) {
    self.analyzer = analyzer; self.sampleRate = sampleRate
  }

  func numberOfRecords(for plotnumberOfRecords : CPTPlot) -> UInt {
    return enable ? nPoints : 0
  }

  func map(_ value: Float) -> Float {
    let minLog = Float(log10(minVal))
    let maxLog = Float(log10(maxVal))
    let exp = minLog + (maxLog - minLog) * value
    return pow(10, exp);
  }

  func getX(_ idx: Float) -> Float {
    let mapIn = idx / Float(nPoints)
    return map(mapIn)
  }

  func getY(_ idx: Float) -> Float {
    let freq = getX(idx)
    return analyzer!.GetDb(freq: freq, SR: sampleRate)
  }

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
