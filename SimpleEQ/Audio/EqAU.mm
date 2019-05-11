//
//  EqAU.m
//  SimpleEQ
//
//  Created by Andrew Voelkel on 4/3/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#import "EqAU.h"
#include "EqDsp.hpp"
#include "MiscDsp.hpp"
#include <algorithm>

using namespace std;

@implementation EqAU

DspBlocks::EqDsp* _DSP = nullptr;

-(void*)getDsp:(int*)bufSize {
  *bufSize = 128;
  if (_DSP == nil) {
    _DSP = new DspBlocks::EqDsp;
  }
  return (void*)_DSP;
}

-(void)dealloc {
  if (_DSP != nullptr) delete(_DSP);
}

-(int)getNStages { return _DSP->masterEq.eqBlock.GetNStages(); }

-(void)setEnabled:(bool)enable atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].enabled = enable;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(bool)getEnabledAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].enabled;
}

-(void)setType:(int)type atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].type = (CoefGen::EqSpec::Type)type;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(int)getTypeAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].type;
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

-(void)setDb:(float)dB atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].dB = dB;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(float)getDbAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].dB;
}

-(void)setQ:(float)Q atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].Q = Q;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(float)getQAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].Q;
}

-(void)setOrder:(int)order atIndex:(int)idx {
  vector<CoefGen::EqSpec> specs = _DSP->masterEq.eqBlock.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  specs[idx].order = order;
  _DSP->masterEq.eqBlock.SetEqSpecs(specs);
}

-(int)getOrderAtIndex:(int)idx {
  return _DSP->masterEq.eqBlock.GetEqSpecs()[idx].order;
}

-(float*)getImpulseResponse:(int)len {
  auto ir = _DSP->masterEq.eqBlock.GetImpulseResponse(len);
  return &ir[0];
}

-(float*)getImpulseResponseForStage:(int)len stage:(int)stage {
  auto ir = _DSP->masterEq.eqBlock.GetImpulseResponse(len);
  return &ir[0];
}

-(void)setupFftAnalyzerForMin:(float)min max:(float)max
                  nFreqPoints:(int)nFreqPoints {
  _DSP->analyzer->SetFrequencies(min, max, nFreqPoints);
}

-(float*)getFrequencyPoints {
  float* freqs = &_DSP->analyzer->GetFrequencies()[0];
  return freqs;
}

-(float*)getFreqResponse {
  float* resp = &_DSP->GetFrequencyResponse()[0];
  return resp;
}

-(float*)getFreqResponseforStage:(int)stage {
  return &_DSP->GetFrequencyResponse(stage)[0];
}

-(float)getInputLevelForChannel:(int)chan {
  return _DSP->inputLevelDetect.GetLevel(chan);
}

-(float)getOutputLevelForChannel:(int)chan {
  return _DSP->outputLevelDetect.GetLevel(chan);
}


- (void*)dsp { return (void*)_DSP; }

@end
