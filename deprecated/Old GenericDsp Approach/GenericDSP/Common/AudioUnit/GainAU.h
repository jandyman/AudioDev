//
//  GainAU.m
//  Temp AUV3
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

#pragma once

#import <Foundation/Foundation.h>
#import <AudioToolbox/AudioToolbox.h>
#import <AudioUnit/AudioUnit.h>
#import "AudioUnitBase.h"

@interface GainAU : AudioUnitBase

- (void*)getDsp:(int*)bufSize;

@property float gain;

@end

#ifdef __cplusplus

#import "GainDsp.hpp"

#endif
