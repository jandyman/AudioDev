//
//  LabeledSwitch.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 5/31/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

@IBDesignable class LabeledSwitch : UIControl {
  
  @IBInspectable var onColor : UIColor = UIColor.blue {
    didSet { setNeedsDisplay() }
  }
  
  @IBInspectable var text : String = "foo" {
    didSet {
      setNeedsLayout()
    }
  }
  
  private var offColor : UIColor?
  private var label = UILabel()

  var isOn : Bool = false {
    didSet {
      if oldValue != isOn {
        sendActions(for: UIControl.Event.valueChanged)
      }
      setNeedsLayout()
    }
  }
  

  override init(frame: CGRect) {
    super.init(frame: frame)
    commonInit()
  }
  
  required public init?(coder aDecoder: NSCoder) {
    super.init(coder: aDecoder)
    commonInit()
  }
  
  private func commonInit() {
    addTarget(self, action: #selector(buttonPressed(_:)), for: UIControl.Event.touchUpInside)
    addSubview(label)
    setNeedsLayout()
  }
  
  // background color is not set on init in IB
  
  override var backgroundColor: UIColor? {
    didSet {
      offColor = backgroundColor
    }
  }
  
  @objc private func buttonPressed(_ sender: AnyObject?) {
    isOn = !isOn
  }
  
  override func layoutSubviews() {
    super.layoutSubviews()
    label.text = text
    label.frame = CGRect(x: 0, y: 0, width: frame.width, height: frame.height)
    label.layer.borderWidth = 1
    label.textAlignment = .center
    label.layer.borderColor = UIColor.black.cgColor
    label.layer.cornerRadius = 5
    label.backgroundColor = isOn ? onColor : offColor!
    let font = UIFont.systemFont(ofSize: 12)
    let size = UIFont.bestFittingFontSize(for: text, in: frame,
                                          fontDescriptor: font.fontDescriptor)
    let newFont = UIFont.systemFont(ofSize: size * 0.85)
    label.font = newFont
  }

  
}
