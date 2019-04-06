//
//  ResponseGraph.m
//  SP Prunable
//
//  Created by Andrew Voelkel on 10/15/15.
//  Copyright © 2015 imect. All rights reserved.
//

#import <Foundation/Foundation.h>
#import "ResponseGraph.h"

CPTGraph* SetupResponseGraph(CGRect bounds) {
  
  // Create a CPTGraph object and add to hostView
  CPTGraph* graph = [[CPTXYGraph alloc] initWithFrame:bounds];
  
  // Set padding
  graph.plotAreaFrame.paddingTop = 20.0f;
  graph.plotAreaFrame.paddingBottom = 70.0f;
  graph.plotAreaFrame.paddingRight = 20.0f;
  graph.plotAreaFrame.paddingLeft = 70.0f;
  
  CPTXYAxisSet *axisSet = (CPTXYAxisSet *)graph.axisSet;
  
  // set axes' title, labels and their text styles
  CPTMutableTextStyle *textStyle = [CPTMutableTextStyle textStyle];
  textStyle.fontName = @"Helvetica";
  textStyle.fontSize = 14;
  CPTMutableLineStyle *lineStyle = [CPTMutableLineStyle lineStyle];
  CPTMutableLineStyle *dotlineStyle = [CPTMutableLineStyle lineStyle];
  dotlineStyle.dashPattern = [NSArray arrayWithObjects:
                              [NSDecimalNumber numberWithInt:1],
                              [NSDecimalNumber numberWithInt:4],
                              nil];
  lineStyle.lineWidth = 1.0f;
  
  // X Axis
  axisSet.xAxis.title = @"Frequency";
  axisSet.xAxis.titleTextStyle = textStyle;
  axisSet.xAxis.titleOffset = 30.0f;
  axisSet.xAxis.labelTextStyle = textStyle;
  axisSet.xAxis.labelOffset = 3.0f;
  axisSet.xAxis.axisLineStyle = lineStyle;
  axisSet.xAxis.majorTickLineStyle = lineStyle;
  axisSet.xAxis.labelingPolicy = CPTAxisLabelingPolicyAutomatic;
  axisSet.xAxis.majorGridLineStyle = lineStyle;
  axisSet.xAxis.minorGridLineStyle = dotlineStyle;
  axisSet.xAxis.majorTickLength = 7.0f;
  axisSet.xAxis.minorTickLineStyle = lineStyle;
  axisSet.xAxis.minorTicksPerInterval = 10;
  axisSet.xAxis.minorTickLength = 5.0f;
  NSNumberFormatter *numberFormatter = [[NSNumberFormatter alloc] init];
  [numberFormatter setPositiveFormat:@"0"];
  axisSet.xAxis.labelFormatter = numberFormatter;
  
  // Y Axis
  axisSet.yAxis.title = @"Amplitude";
  axisSet.yAxis.titleTextStyle = textStyle;
  axisSet.yAxis.labelTextStyle = textStyle;
  axisSet.yAxis.titleOffset = 40.0f;
  axisSet.yAxis.labelOffset = 3.0f;
  axisSet.yAxis.axisLineStyle = lineStyle;
  axisSet.yAxis.minorGridLineStyle = dotlineStyle;
  axisSet.yAxis.majorGridLineStyle = lineStyle;
  axisSet.yAxis.majorTickLineStyle = lineStyle;
  axisSet.yAxis.majorIntervalLength = [NSNumber numberWithFloat:5.0];
  axisSet.yAxis.majorTickLength = 7.0f;
  axisSet.yAxis.minorTickLineStyle = lineStyle;
  axisSet.yAxis.minorTicksPerInterval = 3;
  axisSet.yAxis.minorTickLength = 5.0f;
  axisSet.xAxis.orthogonalPosition = [[NSNumber alloc] initWithInt:-20];
  
  // Get the (default) plotspace from the graph so we can set its x/y ranges
  CPTXYPlotSpace *plotSpace = (CPTXYPlotSpace *) graph.defaultPlotSpace;
  
  // Note that these CPTPlotRange are defined by START and LENGTH (not START and END) !!
  [plotSpace setYRange: [CPTPlotRange plotRangeWithLocation:[NSNumber numberWithFloat:-20] length:[NSNumber numberWithFloat:40]]];
  [plotSpace setXRange: [CPTPlotRange plotRangeWithLocation:[NSNumber numberWithFloat:10] length:[NSNumber numberWithFloat:10000]]];
  plotSpace.xScaleType = CPTScaleTypeLog;
  
  // Create the plot (we do not define actual x/y values yet, these will be supplied by the datasource...)
  CPTScatterPlot* plot = [[CPTScatterPlot alloc] initWithFrame:CGRectZero];
  
  // Finally, add the created plot to the default plot space of the CPTGraph object we created before
  [graph addPlot:plot toPlotSpace:graph.defaultPlotSpace];
  
  return graph;
  
}

