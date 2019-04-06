
#pragma once

#include "GenericDsp.hpp"
#include <math.h>
#include <string.h>

using namespace std;

namespace DspBlocks {
  
  struct SineGen : DspBlockSingleWireSpec {
    float frequency;
    float amplitude = 1.0;
    float phase = 0;

    SineGen() : DspBlockSingleWireSpec(0,1) {}
    
    SineGen(float frequency) : SineGen() {
      this->frequency = frequency;
    }

    const string GetClassName() override { return "SineGen"; }

    void Init() override { phase = 0; }
    
    void Process() override {
      auto pin = outputPins[0];
      WireSpec& ws = pin.wire->wireSpec;
      for (int samp=0; samp < ws.bufSize; samp++) {
        pin.wire->buffers[0][samp] = sin(phase * 2 * M_PI) * amplitude;
        phase += frequency / ws.sampleRate;
      }
    }
    
  };
  
  struct Impulse : DspBlockSingleWireSpec {
    float amplitude = 1.0;
    bool sampZero = true;
    
    Impulse() : DspBlockSingleWireSpec(0,1) {}
    
    const string GetClassName() override { return "Impulse"; }
    
    void Process() override {
      auto pin = outputPins[0];
      WireSpec& ws = pin.wire->wireSpec;
      memset(&pin.wire->buffers[0][0], 0, sizeof(float) * ws.bufSize);
      if (sampZero) { pin.wire->buffers[0][0] = 1.0; sampZero = false; }
    }
  };

  struct Probe : DspBlockSingleWireSpec {
    float **buffers = nullptr;  // copy data to this buffer during operation
    Probe() : DspBlockSingleWireSpec(1,0) {}
    
    const string GetClassName() { return "Probe"; }

    void Init() {
      freeBuffers();
      buffers = inputPins[0].wire->wireSpec.AllocateBuffers();
    }

    void freeBuffers() {
      if (buffers != nullptr) {
        for (int i = 0; i < inputPins[0].wire->wireSpec.nChannels; i++) {
          if (buffers[i] != nullptr) delete buffers[i];
        }
        delete buffers;
      }
    }

    void Process() {
      float** pinBuf = inputPins[0].wire->buffers;
      auto& ws = inputPins[0].wire->wireSpec;
      for (int ch=0 ; ch < ws.nChannels; ch++) {
        copy(&pinBuf[ch][0], &pinBuf[ch][ws.bufSize], buffers[ch]);
      }
    }

    float** getBuffers() { return buffers; }

  };

}


