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

namespace DspBlocks {
  
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
  
  struct EqDsp : TopLevelGraph {
    DesignContext dc;
    EqBlock masterEq;
    
    EqDsp() :
    TopLevelGraph(dc,1,1), masterEq(dc) {
      try {
        Connect(this, &masterEq);
        Connect(&masterEq, this);
      } catch (DspError err) {
        cout << err.msg;
      }
    }
    
    void Init(WireSpec ws) {
      try {
        PrepareForOperation(ws, true);
        printf("\n");
        dc.Describe();
        // initialize blocks
        InitBlocks();
      } catch (DspError err) {
        cout << err.msg;
      }
    }
  };
}
