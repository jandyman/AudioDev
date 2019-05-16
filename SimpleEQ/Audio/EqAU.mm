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
#include <functional>

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

-(int)getNStages:(int)unit {
  return _DSP->EQs[unit].eqBlock.GetNStages();
}

using CoefGen::EqSpec;

void setEqParam(int unit, int idx, function<void(EqSpec&)> func) {
  auto& block = _DSP->EQs[unit].eqBlock;
  vector<CoefGen::EqSpec> specs = block.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  func(specs[idx]);
  block.SetEqSpecs(specs);
}

template <typename T> T getEqParam(int unit, int idx, function<T(EqSpec&)> func) {
  auto& block = _DSP->EQs[unit].eqBlock;
  vector<CoefGen::EqSpec> specs = block.GetEqSpecs();
  assert(idx >= 0 && idx < specs.size());
  return func(specs[idx]);
}

-(void)setEnabled:(int)unit enable:(bool)enable stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.enabled = enable; } );
}

-(bool)getEnabled:(int)unit stage:(int)idx {
  return getEqParam<bool>(unit, idx, [](EqSpec spec) { return spec.enabled; } );
}

-(void)setType:(int)unit type:(int)type stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.type = (CoefGen::EqSpec::Type)type; } );
}

-(int)getType:(int)unit stage:(int)idx {
  return getEqParam<int>(unit, idx, [](EqSpec spec) { return spec.type; } );
}

-(void)setFrequency:(int)unit frequency:(float)freq stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.frequency = freq; });
}

-(float)getFrequency:(int)unit stage:(int)idx {
  return getEqParam<float>(unit, idx, [](EqSpec spec) { return spec.frequency; });
}

-(void)setDb:(int)unit dB:(float)dB stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.dB = dB; });
}

-(float)getDb:(int)unit stage:(int)idx {
  return getEqParam<float>(unit, idx, [](EqSpec spec) { return spec.dB; });
}

-(void)setQ:(int)unit Q:(float)Q stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.Q = Q; });
}

-(float)getQ:(int)unit stage:(int)idx {
  return getEqParam<float>(unit, idx, [](EqSpec spec) { return spec.Q; });
}

-(void)setOrder:(int)unit order:(int)order stage:(int)idx {
  setEqParam(unit, idx, [&](EqSpec& spec) { spec.order = order; });
}

-(float)getOrder:(int)unit stage:(int)idx {
  return getEqParam<int>(unit, idx, [](EqSpec spec) { return spec.order; });
}

-(float*)getImpulseResponse:(int)unit len:(int)len {
  auto ir = _DSP->EQs[unit].eqBlock.GetImpulseResponse(len);
  return &ir[0];
}

-(float*)getImpulseResponse:(int)unit len:(int)len stage:(int)stage {
  auto ir = _DSP->EQs[unit].eqBlock.GetImpulseResponse(len);
  return &ir[0];
}

-(void)setupFftAnalyzer:(int)unit min:(float)min max:(float)max
                  nFreqPoints:(int)nFreqPoints {
  _DSP->analyzers[unit]->SetFrequencies(min, max, nFreqPoints);
}

-(float*)getFrequencyPoints:(int)unit {
  float* freqs = &_DSP->analyzers[unit]->GetFrequencies()[0];
  return freqs;
}

-(float*)getFreqResponse:(int)unit {
  float* resp = &_DSP->GetFrequencyResponse(unit)[0];
  return resp;
}

-(float*)getFreqResponse:(int)unit stage:(int)stage {
  return &_DSP->GetFrequencyResponse(stage)[0];
}

-(float)getInputLevelForChannel:(int)chan {
  auto detector = (chan == 0) ? _DSP->detectors[0] : _DSP->detectors[1];
  return detector.GetLevel(chan);
}

-(float)getOutputLevelForChannel:(int)chan {
  auto detector = (chan == 0) ? _DSP->detectors[2] : _DSP->detectors[3];
  return detector.GetLevel(chan);
}

- (void*)dsp { return (void*)_DSP; }

@end
