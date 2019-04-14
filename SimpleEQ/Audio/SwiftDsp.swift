//
//  SwiftDsp.swift
//  SwiftUi
//
//  Created by Andrew Voelkel on 10/20/15.
//  Copyright © 2015 Andrew Voelkel. All rights reserved.
//

// The only code which belongs here is code which is not platform-portable. All platform
// portable DSP code should be in C++ and therefore not here.

import Foundation
import Accelerate

enum FilterType : String, Codable {
  case loShelf
  case peaking
  case hiShelf
  case loPass
  case hiPass
}

class FilterSpec : Codable {
  var Enabled = false
  var `Type` : FilterType = .peaking
  var Order : Int = 1
  var Frequency : Double = 1000
  var Db : Double = 0
  var Q : Double = 1
}

class GainSpecs : Codable {
  var GainDb : Double = 0
  var Enabled = false

  static func == (l: GainSpecs, r: GainSpecs) -> Bool {
    return (l.GainDb == r.GainDb) && (l.Enabled == r.Enabled)
  }
}

/**
 Performs FFT analysis by calling vDSP functions. Assume that the response being analyzed are
 impulse reponses, and therefore applies a half hanning window before performing FFTs. The 
 length of the FFT must be selected when the FftAnalyzer is created.
 */

class FftAnalyzer {

  let log2len : UInt
  let intLen : UInt
  var realp : [Float]
  var imagp : [Float]
  var fftOut : DSPSplitComplex
  let fftSetup: FFTSetup

  init(log2len: UInt) {
    self.log2len = log2len
    intLen = 1 << log2len
    realp = [Float](repeating: 0, count: Int(intLen))
    imagp = [Float](repeating: 0, count: Int(intLen))
    fftOut = DSPSplitComplex(realp: &realp, imagp: &imagp)
    fftSetup = vDSP_create_fftsetup(UInt(log2len), Int32(kFFTRadix2))!
  }

  func DoFft (_ resp : inout [Float]) {
    resp = SwiftDsp.WindowAndAdjustLength(x: resp, len: Int(intLen))
    // do the actual FFT
    RealFFT(fftSetup, Int32(log2len), &resp, &fftOut)
  }

  func GetDb(freq: Float, SR: Float) -> Float {
    let idx = Int(freq / (SR / 2.0) * Float(intLen/2+1))
    var absv : Float = 0
    switch idx {
    case 0:
      absv = abs(fftOut.realp[0])
    case Int(intLen):
      absv = abs(fftOut.imagp[0])
    default:
      let realp = fftOut.realp[idx]
      let imagp = fftOut.imagp[idx]
      absv = sqrt(pow(realp,2) + pow(imagp,2))
    }
    let db = 20 * log10(absv);
    return Float(db);
  }

}

class SwiftDsp {

  class func WindowAndAdjustLength(x: [Float], len: Int, applyWindow: Bool = false) -> [Float] {
    var retval = (x.count > len) ? Array(x[0..<len]) : x  // trim first
    // window the IR with the second half of a hann window
    var win = [Float](repeating: 0, count: retval.count)
    vDSP_hann_window(&win, UInt(retval.count*2), Int32(vDSP_HALF_WINDOW))
    var winptr = UnsafePointer<Float>(win)
    winptr += Int(retval.count) - 1
    vDSP_vmul(retval, 1, winptr, -1, &retval, 1, UInt(retval.count))
    // pad if necessary
    if (retval.count < len) {
      let pad = [Float](repeating: 0, count: len - retval.count)
      retval += pad
    }
    return retval
  }

  class func PrintTimeElapsed(_ title:String, operation:()->()) {
    let startTime = CFAbsoluteTimeGetCurrent()
    operation()
    let timeElapsed = CFAbsoluteTimeGetCurrent() - startTime
    print("Time elapsed for \(title): \(timeElapsed) s")
  }

  class func maxDiffDb(x: [Float], y: [Float]) -> Float {
    assert(x.count == y.count)
    var maxDiff : Float = 0.0
    for i in 0...x.count-1 { maxDiff = max(maxDiff, abs(x[i]-y[i])) }
    return 20 * log10(maxDiff)
  }
  
}

