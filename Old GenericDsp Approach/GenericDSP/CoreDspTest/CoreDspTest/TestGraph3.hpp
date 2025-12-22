
#pragma once

#include "GenericDsp.hpp"
#include "Sources.hpp"
#include "Mixers.hpp"
#include "BiquadChain.hpp"
#include "MiscBlocks.hpp"

#include <iostream>

using namespace DspBlocks;
using namespace CoefGen;

// create a subgraph, just so we can test heirarchy

struct EqBlock : GraphBase {
  GainMute gainBlock;
  BiquadChainBlock eqBlock;
  const string GetClassName() override { return "Eq Subgraph"; }
  
  EqBlock(DesignContext& dc) : GraphBase(dc,1,1) {
    Connect(this, &eqBlock);
    Connect(&eqBlock, &gainBlock);
    Connect(&gainBlock, this);
  }
};

struct EqMasterGraph : TopLevelGraph {
  EqBlock masterEq;
  WireSpec wireSpec;
  
  EqMasterGraph(DesignContext& dc, WireSpec ws) :
  TopLevelGraph(dc,1,1), masterEq(dc) {
    wireSpec = ws;
    
    try {
      Connect(this, &masterEq);
      Connect(&masterEq, this);
      
      auto eqSpecs = vector<EqSpec>(1);
      eqSpecs[0].dB = 18;
      masterEq.eqBlock.SetEqSpec(eqSpecs);
      
      PrepareForOperation(wireSpec, true);
      printf("\n");
      dc.Describe();
      
      // initialize blocks
      InitBlocks();
      
    } catch (DspError err) {
      cout << err.msg;
    }
  }
  
};

