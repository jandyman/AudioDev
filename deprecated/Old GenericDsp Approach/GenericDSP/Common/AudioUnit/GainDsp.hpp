//
//  GainDsp.hpp
//  Temp AUV3
//
//  Created by Andrew Voelkel on 11/7/18.
//  Copyright © 2018 Andrew Voelkel. All rights reserved.
//

#pragma once

#include "Accelerate/Accelerate.h"
#include "GenericDsp.hpp"
#include "Mixers.hpp"

namespace DspBlocks {

class GainDsp : TopLevelGraph {
  DesignContext dc;
  WireSpec wireSpec;
  GainMute gainBlock;
  
public:
  float gain;
  
  GainDsp() : TopLevelGraph(dc,1,1) {
    Connect(this, &gainBlock);
    Connect(&gainBlock, this);
  }
  
  void init(int nChannels, double sampleRate, int bufSize) {
    
    try {
      wireSpec = WireSpec(nChannels, sampleRate, bufSize);
      PrepareForOperation(wireSpec, true);
      InitBlocks();
    } catch (DspError err) {
      std::cout << err.msg;
    }
  }
    
};
  
}






