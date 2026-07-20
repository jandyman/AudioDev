//
//  MiscBlocks.hpp
//  CoreDspTest
//
//  Created by Andrew Voelkel on 1/29/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#pragma once

#include "GenericDsp.hpp"
#include <Accelerate/Accelerate.h>
#include <vector>
#include "math.h"

namespace DspBlocks {
  
  struct Splitter : DspBase {
    const string GetClassName() override { return "Splitter"; }
    Splitter(int nOutputPins) : DspBase(1, nOutputPins) {}
    
    WireSpec outputWs;
    
    bool UpdateWireSpecs() override {
      bool did_something = false;
      auto& inputPin = inputPins[0];
      if (inputPin.wire->wireSpec.nChannels != outputPins.size()) {
        throw new DspError("Splitter: n Input Channels != n Output Ports");
      }
      auto ws = inputPin.wire->wireSpec;
      auto newWs = WireSpec(1, ws.sampleRate, ws.bufSize);
      if (!ws.IsEmpty()) {
        did_something = SetWireSpec(outputPins, newWs);
      } else {
        auto ws = GetFirstWireSpec(outputPins);
        if (!ws.IsEmpty()) {
          SetWireSpec(outputPins, ws);
          ws.nChannels = inputPin.wire->wireSpec.nChannels;
          inputPin.wire->wireSpec.nChannels = ws.nChannels;
        }
      }
      return did_something;
    }
    
    void Process() override {
      int nChannels = inputPins[0].wire->NChannels();
      int bufSize = outputPins[0].wire->BufSize();
      float** inbufs = inputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        float* inbuf = inbufs[ch];
        float* outbuf = outputPins[ch].wire->buffers[0];
        std::copy(inbuf, inbuf + bufSize, outbuf);
      }
    }
      
  };
  
  struct Joiner : DspBase {
    const string GetClassName() override { return "Joiner"; }
    Joiner(int nOutputPins) : DspBase(nOutputPins, 1) {}
    
    bool UpdateWireSpecs() override {
      bool did_something = false;
      auto& outputPin = outputPins[0];
      if (outputPin.wire->wireSpec.nChannels != inputPins.size()) {
        throw new DspError("Splitter: n Output Channels != n Input Ports");
      }
      auto ws = outputPin.wire->wireSpec;
      auto newWs = WireSpec(1, ws.sampleRate, ws.bufSize);
      if (!ws.IsEmpty()) {
        did_something = SetWireSpec(inputPins, newWs);
      } else {
        auto ws = GetFirstWireSpec(inputPins);
        if (!ws.IsEmpty()) {
          SetWireSpec(inputPins, ws);
          ws.nChannels = outputPin.wire->wireSpec.nChannels;
          outputPin.wire->wireSpec.nChannels = ws.nChannels;
        }
      }
      return did_something;
    }
    
    void Process() override {
      int nChannels = outputPins[0].wire->NChannels();
      int bufSize = outputPins[0].wire->BufSize();
      float** outbufs = outputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        float* inbuf = inputPins[ch].wire->buffers[0];
        float* outbuf = outbufs[ch];
        std::copy(inbuf, inbuf + bufSize, outbuf);
      }
    }

  };
  
  struct NullSink : DspBlockSingleWireSpec {
    const string GetClassName() override { return "Null Sink"; }
    NullSink() : DspBlockSingleWireSpec(1, 0) {}
  };
  
  struct NullSource : DspBlockSingleWireSpec {
    const string GetClassName() override { return "Null Source"; }
    NullSource() : DspBlockSingleWireSpec(0, 1) {}

    void Process() override {
      int nChannels = outputPins[0].wire->NChannels();
      int bufSize = outputPins[0].wire->BufSize();
      float** outbufs = outputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        std::fill(outbufs[0], outbufs[0]+bufSize, 0);
      }
    }

  };
  
}

#include "Dynamics.hpp"

namespace DspBlocks {
  
  struct LevelDetect : DspBlockSingleWireSpec {
    template<typename T> using vector = std::vector<T>;
    using AttRel = DSP::AttRel;

    vector<AttRel> attRels;
    const string GetClassName() override { return "Level Detect"; }
    LevelDetect() : DspBlockSingleWireSpec(1, 0) {}

    void Init() override {
      float fs = sharedWireSpec.sampleRate;
      attRels = vector<AttRel>(sharedWireSpec.nChannels, AttRel(fs, .005, .3));
    }
    
    float GetLevel(int chan) { return attRels[chan].Y; }
    
    void Process() override {
      int nChannels = inputPins[0].wire->NChannels();
      int bufSize = inputPins[0].wire->BufSize();
      float** inbufs = inputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        attRels[ch].Run(inbufs[ch], bufSize);
      }
    }
    
  };
  
}
