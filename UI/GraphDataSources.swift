//
//  PointDataSource.swift
//  GraphTest
//
//  Created by Andrew Voelkel on 5/16/18.
//  Copyright © 2018 Setpoint Medical. All rights reserved.
//

import Foundation
import CorePlot

struct Point {
    var x = 0.0
    var y = 0.0
}

class PointDataSet : NSObject, CPTPlotDataSource {

    var points : [Point]!

    init(points: [Point]) { self.points = points }

    func numberOfRecords(for plotnumberOfRecords : CPTPlot) -> UInt {
        return UInt(points.count)
    }

    func double(for plot: CPTPlot, field fieldEnum: UInt, record idx: UInt) -> Double {
        // This method is actually called twice per point in the plot, one for the X and one for the Y value
        if fieldEnum == UInt(CPTScatterPlotField.X.rawValue) {
            return points[Int(idx)].x
        } else {
            return points[Int(idx)].y
        }
    }

}

class YValuesDataSet : NSObject, CPTPlotDataSource {
  
  var yValues : [Double]!
  
  init(yValues: [Double]) { self.yValues = yValues }
  
  func numberOfRecords(for plotnumberOfRecords : CPTPlot) -> UInt {
    return UInt(yValues.count)
  }
  
  func double(for plot: CPTPlot, field fieldEnum: UInt, record idx: UInt) -> Double {
    // This method is actually called twice per point in the plot, one for the X and one for the Y value
    if fieldEnum == UInt(CPTScatterPlotField.X.rawValue) {
      return Double(idx)
    } else {
      return yValues[Int(idx)]
    }
  }
  
}



