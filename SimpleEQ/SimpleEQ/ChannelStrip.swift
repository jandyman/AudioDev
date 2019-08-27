//
//  ChannelStrip.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 8/24/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import Foundation

@IBDesignable class ChannelStrip: UIControl {

    var slider = VerticalSlider()
    var inMeter = BasicVuMeter()
    var outMeter = BasicVuMeter()
    var muteSwitch = LabeledSwitch()
    var phaseSwitch = LabeledSwitch()

    func commonInit() {
        let views = [slider, inMeter, outMeter, muteSwitch, phaseSwitch]
        for view in views {
            addSubview(view)
            view.backgroundColor = UIColor.white
        }
        muteSwitch.text = "M"
        phaseSwitch.text = "P"
    }

    required public init?(coder aDecoder: NSCoder) {
        super.init(coder: aDecoder)
        commonInit()
    }

    override init(frame: CGRect) {
        super.init(frame: frame)
        commonInit()
    }


    open override func layoutSubviews() {
        super.layoutSubviews()

        let margin = CGFloat(15)
        let width = bounds.width
        let buttonHeight = width
        var height = bounds.height
        height = height - 2 * buttonHeight - 4 * margin
        let sliderHeight = height * 0.5
        height = height - sliderHeight
        let meterHeight = height * 0.5
        var y = CGFloat(0)

        inMeter.frame = CGRect(x: 0, y: y, width: width, height: meterHeight)
        y = y + meterHeight + margin
        outMeter.frame = CGRect(x: 0, y: y, width: width, height: meterHeight)
        y = y + meterHeight + margin
        muteSwitch.frame = CGRect(x: 0, y: y, width: width, height: width)
        y = y + width + margin
        phaseSwitch.frame = CGRect(x: 0, y: y, width: width, height: width)
        slider.frame = CGRect(x: 0,
                              y: bounds.height - sliderHeight,
                              width: width,
                              height: sliderHeight)
    }

}

