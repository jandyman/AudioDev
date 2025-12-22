//
//  GainDsp.m
//  Temp AUV3
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

#import "GainAU.h"
#include "GainDsp.hpp"

@implementation GainAU

DspBlocks::GainDsp* _DSP = nil;

- (void*)getDsp:(int*)bufSize {
  *bufSize = 128;
  return (void*)(new DspBlocks::GainDsp);
}

- (void)dealloc {
  if (_DSP != NULL) delete(_DSP);
}

- (float)gain { return _DSP->gain; }
- (void)setGain:(float)gain { _DSP->gain = gain; }

- (void*)dsp { return (void*)_DSP; }

@end






