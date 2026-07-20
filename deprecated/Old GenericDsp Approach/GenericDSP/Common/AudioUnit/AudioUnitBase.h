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

@interface AudioUnitBase : AUAudioUnit

/**
 This method should be overridden by the specific AU code, because it knows how to set up
 the DSP code. It should also be declared as public in the h file, but that causes problems
 because Swift wants to process as a bridging header, and it doesn't understand what a DSPBase
 is. I'm not sure the standard way to deal with this.
 */

-(void*)getDsp:(int*)bufSize;

// These three properties are what are in the Apple example code.

@property AUAudioUnitBus *outputBus;
@property AUAudioUnitBus *inputBus;
@property AUAudioUnitBusArray *inputBusArray;
@property AUAudioUnitBusArray *outputBusArray;

@end


