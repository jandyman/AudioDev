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
    double *coefs = NULL;
    float *dlyBuf = NULL;
    int nStages = 0;
    
    void init(double* coefs, uint nStages) {
      this->nStages = nStages;
      clearState();
      this->coefs = new double[5 * nStages];
      copy(coefs, coefs + (5 * nStages), this->coefs);
      biquadSetup = vDSP_biquad_CreateSetup(coefs, (vDSP_Length)nStages);
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
    
    BiquadChain(double* coefs, int nStages) {
      init(coefs, nStages);
    }
    
    BiquadChain(vector<EqSpec> specs, double sampleRate) {
      double allCoefs[specs.size() * 5];
      int idx = 0, nStages = 0;
      for (auto spec: specs) {
        if (spec.needsCoefs()) {
          auto coefs = spec.Coefs(sampleRate);
          coefs.fillArray(&allCoefs[idx]); idx += 5;
          nStages++;
        }
      }
      init(allCoefs, nStages);
    }
    
    BiquadChain (const BiquadChain &obj) {
      nStages = obj.nStages;
      dlyBuf = new float[4 * nStages]();
      coefs = new double[5 * nStages];
      copy(obj.coefs, obj.coefs + (5 * nStages), coefs);
      biquadSetup = vDSP_biquad_CreateSetup(coefs, nStages);
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
    vector<BiquadChain> biquadChains;
    vector<EqSpec> eqSpecs;
    uint nStages = 1;
    uint nChannels = 0;
    
  public:
    BiquadChainBlock(int nStages = 1) : DspBlockSingleWireSpec(1,1) {
      this->nStages = nStages;
      eqSpecs = vector<EqSpec>(nStages, EqSpec());
    }
    
    const string GetClassName() override { return "Biquad Chain"; }
    
    void SetEqSpecs(vector<EqSpec> eqSpecs) {
      this->eqSpecs = eqSpecs;
      nStages = eqSpecs.size();
      updateBiquadChains();
    }
    
    int GetNStages() { return nStages; }
    
    vector<EqSpec> GetEqSpecs() { return eqSpecs; }
    
    void Init() override {
      nChannels = outputPins[0].wire->NChannels();
      assertConnected();
      updateBiquadChains();
    }
    
    void assertConnected() {
      if (nChannels == 0) { throw new DspError("BiquadChainBlock not connected"); }
    }
    
    void updateBiquadChains() {
      auto coefs = EqSpec::ToCoefs(eqSpecs, sharedWireSpec.sampleRate);
      auto biquadChain = BiquadChain(coefs, nStages);
      biquadChains = vector<BiquadChain>(nChannels, biquadChain);
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
      int nChannels = outputPins[0].wire->NChannels();
      int bufSize = outputPins[0].wire->BufSize();
      float** outbufs = outputPins[0].wire->buffers;
      float** inbufs = inputPins[0].wire->buffers;
      for (int ch=0; ch < nChannels; ch++) {
        biquadChains[ch].process(inbufs[ch], outbufs[ch], bufSize);
      }
    }
    
  };
  
}
