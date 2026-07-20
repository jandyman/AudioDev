
#pragma once

#include "GenericDsp.hpp"
#include <Accelerate/Accelerate.h>
#include "math.h"
#include "MiscDsp.hpp"

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
  
  struct NInputMixer : DspBlockSingleWireSpec {
    int nInputs = 0;

    NInputMixer(int nInputs) : DspBlockSingleWireSpec(nInputs,1) { this->nInputs = nInputs; }

    const string GetClassName() override { return "Two Input Mixer"; }

    void Process() override {
      int nChannels = outputPins[0].wire->wireSpec.nChannels;
      int bufSize = outputPins[0].wire->wireSpec.bufSize;
      float** inBufs[nChannels];
      for (int i=0; i < nChannels; i++) {
        inBufs[i] = inputPins[i].wire->buffers;
      }
      float** outBufs = outputPins[0].wire->buffers;
      for (int ch = 0; ch < nChannels; ch++) {
        if (nInputs >= 2) {
          vDSP_vadd(inBufs[0][ch], 1, inBufs[1][ch], 1, outBufs[ch], 1, bufSize);
        } else {
          std::copy(inBufs[0][ch], inBufs[0][ch] + bufSize, outBufs[ch]);
        }
        for (int in = 2; in < nInputs; in++) {
          vDSP_vadd(inBufs[in][ch], 1, outBufs[ch], 1, outBufs[ch], 1, bufSize);
        }
      }
    }

  };

  struct GainMute : DspBlockSingleWireSpec {
  
    GainMute() : DspBlockSingleWireSpec(1,1) { }
    
    const string GetClassName() override { return "Gain / Mute"; }
    
  private:
    float gain;
    float _gain;
    bool enable = true;
    bool inPhase = true;
    
    void UpdateGain() {
      _gain = enable ? gain : 0;
      if (!inPhase) _gain = -_gain;
    }
    
  public:
    void SetGain(float gain) { this->gain = gain; UpdateGain(); }
    void SetGainDb(float gainDb) { this->gain = AWV::Math::DbToLin(gainDb); UpdateGain(); }
    void SetEnable(bool enable) { this->enable = enable; UpdateGain(); }
    void SetInPhase(bool inPhase) { this->inPhase = inPhase; UpdateGain(); }
    float Gain() { return gain; }
    float GainDb() { return AWV::Math::LinToDb(gain); }
    bool Enable() { return enable; }
    bool InPhase() { return inPhase; }
    
    void Init() override {
      UpdateGain();
    }
    
    void Process() override {
      int nChannels = outputPins[0].wire->wireSpec.nChannels;
      int bufSize = outputPins[0].wire->wireSpec.bufSize;
      float** inBufs = inputPins[0].wire->buffers;
      float** outBufs = outputPins[0].wire->buffers;
      for (int ch = 0; ch < nChannels; ch++) {
        vDSP_vsmul(inBufs[ch], 1, &_gain, outBufs[ch], 1, bufSize);
      }
    }

    
  };
    
  }
