//
//  EqDsp.hpp
//  SimpleEQ
//
//  Created by Andrew Voelkel on 4/3/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#pragma once

#include "BiquadChain.hpp"
#include "Mixers.hpp"
#include "MiscDsp.hpp"
#include "MiscBlocks.hpp"
#include "json.hpp"

namespace DspBlocks {
  
  struct EqBlock : GraphBase {
    GainMute gainBlock;
    BiquadChainBlock eqBlock;
    const string GetClassName() override { return "Eq Subgraph"; }
    
    // since we create a vector of these below, and because this is a subgraph,
    // we need a customized initialization scheme
    
    void ConnectSubBlocks() {
      Connect(this, &eqBlock);
      Connect(&eqBlock, &gainBlock);
      Connect(&gainBlock, this);
    }
    
    EqBlock(DesignContext& dc) : eqBlock(6), GraphBase(dc,1,1) {}
    
  };
  
  struct EqDsp : TopLevelGraph {
    DesignContext dc;
    vector<EqBlock> EQs;
    Splitter splitter;
    TwoInputMixer mixer;
    Joiner joiner;
    WireSpec wireSpec;
    vector<AWV::FftAnalyzer*> analyzers;
    vector<LevelDetect> detectors;
    
    EqDsp() :
    TopLevelGraph(dc,1,1), splitter(2), joiner(2) {
      try {
        EQs = vector<EqBlock>(2, EqBlock(dc));
        for (auto& eq : EQs) { eq.ConnectSubBlocks(); }
        detectors = vector<LevelDetect>(4);
        Connect(this, &splitter);
        Connect(&splitter, 0, &EQs[0]);
        Connect(&splitter, 1, &EQs[1]);
        Connect(&splitter, 0, &detectors[0]);
        Connect(&splitter, 1, &detectors[1]);
        Connect(&EQs[0], &mixer, 0);
        Connect(&EQs[1], &mixer, 1);
        Connect(&EQs[0], &detectors[2]);
        Connect(&EQs[1], &detectors[3]);
        Connect(&mixer, &joiner, 0);
        Connect(&mixer, &joiner, 1);
        Connect(&joiner, this);

        // this stuff is just to get this working with an inactive AU
        analyzers = vector<AWV::FftAnalyzer*>(2, new AWV::FftAnalyzer(13)); // 2 << 13 = 16384
        for (auto a : analyzers) {
          a->SetFrequencies(10, 10000, 300);
          a->SetSampleRate(44100);
        }
        wireSpec = WireSpec(2, 44100, 128);
        
      } catch (DspError err) {
        cout << err.msg;
      }
    }
    
    ~EqDsp() {
      for (auto a: analyzers) {
        if (a != nullptr) delete(a);
      }
    }
    
    void Init(WireSpec ws) {
      try {
        PrepareForOperation(ws, true);
        printf("\n");
        dc.Describe();
        // initialize blocks
        InitBlocks();
        for (auto a : analyzers) { a->SetSampleRate(ws.sampleRate); }
      } catch (DspError err) {
        cout << err.msg;
      }
    }
        
    vector<float>& GetFrequencyResponse(int idx) {
      auto eqSpecs = EQs[idx].eqBlock.GetEqSpecs();
      BiquadChain bq(eqSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      return analyzers[idx]->GetFrequencyResponse(ir);
    }
    
    vector<float>& GetFrequencyResponse(int idx, int stage) {
      auto eqSpecs = EQs[idx].eqBlock.GetEqSpecs();
      auto stageSpecs = vector<EqSpec>(1, eqSpecs[stage]);
      BiquadChain bq(stageSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      return analyzers[idx]->GetFrequencyResponse(ir);
    }
    
  };
  
}
