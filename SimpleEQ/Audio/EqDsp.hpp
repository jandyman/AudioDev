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
    template<typename T> using vector = std::vector<T>;
    std::ostream& cout = std::cout;
    
    DesignContext dc;
    vector<EqBlock> EQs;
    Splitter splitter;
    TwoInputMixer mixer;
    Joiner joiner;
    vector<AWV::FftAnalyzer*> analyzers;
    vector<LevelDetect> detectors;
    
    bool inPhase = true;
    float rightGainDb = 0;
    float masterGainDb = 0;
    bool leftEnable = true;
    bool rightEnable = true;
    
    EqDsp() :
    TopLevelGraph(dc,1,1), splitter(2), joiner(2) {
      try {
        // EQ[0] = left Eq, EQ[1] = right Eq
        EQs = vector<EqBlock>(2, EqBlock(dc));
        for (auto& eq : EQs) { eq.ConnectSubBlocks(); }
        // 0 = left in, 1 = right in, 2 = left EQ, 3 = right EQ, 4 = master
        detectors = vector<LevelDetect>(5);
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
        Connect(&mixer, &detectors[4]);
        Connect(&joiner, this);

        // this stuff is just to get this working with an inactive AU
        analyzers = vector<AWV::FftAnalyzer*>(2, new AWV::FftAnalyzer(13)); // 2 << 13 = 16384
        for (auto a : analyzers) {
          a->SetFrequencies(10, 10000, 300);
          a->SetSampleRate(44100);
        }
        wireSpec = WireSpec(2, 44100, 128);

        designContext.Describe(false);
        CompleteComposition();
        
      } catch (DspError err) {
        cout << err.msg;
        throw err;
      }
    }
    
    ~EqDsp() { for (auto a: analyzers) { delete(a); }}
    
    void UpdateGains() {
      EQs[0].gainBlock.SetEnable(leftEnable);
      EQs[1].gainBlock.SetEnable(rightEnable);
      EQs[1].gainBlock.SetInPhase(inPhase);
      EQs[1].gainBlock.SetGainDb(rightGainDb + masterGainDb);
      EQs[0].gainBlock.SetGainDb(masterGainDb);
    }
    
    void Init(WireSpec ws) {
      try {
        PrepareForOperation(ws);
        printf("\n");
        dc.Describe(true);
        // initialize blocks
        InitBlocks();
        UpdateGains();
        for (auto a : analyzers) { a->SetSampleRate(ws.sampleRate); }
      } catch (DspError err) {
        cout << err.msg;
        throw err;
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
      auto stageSpecs = vector<CoefGen::EqSpec>(1, eqSpecs[stage]);
      BiquadChain bq(stageSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      return analyzers[idx]->GetFrequencyResponse(ir);
    }
    
  };


  struct nEqBlock : GraphBase {
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

    nEqBlock(DesignContext& dc) : eqBlock(6), GraphBase(dc,1,1) {}

  };

  struct nEqDsp : TopLevelGraph {
    template<typename T> using vector = std::vector<T>;
    std::ostream& cout = std::cout;

    DesignContext dc;
    vector<EqBlock> EQs;
    Splitter splitter;
    NInputMixer mixer;
    Joiner joiner;
    vector<AWV::FftAnalyzer*> analyzers;
    vector<LevelDetect> detectors;
    int nChannels;

    nEqDsp(int nChannels) :
    TopLevelGraph(dc,1,1), splitter(2), joiner(2), mixer(nChannels) { }

    void Compose(int nChannels) {
      try {
        this->nChannels = nChannels;
        EQs = vector<EqBlock>(nChannels, EqBlock(dc));
        for (auto& eq : EQs) { eq.ConnectSubBlocks(); }
        // n inputs, n outputs, 1 master
        detectors = vector<LevelDetect>(2 * nChannels + 1);
        Connect(this, &splitter);
        for (int i=0; i < nChannels; i++) {
          Connect(&splitter, i, &EQs[i]);
          Connect(&splitter, i, &detectors[i]);
          Connect(&EQs[i], &mixer, i);
          Connect(&EQs[i], &detectors[i + nChannels]);
        }
        Connect(&mixer, &joiner, 0);
        Connect(&mixer, &joiner, 1);
        Connect(&mixer, &detectors[4]);
        Connect(&joiner, this);

        // This stuff is just to get this working with an inactive AU. The UI may still want to
        // display a frequency graph with HW disconnected.
        analyzers = vector<AWV::FftAnalyzer*>(nChannels, new AWV::FftAnalyzer(13)); // 2 << 13 = 16384
        for (auto a : analyzers) {
          a->SetFrequencies(10, 10000, 300);
          a->SetSampleRate(44100);
        }
        wireSpec = WireSpec(nChannels, 44100, 128);

        CompleteComposition();

      } catch (DspError err) {
        cout << err.msg;
        throw err;
      }
    }

    ~nEqDsp() { for (auto a: analyzers) { delete(a); }}

    void Init(WireSpec ws) override {
      try {
        PrepareForOperation(ws);
        InitBlocks();
        for (auto a : analyzers) { a->SetSampleRate(ws.sampleRate); }
      } catch (DspError err) {
        cout << err.msg;
        throw err;
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
      auto stageSpecs = vector<CoefGen::EqSpec>(1, eqSpecs[stage]);
      BiquadChain bq(stageSpecs, wireSpec.sampleRate);
      vector<float> ir = bq.impulseResponse(16384);
      return analyzers[idx]->GetFrequencyResponse(ir);
    }

  };

}

