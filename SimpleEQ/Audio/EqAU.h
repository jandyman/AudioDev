//
//  EqAU.h
//  SimpleEQ
//
//  Created by Andrew Voelkel on 4/3/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#pragma once

#import <Foundation/Foundation.h>
#import <AudioToolbox/AudioToolbox.h>
#import <AudioUnit/AudioUnit.h>
#import "AudioUnitBase.h"

@interface EqAU : AudioUnitBase

-(void*)getDsp:(int*)bufSize;

-(int)getNStages;

-(void)setFrequency:(float)frequency atIndex:(int)idx;
-(float)getFrequencyAtIndex:(int)idx;


@end

#ifdef __cplusplus

#import "EqDsp.hpp"

#endif
