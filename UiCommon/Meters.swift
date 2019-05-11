//
//  Meters.swift
//  UiTools
//
//  Created by Andrew Voelkel on 3/10/17.
//  Copyright © 2017 Andrew Voelkel. All rights reserved.
//

import UIKit

@IBDesignable public class BasicVuMeter: UIControl {
  
  @IBInspectable var minDb : Int = -100;
  
  @IBInspectable var Color : UIColor = UIColor.blue {
    didSet { setNeedsDisplay() }
  }
  
  var percent : Float = 0
  
  public func SetEnvelope(_ newVal: Float) {
    let db = 20 * log10(newVal)
    percent = Float((Float(-minDb) + db) / Float(-minDb));
    setNeedsDisplay()
  }

  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }
  
  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }
  
func commonInit() {
    layer.borderWidth = 1
  }
  
  open override func layoutSubviews() {
    super.layoutSubviews()
    
  }
  
  override public func draw(_ rect: CGRect) {
    let cont = UIGraphicsGetCurrentContext()
    cont?.setFillColor(Color.cgColor)
    let height = bounds.height * CGFloat(percent)
    let rect = CGRect(x:0, y:bounds.height - height, width:bounds.width, height:height)
    cont?.fill(rect)
  }

}

