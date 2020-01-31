//
//  TestGraph2.hpp
//  CoreDspTest
//
//  Created by Andrew Voelkel on 1/28/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#pragma once

#include "Sources.hpp"
#include "Mixers.hpp"
#include "BiquadChain.hpp"
#include "MiscBlocks.hpp"

#include <iostream>

namespace DspBlocks {
  
  using namespace CoefGen;
  
  // create a subgraph, just so we can test heirarchy
  
  struct EqBlock : GraphBase {
    GainMute gainBlock;
    BiquadChainBlock eqBlock;
    const string GetClassName() override { return "Eq Subgraph"; }
    
    EqBlock(DesignContext& dc) : GraphBase(dc,1,1)  {
      Connect(this, &eqBlock);
      Connect(&eqBlock, &gainBlock);
      Connect(&gainBlock, this);
    }
  };
  
  struct EqMasterGraph : TopLevelGraph {
    DesignContext dc;
    Splitter splitter;
    EqBlock leftEq;
    EqBlock rightEq;
    EqBlock masterEq;
    NullSource nullSrc;
    Joiner joiner;
    TwoInputMixer mixer;
    
    EqMasterGraph() :
    TopLevelGraph(dc,1,1), leftEq(dc), rightEq(dc), masterEq(dc), splitter(2), joiner(2) {
      try {
        Connect((GraphBase*)this, &splitter);
        Connect(&splitter, 0, &leftEq);
        Connect(&splitter, 1, &rightEq);
        Connect(&leftEq, &mixer, 0);
        Connect(&rightEq, &mixer, 1);
        Connect(&mixer, &masterEq);
        Connect(&masterEq, &joiner, 0);
        Connect(&nullSrc, &joiner, 1);
        Connect(&joiner, this);
        auto eqSpecs = vector<EqSpec>(1);
        eqSpecs[0].dB = 12;
        eqSpecs[0].enabled = true;
        eqSpecs[0].type = EqSpec::hiShelf;
        eqSpecs[0].frequency = 3000;
        eqSpecs[0].order = 1;
        leftEq.eqBlock.SetEqSpecs(eqSpecs);
        eqSpecs[0].type = EqSpec::loShelf;
        eqSpecs[0].frequency = 200;
        eqSpecs[0].enabled = true;
        rightEq.eqBlock.SetEqSpecs(eqSpecs);
        CompleteComposition();
        dc.Describe(true);
      } catch (DspError err) {
        cout << err.msg;
      }
    }
    
    void Init(WireSpec ws) {
      try {
        PrepareForOperation(ws);
        printf("\n");
        dc.Describe(true);
        // initialize blocks
        InitBlocks();
      } catch (DspError err) {
        cout << err.msg;
      }
    }
  };
  
}

