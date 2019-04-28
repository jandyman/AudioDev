//
//  BiquadChain.hpp
//  Acoustify
//
//  Created by Andrew Voelkel on 6/2/18.
//  Copyright © 2018 Setpoint Medical. All rights reserved.
//

#pragma once

#include "GenericDsp.hpp"
#include "CoefGen.hpp"
#include <algorithm>

namespace DspBlocks {
  using namespace std;
  using namespace CoefGen;

  class BiquadChain {
    vDSP_biquad_Setup biquadSetup = NULL;
    vector<double> coefs;
    float *dlyBuf = NULL;
    int nStages = 0;
    
    void init(vector<double> coefs, uint nStages) {
      this->nStages = nStages;
      clearState();
      this->coefs = coefs;
      biquadSetup = vDSP_biquad_CreateSetup(&coefs[0], (vDSP_Length)nStages);
      dlyBuf = new float[4 * nStages]();
    }
    
    void clearState() {
      if (dlyBuf != NULL) { delete dlyBuf; dlyBuf = NULL; }
      if (biquadSetup != NULL) {
        vDSP_biquad_DestroySetup(biquadSetup);
        biquadSetup = NULL;
      }
    }
    
  public:
    
    BiquadChain(vector<double> coefs, int nStages) {
      init(coefs, nStages);
    }
    
    BiquadChain(vector<EqSpec> specs, double sampleRate) {
      vector<double> allCoefs(specs.size() * 5);
      int idx = 0, nStages = 0;
      for (auto spec: specs) {
        if (spec.needsCoefs()) {
          auto coefs = spec.Coefs(sampleRate);
          coefs.fillArray(&allCoefs[idx]); idx += 5;
          nStages++;
        }
      }
      if (nStages == 0) { // if no stages, build a dummy one
        Coefs coefs;
        coefs.c0 = 1.0;
        coefs.fillArray(&allCoefs[0]);
        nStages = 1;
      }
      init(allCoefs, nStages);
    }
    
    BiquadChain (const BiquadChain &obj) {
      nStages = obj.nStages;
      dlyBuf = new float[4 * nStages]();
      coefs = vector<double>(5 * nStages);
      coefs = obj.coefs;
      biquadSetup = vDSP_biquad_CreateSetup(&coefs[0], nStages);
    }
    
    ~BiquadChain() {
      clearState();
      
    }
    
    vector<float> impulseResponse(int len) {
      vector<float> impulse(len); impulse[0] = 1;
      vector<float> response(len, 0); 
      fill_n(dlyBuf, nStages * 4, 0);
      vDSP_biquad(biquadSetup, dlyBuf, &impulse[0], 1, &response[0], 1, len);
      return response;
    }
    
    // impulse response for a specific stage
    
    vector<float> impulseResponse(int len, int stage) {
      assert(stage >= 0 && stage < nStages);
      vector<float> impulse(len); impulse[0] = 1;
      vector<float> response(len, 0);
      fill_n(dlyBuf, 4, 0);
      auto setup = vDSP_biquad_CreateSetup(&coefs[stage * 5], 1);
      vDSP_biquad(setup, dlyBuf, &impulse[0], 1, &response[0], 1, len);
      vDSP_biquad_DestroySetup(setup);
      return response;
    }
    
    void process(float *input, float *output, int nSamps) {
      vDSP_biquad(biquadSetup, dlyBuf, input, 1, output, 1, nSamps);
    }
    
  };
  
  // --- Biquad Chain Block ---
  
  struct BiquadChainBlock : DspBlockSingleWireSpec {
    
  private:
    vector<BiquadChain>* biquadChains = nullptr;
    vector<BiquadChain>* newBiquadChains = nullptr;
    vector<EqSpec> eqSpecs;
    uint nChannels = 0;
    
  public:
    BiquadChainBlock(int nStages = 1) : DspBlockSingleWireSpec(1,1) {
      eqSpecs = vector<EqSpec>(nStages, EqSpec());
    }
    
    ~BiquadChainBlock() {
      delete biquadChains;
      if (biquadChains != newBiquadChains) {
        delete newBiquadChains;
      }
    }
    
    const string GetClassName() override { return "Biquad Chain"; }
    
    void Init() override {
      nChannels = outputPins[0].wire->NChannels();
      assertConnected();
      SetEqSpecs(eqSpecs);
    }
    
    void SetEqSpecs(vector<EqSpec> eqSpecs) {
      this->eqSpecs = eqSpecs;
      auto tmp = newBiquadChains;
      auto biquadChain = BiquadChain(eqSpecs, sharedWireSpec.sampleRate);
      newBiquadChains = new vector<BiquadChain>(nChannels, biquadChain);
      delete biquadChains;
      biquadChains = nullptr;
      delete tmp;
    }
    
    int GetNStages() { return eqSpecs.size(); }
    
    vector<EqSpec> GetEqSpecs() { return eqSpecs; }
    
    void assertConnected() {
      if (nChannels == 0) { throw new DspError("BiquadChainBlock not connected"); }
    }
    
    vector<float> GetImpulseResponse(int len) {
      BiquadChain bq(eqSpecs, sharedWireSpec.sampleRate);
      return bq.impulseResponse(len);
    }
    
    vector<float> GetImpulseResponse(int len, int stage) {
      vector<EqSpec> specs(1, eqSpecs[stage]);
      BiquadChain bq(eqSpecs, sharedWireSpec.sampleRate);
      return bq.impulseResponse(len);
    }
    
    void Process() override {
      if (newBiquadChains != biquadChains) {
        biquadChains = newBiquadChains;        
      }
      int nChannels = outputPins[0].wire->NChannels();
      int bufSize = outputPins[0].wire->BufSize();
      float** outbufs = outputPins[0].wire->buffers;
      float** inbufs = inputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        (*biquadChains)[ch].process(inbufs[ch], outbufs[ch], bufSize);
      }
    }
    
  };
  
}
