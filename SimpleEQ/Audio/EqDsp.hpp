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


namespace DspBlocks {
  
  struct EqBlock : GraphBase {
    GainMute gainBlock;
    BiquadChainBlock eqBlock;
    const string GetClassName() override { return "Eq Subgraph"; }
    
    EqBlock(DesignContext& dc) : eqBlock(6), GraphBase(dc,1,1)  {
      Connect(this, &eqBlock);
      Connect(&eqBlock, &gainBlock);
      Connect(&gainBlock, this);
    }
  };
  
  struct EqDsp : TopLevelGraph {
    DesignContext dc;
    EqBlock masterEq;
    WireSpec wireSpec;
    AWV::FftAnalyzer* analyzer = nullptr;
    
    EqDsp() :
    TopLevelGraph(dc,1,1), masterEq(dc) {
      try {
        Connect(this, &masterEq);
        Connect(&masterEq, this);
      } catch (DspError err) {
        cout << err.msg;
      }
    }
    
    ~EqDsp() {
      if (analyzer != nullptr) delete(analyzer);
    }
    
    void Init(WireSpec ws) {
      try {
        analyzer = new AWV::FftAnalyzer(16384);
        PrepareForOperation(ws, true);
        printf("\n");
        dc.Describe();
        // initialize blocks
        InitBlocks();
      } catch (DspError err) {
        cout << err.msg;
      }
    }
    
    vector<float> GetFrequencyResponse() {
      auto eqSpecs = masterEq.eqBlock.GetEqSpecs();
      BiquadChain bq(eqSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      vector<float>& response = analyzer->GetFrequencyResponse(ir);
      return response;
    }
    
    vector<float> GetFrequencyResponse(int stage) {
      auto eqSpecs = masterEq.eqBlock.GetEqSpecs();
      auto stageSpecs = vector<EqSpec>(1, eqSpecs[0]);
      BiquadChain bq(stageSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      vector<float>& response = analyzer->GetFrequencyResponse(ir);
      return response;
    }
    
  };
}
