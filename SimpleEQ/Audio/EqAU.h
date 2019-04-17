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

-(void)setEnabled:(bool)enable atIndex:(int)idx;
-(bool)getEnabledAtIndex:(int)idx;

-(void)setType:(int)frequency atIndex:(int)idx;
-(int)getTypeAtIndex:(int)idx;

-(void)setFrequency:(float)frequency atIndex:(int)idx;
-(float)getFrequencyAtIndex:(int)idx;

-(void)setDb:(float)dB atIndex:(int)idx;
-(float)getDbAtIndex:(int)idx;

-(void)setQ:(float)Q atIndex:(int)idx;
-(float)getQAtIndex:(int)idx;

-(void)setOrder:(int)order atIndex:(int)idx;
-(int)getOrderAtIndex:(int)idx;

-(float*)getImpulseResponse:(int)len;
-(float*)getImpulseResponseForStage:(int)len stage:(int)stage;

-(void)setupFftAnalyzerForMin:(float)min max:(float)max
                  nFreqPoints:(int)nFreqPoints;;

-(float*)getFreqResponse;
-(float*)getFreqResponseforStage:(int)stage;

@end

#ifdef __cplusplus

#import "EqDsp.hpp"

#endif
