
#pragma once

#include "GenericDsp.hpp"
#include <Accelerate/Accelerate.h>
#include "math.h"

namespace DspBlocks {

  struct TwoInputMixer : DspBlockSingleWireSpec {

    TwoInputMixer() : DspBlockSingleWireSpec(2,1) { }

    const string GetClassName() override { return "Two Input Mixer"; }

    void Process() override {
      int nChannels = outputPins[0].wire->wireSpec.nChannels;
      int bufSize = outputPins[0].wire->wireSpec.bufSize;
      float** in1Bufs = inputPins[0].wire->buffers;
      float** in2Bufs = inputPins[1].wire->buffers;
      float** outBufs = outputPins[0].wire->buffers;
      for (int ch = 0; ch < nChannels; ch++) {
        vDSP_vadd(in1Bufs[ch], 1, in2Bufs[ch], 1, outBufs[ch], 1, bufSize);
      }
    }

  };
  
  struct GainMute : DspBlockSingleWireSpec {
  
    GainMute() : DspBlockSingleWireSpec(1,1) { }
    
    const string GetClassName() override { return "Gain / Mute"; }
    
  private:
    float gain;
    float gainDb = 0;
    bool enable = true;
    bool inPhase = true;
    
    void UpdateGain() {
      gain = enable ? pow(10, gainDb / 20) : 0;
      if (!inPhase) gain = -gain;
    }
    
    void Init() override {
      UpdateGain();
    }
    
  public:
    void SetGainDb(float gainDb) { this->gainDb = gainDb; UpdateGain(); }
    void SetEnable(bool enable) { this->enable = enable; UpdateGain(); }
    void SetInPhase(bool inPhase) { this->inPhase = inPhase; UpdateGain(); }
    
    void Process() override {
      int nChannels = outputPins[0].wire->wireSpec.nChannels;
      int bufSize = outputPins[0].wire->wireSpec.bufSize;
      float** inBufs = inputPins[0].wire->buffers;
      float** outBufs = outputPins[0].wire->buffers;
      for (int ch = 0; ch < nChannels; ch++) {
        vDSP_vsmul(inBufs[ch], 1, &gain, outBufs[ch], 1, bufSize);
      }
    }

    
  };
    
  }
