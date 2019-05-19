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

-(int)getNStages:(int)unit;

-(void)setEnabled:(int)unit enable:(bool)enable stage:(int)idx;
-(bool)getEnabled:(int)unit stage:(int)idx;

-(void)setType:(int)unitIdx type:(int)type stage:(int)idx;
-(int)getType:(int)unitIdx stage:(int)idx;

-(void)setFrequency:(int)unit frequency:(float)frequency stage:(int)idx;
-(float)getFrequency:(int)unitIdx stage:(int)idx;

-(void)setDb:(int)unit dB:(float)dB stage:(int)idx;
-(float)getDb:(int)unit stage:(int)idx;

-(void)setQ:(int)unit Q:(float)Q stage:(int)idx;
-(float)getQ:(int)unit stage:(int)idx;

-(void)setOrder:(int)unit order:(int)order stage:(int)idx;
-(int)getOrder:(int)unit stage:(int)idx;

-(float*)getImpulseResponse:(int)unit len:(int)len;
-(float*)getImpulseResponse:(int)unit len:(int)len stage:(int)stage;

-(void)setupFftAnalyzer:(int)unit min:(float)min max:(float)max
                  nFreqPoints:(int)nFreqPoints;;

-(float*)getFrequencyPoints:(int)unit;
-(float*)getFreqResponse:(int)unit;
-(float*)getFreqResponse:(int)unit stage:(int)stage;

-(float)getInputLevelForChannel:(int)chan;
-(float)getOutputLevelForChannel:(int)chan;

@end

#ifdef __cplusplus

#import "EqDsp.hpp"

#endif
