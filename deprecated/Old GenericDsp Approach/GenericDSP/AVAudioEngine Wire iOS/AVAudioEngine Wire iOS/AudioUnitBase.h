//
//  AKAudioUnitBase.h
//  AudioKit
//
//  Created by Andrew Voelkel, revision history on GitHub.
//  Copyright © 2018 AudioKit. All rights reserved.
//

#pragma once

#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <AudioToolbox/AudioToolbox.h>

@interface ThruAudioUnit : AUAudioUnit

// These three properties are what are in the Apple example code.

@property AUAudioUnitBus *outputBus;
@property AUAudioUnitBus *inputBus;
@property AUAudioUnitBusArray *inputBusArray;
@property AUAudioUnitBusArray *outputBusArray;

@end


