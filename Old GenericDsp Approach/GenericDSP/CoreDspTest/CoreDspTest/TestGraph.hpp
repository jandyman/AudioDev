//
// Created by Andrew Voelkel on 8/27/18.
//

#pragma once

#include "GenericDsp.hpp"
#include "Sources.hpp"
#include "Mixers.hpp"

#include <iostream>

using namespace DspBlocks;

// create a subgraph, just so we can test heirarchy

struct SubGraph : GraphBase {
  TwoInputMixer mixer;
  
  SubGraph(DesignContext& dc) : GraphBase(dc, 2,1) {
    Connect(this, &mixer);
    Connect(this, 1, &mixer, 1);
    Connect(&mixer, this);
  }
  
  const string GetClassName() override { return "SubGraph"; }
  
};

struct Graph : TopLevelGraph {
  SubGraph subGraph;
  SineGen osc1;
  WireSpec wireSpec;

  Graph(DesignContext& dc, WireSpec ws) : TopLevelGraph(dc,1,1), subGraph(dc) {
    wireSpec = ws;

    try {

      // design time
      osc1.frequency = 100;
      osc1.amplitude = .3;
      Connect(this, &subGraph, 1);
      Connect(&osc1, &subGraph);
      Connect(&subGraph, this);
      
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
