//
//  FreqCombo.swift
//  FirstSwiftUi
//
//  Created by Andrew Voelkel on 7/30/15.
//  Copyright (c) 2015 Andrew Voelkel. All rights reserved.
//

import UIKit

//public extension UIView {
//  
//  /// Removes all constraints related to a view from the entire view hierarchy.
//  public func removeAllConstraints() {
//    var currentAncestorView: UIView? = superview
//    while currentAncestorView != nil {
//      for constraint in currentAncestorView!.constraints {
//        if constraint.firstItem === self || constraint.secondItem === self {
//          currentAncestorView?.removeConstraint(constraint)
//        }
//      }
//      currentAncestorView = currentAncestorView!.superview
//    }
//    removeConstraints(constraints)
//  }
//}


@IBDesignable open class ParamCombo: UIControl {
  
  @IBInspectable var minVal : Double = 10.0
  @IBInspectable var maxVal : Double = 10000.0
  @IBInspectable var numDigits : Int = 2
  
  @IBInspectable var nameWidth : CGFloat = 90
  @IBInspectable var valueWidth : CGFloat = 60
  @IBInspectable var margin : CGFloat = 3
  @IBInspectable var paramName : String = "" {
    didSet { paramLabel.text = paramName }
  }
  var paramLabel = UILabel()
  var slider = UISlider()
  var valueBox = UITextField()
  
  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }
  
  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }
  
  func sendValueChanged() {
    sendActions(for: UIControl.Event.valueChanged)
  }
  
  @objc func sliderChanged(_ sender: AnyObject?) {
    let mapped = map(Double(slider.value))
    let fmtStr = String(format: "%%1.%if", numDigits)
    let textString = String(format: fmtStr, mapped)
    if textString != valueBox.text {
      valueBox.text = textString
      sendValueChanged()
    }
  }
  
  @objc func textChanged(_ sender: AnyObject) {
    let fmt = NumberFormatter()
    let val = fmt.number(from: valueBox.text!);
    if (val == nil) {
      sliderChanged(nil)
    } else {
      slider.value = Float(invMap(val!.doubleValue))
      sliderChanged(nil)
    }
  }
  
  func map(_ value: Double) -> Double {
    return minVal + value * (maxVal - minVal)
  }
  
  func invMap(_ value: Double) -> Double {
    return (value - minVal)/(maxVal - minVal)
  }
  
  open var Value: Double {
    get {
      return map(Double(slider.value))
    }
    set(newVal) {
      if (newVal != Value) {
        slider.value = Float(invMap(newVal))
        sliderChanged(nil)
      }
    }
  }
  
  func commonInit() {
    slider.addTarget(self, action: #selector(sliderChanged(_:)), for: UIControl.Event.valueChanged)
    let mask: UIControl.Event = [UIControl.Event.editingDidEndOnExit, UIControl.Event.editingDidEnd];
    valueBox.addTarget(self, action: #selector(textChanged(_:)), for: mask)
    valueBox.keyboardType = UIKeyboardType.decimalPad
    valueBox.borderStyle = UITextField.BorderStyle.roundedRect
    valueBox.backgroundColor = UIColor.white
    valueBox.frame = CGRect(x: 10, y:10, width: 60, height: 30)
    valueBox.canBecomeFirstResponder
    valueBox.clearsOnBeginEditing = true
    valueBox.reloadInputViews()
    paramLabel.textAlignment = NSTextAlignment.center
    addSubview(valueBox)
    addSubview(slider)
    addSubview(paramLabel)
  }
  
  open override func layoutSubviews() {
    super.layoutSubviews()
    let height = CGFloat(30)
    let top = (bounds.height - height)/2
    let right = bounds.width - margin;
    let sliderWidth = bounds.width - valueWidth - nameWidth - (4 * margin)
    
    paramLabel.frame = CGRect(x: margin, y: top, width: nameWidth, height: height)
    valueBox.frame = CGRect(x: right - valueWidth, y: top, width: valueWidth, height: height)
    paramLabel.font = paramLabel.font?.withSize(CGFloat(bounds.height * 0.55))
    valueBox.font = valueBox.font?.withSize(CGFloat(bounds.height * 0.55))
    slider.frame = CGRect(x: 2 * margin + nameWidth, y: top, width: sliderWidth, height: height)
  }
  
}

@IBDesignable class LogParamCombo : ParamCombo {
  
  override func map(_ value: Double) -> Double {
    let minLog = log10(minVal)
    let maxLog = log10(maxVal)
    let exp = minLog + (maxLog - minLog) * value
    return pow(10, exp);
  }
  
  override func invMap(_ value: Double) -> Double {
    let minLog = log10(minVal)
    let maxLog = log10(maxVal)
    let tmp = log10(value)
    return (tmp - minLog)/(maxLog - minLog)
  }
}

@IBDesignable open class NumericCombo: UIControl {
  
  @IBInspectable var minimumValue : Double = 0
  @IBInspectable var maximumValue : Double = 100
  @IBInspectable var step : Double = 1
  
  @IBInspectable var nameWidth : CGFloat = 90
  @IBInspectable var valueWidth : CGFloat = 60
  @IBInspectable var unitsWidth : CGFloat = 60
  @IBInspectable var margin : CGFloat = 3
  @IBInspectable var paramName : String = "" {
    didSet { paramLabel.text = paramName }
  }
  @IBInspectable var unitsName : String = "" {
    didSet { unitsLabel.text = unitsName }
  }
  var paramLabel = UILabel()
  var unitsLabel = UILabel()
  var stepper = UIStepper()
  var valueBox = UITextField()
  
  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }
  
  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }
  
  func sendValueChanged() {
    sendActions(for: UIControl.Event.valueChanged)
  }
  
  @objc func stepperChanged(_ sender: AnyObject?) {
    let text = String(format: "%1.0f", stepper.value) // tmp kludge
    if text != valueBox.text {
      valueBox.text = text
      sendValueChanged()
    }
  }
  
  @objc func textChanged(_ sender: AnyObject) {
    let fmt = NumberFormatter()
    let val = fmt.number(from: valueBox.text!)
    // validate before setting this
    stepper.value = Double(truncating: val!)
    stepperChanged(stepper)
  }
  
  open var Value: Double {
    get {
      return stepper.value
    }
    set(newVal) {
      stepper.value = newVal
    }
  }
  
  func commonInit() {
    stepper.addTarget(self, action: #selector(stepperChanged(_:)), for: UIControl.Event.valueChanged)
    let mask: UIControl.Event = [UIControl.Event.editingDidEndOnExit, UIControl.Event.editingDidEnd];
    valueBox.addTarget(self, action: #selector(textChanged(_:)), for: mask)
    valueBox.keyboardType = UIKeyboardType.decimalPad
    valueBox.borderStyle = UITextField.BorderStyle.roundedRect
    valueBox.backgroundColor = UIColor.white
    valueBox.frame = CGRect(x: 10, y:10, width: 60, height: 30)
    valueBox.canBecomeFirstResponder
    valueBox.clearsOnBeginEditing = true
    valueBox.reloadInputViews()
    paramLabel.textAlignment = NSTextAlignment.center
    addSubview(valueBox)
    addSubview(stepper)
    addSubview(paramLabel)
    addSubview(unitsLabel)
  }
  
  open override func layoutSubviews() {
    // tmp kludge next four statements
    stepper.minimumValue = minimumValue
    stepper.maximumValue = maximumValue
    stepper.stepValue = step
    stepperChanged(stepper)
    super.layoutSubviews()
    let height = CGFloat(30)
    let top = (bounds.height - height)/2
    let right = bounds.width - margin;
    let sliderWidth = bounds.width - valueWidth - nameWidth - (4 * margin)
    
    paramLabel.frame = CGRect(x: margin, y: top, width: nameWidth, height: height)
    valueBox.frame = CGRect(x: right - valueWidth - unitsWidth - margin, y: top, width: valueWidth, height: height)
    unitsLabel.frame = CGRect(x: right - unitsWidth, y: top, width: unitsWidth, height: height)
    stepper.frame = CGRect(x: 2 * margin + nameWidth, y: top, width: sliderWidth, height: height)
  }
  
}

class CustomButton : UIButton {
  
  var IsPlus = false
  
  var Color : UIColor = UIColor.blue {
    didSet { setNeedsDisplay() }
  }
  
  override func draw(_ rect: CGRect) {
    
    let path = UIBezierPath(ovalIn: rect)
    Color.setFill()
    path.fill()
    
    let width = bounds.width
    let height = bounds.height
    
    let plusHeight: CGFloat = 3.0
    let plusWidth: CGFloat = min(width, height) * 0.6
    
    let plusPath = UIBezierPath()
    
    plusPath.lineWidth = plusHeight
    UIColor.white.setStroke()
    
    plusPath.move(to: CGPoint(x:width/2 - plusWidth/2, y:height/2))
    plusPath.addLine(to: CGPoint(x:width/2 + plusWidth/2, y:height/2))
    
    if (IsPlus) {
      plusPath.move(to: CGPoint(x:width/2, y:height/2 - plusWidth/2))
      plusPath.addLine(to: CGPoint(x:width/2, y:height/2 + plusWidth/2))
    }
    
    plusPath.stroke()
  }
  
}

@IBDesignable open class NumericCombo2: UIControl {
  
  @IBInspectable var valueWidth : CGFloat = 80
  @IBInspectable @objc var minimumValue : Double = 0
  @IBInspectable var maximumValue : Double = 100
  @IBInspectable var numDigits : Int = 0
  @IBInspectable var step : Double = 1
  @IBInspectable var Color : UIColor = UIColor.blue {
    didSet { btnUp.Color = Color; btnDown.Color = Color }
  }
  
  var Font: UIFont?
  
  let hmargin = 8
  
  let btnDown = CustomButton()
  let btnUp = CustomButton()
  let valueBox = UITextField()
  
  open var Value : Double = 0 {
    didSet {
      if Value > maximumValue { Value = maximumValue }
      if Value < minimumValue { Value = minimumValue }
      valueChanged()
      if (Value != oldValue) { sendValueChanged() }
    }
  }
  
  fileprivate var timer : Timer?
  fileprivate var timerHasFired : Bool = false
  fileprivate var btnDnPressed : Bool = false
  fileprivate var btnUpPressed : Bool = false
  
  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }
  
  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }
  
  fileprivate func StartTimer() {
    timerHasFired = false
    timer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(timerFired), userInfo: nil, repeats: true)
  }
  
  fileprivate func StopTimer() {
    if timer != nil { timer!.invalidate() }
  }
  
  @objc func timerFired() {
    timerHasFired = true
    if btnUpPressed { Value += 5 * step }
    if btnDnPressed { Value -= 5 * step }
    valueChanged()
  }
  
  func sendValueChanged() {
    sendActions(for: UIControl.Event.valueChanged)
  }
  
  @objc func btnUpTouchUp(_ sender: UIButton) {
    if !timerHasFired { Value += step }
    btnUpPressed = false
    StopTimer()
    valueChanged()
  }
  
  @objc func btnDnTouchUp(_ sender: UIButton) {
    if !timerHasFired { Value -= step }
    btnDnPressed = false
    StopTimer()
    valueChanged()
  }
  
  @objc func btnUpTouchDown(_ sender: UIButton) {
    btnUpPressed = true
    StartTimer()
  }
  
  @objc func btnDnTouchDown(_ sender: UIButton) {
    btnDnPressed = true
    StartTimer()
  }
  
  func valueChanged() {
    let fmtStr = String(format: "%%1.%if", numDigits)
    valueBox.text = String(format: fmtStr, Value)
  }
  
  @objc func textChanged(_ sender: AnyObject) {
    let fmt = NumberFormatter()
    let val = fmt.number(from: valueBox.text!)
    Value = Double(truncating: val!) // validate before setting this
    Value = max(Value, minimumValue)
    Value = min(Value, maximumValue)
  }
  
  func commonInit() {
    let mask: UIControl.Event = [UIControl.Event.editingDidEndOnExit, UIControl.Event.editingDidEnd];
    valueBox.addTarget(self, action: #selector(textChanged(_:)), for: mask)
    valueBox.borderStyle = UITextField.BorderStyle.roundedRect
    valueBox.backgroundColor = UIColor.white
    valueBox.frame = CGRect(x: 10, y:10, width: 60, height: 30)
    valueBox.clearsOnBeginEditing = true
    btnUp.IsPlus = true
    btnDown.Color = Color
    btnUp.Color = Color
    btnDown.addTarget(self, action: #selector(btnDnTouchDown(_:)), for: UIControl.Event.touchDown)
    btnDown.addTarget(self, action: #selector(btnDnTouchUp(_:)), for: UIControl.Event.touchUpInside)
    btnUp.addTarget(self, action: #selector(btnUpTouchDown(_:)), for: UIControl.Event.touchDown)
    btnUp.addTarget(self, action: #selector(btnUpTouchUp(_:)), for: UIControl.Event.touchUpInside)
    addSubview(valueBox)
    addSubview(btnUp)
    addSubview(btnDown)
  }
  
  open override func layoutSubviews() {
    // tmp kludge next four statements
    super.layoutSubviews()
    let buttonWidth = bounds.height
    let margin = CGFloat(hmargin)
    let valWidth = CGFloat(bounds.width - 2 * buttonWidth - 3 * margin);
    btnDown.frame = CGRect(x: 0, y: 0, width: buttonWidth, height: bounds.height)
    btnUp.frame = CGRect(x: buttonWidth + margin, y: 0, width: buttonWidth, height: bounds.height)
    valueBox.frame = CGRect(x: bounds.width - valWidth, y: 0, width: valWidth, height: bounds.height)
    Font = valueBox.font?.withSize(CGFloat(bounds.height * 0.8))
    valueBox.font = Font
  }
  
}

@IBDesignable class MultiIndicator : UIView {
  
  @IBInspectable var Margin : CGFloat = 1
  
  @IBInspectable var Color : UIColor = UIColor.blue {
    didSet { setNeedsDisplay() }
  }
  
  @IBInspectable var NumSegments : Int = 2 {
    didSet {
      if NumSegments < 1 { NumSegments = 1 }
      SegEnabled = [Bool](repeating: false, count: NumSegments)
      setNeedsDisplay()
    }
  }
  
  func SetEnable(_ idx : Int, enable : Bool) {
    SegEnabled![idx] = enable
    setNeedsDisplay()
  }
  
  var SegEnabled : [Bool]?
  
  override func draw(_ rect: CGRect) {
    let cont = UIGraphicsGetCurrentContext()
    cont?.setFillColor(Color.cgColor)
    let segWidth = bounds.width / CGFloat(NumSegments)
    for i in 0...NumSegments-1 {
      let xpos = CGFloat(i) * segWidth
      if (SegEnabled![i]) {
        let rect = CGRect(x: xpos + Margin, y: 0, width: segWidth - 2 * Margin, height: bounds.height)
        cont?.fill(rect)
      }
    }
    //    let path = UIBezierPath(ovalInRect: rect)
    //    Color.setFill()
    //    path.fill()
  }
  
  
  
  
}

