//
//  EqAU.m
//  SimpleEQ
//
//  Created by Andrew Voelkel on 4/3/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#import "EqAU.h"
#include "EqDsp.hpp"
#include <algorithm>

using namespace std;

@implementation EqAU

DspBlocks::EqDsp* _DSP = nil;

- (void*)getDsp:(int*)bufSize {
  *bufSize = 128;
  return (void*)(new DspBlocks::EqDsp);
}

- (void)dealloc {
  if (_DSP != NULL) delete(_DSP);
}

-(void)setFrequency:(float)frequency atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].frequency = frequency;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(float)getFrequencyAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].frequency;
}

- (void*)dsp { return (void*)_DSP; }

@end
