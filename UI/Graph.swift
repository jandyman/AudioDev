//
//  Graph.swift
//  GraphTest
//
//  Created by Andrew Voelkel on 6/3/18.
//  Copyright © 2018 Setpoint Medical. All rights reserved.
//

import Cocoa
import CorePlot

@IBDesignable class Graph: NSView {

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

  var yTitle : String? {
    get { return (graph.axisSet as! CPTXYAxisSet).yAxis!.title }
    set(value) { (graph.axisSet as! CPTXYAxisSet).yAxis!.title = value }
  }

  var xTitle : String? {
    get { return (graph.axisSet as! CPTXYAxisSet).xAxis!.title }
    set(value) { (graph.axisSet as! CPTXYAxisSet).xAxis!.title = value }
  }

  var xLimits : (Double, Double)? = nil
  var yLimits : (Double, Double)? = nil

  func SetupResponseGraph() {
    // Create a CPTGraph object and add to hostView
    graph = CPTXYGraph(frame: hostingView.bounds)
    hostingView.hostedGraph = graph;

    // Set padding
    graph.paddingBottom = 0.0
    graph.paddingLeft = 0.0
    graph.paddingTop = 0.0
    graph.paddingRight = 0.0
    graph.plotAreaFrame!.paddingTop = 20.0
    graph.plotAreaFrame!.paddingBottom = 65.0
    graph.plotAreaFrame!.paddingRight = 20.0
    graph.plotAreaFrame!.paddingLeft = 80.0

    let axisSet = graph.axisSet as! CPTXYAxisSet
    // set axes' title, labels and their text styles
    let textStyle = CPTMutableTextStyle()
    textStyle.fontName = "Helvetica"
    textStyle.fontSize = 14;
    let lineStyle = CPTMutableLineStyle()
    let dotlineStyle = CPTMutableLineStyle()
    dotlineStyle.dashPattern = [2, 4]
    let ydotlineStyle = CPTMutableLineStyle()
    ydotlineStyle.dashPattern = [4, 4]

    lineStyle.lineWidth = 1.0
    graph.axisSet!.borderLineStyle = lineStyle

    // X Axis
    axisSet.xAxis!.title = ""
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

    // Y Axis
    axisSet.yAxis!.title = ""
    axisSet.yAxis!.titleTextStyle = textStyle
    axisSet.yAxis!.titleOffset = 50.0
    axisSet.yAxis!.labelTextStyle = textStyle;
    axisSet.yAxis!.labelOffset = 3.0
    axisSet.yAxis!.axisLineStyle = lineStyle;
    axisSet.yAxis!.majorTickLineStyle = lineStyle;
    axisSet.yAxis!.labelingPolicy = CPTAxisLabelingPolicy.automatic
    axisSet.yAxis!.majorGridLineStyle = lineStyle;
    axisSet.yAxis!.minorGridLineStyle = dotlineStyle;

    let plotSpace = graph.defaultPlotSpace as! CPTXYPlotSpace
    plotSpace.yRange = CPTPlotRange(location: -100, length: 100)


  }

  func addLegend() {
    graph.legend = CPTLegend(graph: graph)
    graph.legend!.fill = CPTFill(color: CPTColor.white())
    graph.legendAnchor = CPTRectAnchor.topLeft
    graph.legend?.numberOfColumns = 1
    graph.legendDisplacement = CGPoint(x: 90, y: -30)
  }

  func addTrace(dataSource: CPTPlotDataSource,
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
    graph.reloadData()

    let plotSpace = graph.defaultPlotSpace as! CPTXYPlotSpace
    if let xLimits = self.xLimits {
      let loc = NSNumber(value: xLimits.0)
      let rng = NSNumber(value: xLimits.1 - xLimits.0)
      plotSpace.xRange = CPTPlotRange(location: loc, length: rng)
    } else {
      plotSpace.scale(toFit: graph.allPlots(), for: CPTCoordinate.X)
    }
    if let yLimits = self.yLimits {
      let loc = NSNumber(value: yLimits.0)
      let rng = NSNumber(value: yLimits.1 - yLimits.0)
      plotSpace.yRange = CPTPlotRange(location: loc, length: rng)
    } else {
      plotSpace.scale(toFit: graph.allPlots(), for: CPTCoordinate.Y)
    }
    let axisSet = graph.axisSet as! CPTXYAxisSet
    axisSet.xAxis!.orthogonalPosition = plotSpace.yRange.minLimit
  }

}
