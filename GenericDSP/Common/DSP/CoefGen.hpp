//
//  Header.h
//
//  Created by Andrew Voelkel on 4/13/15.
//  Copyright (c) 2015 Andrew Voelkel. All rights reserved.
//

#pragma once

#include <complex>
#include <vector>
#include <Accelerate/Accelerate.h>

namespace CoefGen {
  using namespace std;
  
  struct Coefs {
    double c0;
    double c1;
    double c2;
    double c3;
    double c4;

    void fillArray(double* array) {
      array[0] = c0;
      array[1] = c1;
      array[2] = c2;
      array[3] = c3;
      array[4] = c4;
    }
  };
  
  double prewarp(double sfreq, double Fs);
  
  complex<double> s2z(complex<double> s, double T);

  struct Roots2ndOrder;
  
  struct Poly2ndOrder {
    double c0;
    double c1;
    double c2;
    
    Poly2ndOrder(double c0, double c1, double c2) {
      this->c0 = c0;
      this->c1 = c1;
      this->c2 = c2;
    }
    
    void Scale(double scalar) {
      c0 = c0 * scalar;
      c1 = c1 * scalar;
      c2 = c2 * scalar;
    }
    
    double Eval(double val) {
      return c0 + val * c1 + pow(val,2) * c2;
    }
    
    // Args must be real roots or complex conjugates!!
    Poly2ndOrder(complex<double> root1, complex<double> root2) {
      c0 = 1;
      c1 = -((root1 + root2)).real();
      c2 = (root1 * root2).real();
    }
    
    Poly2ndOrder() { c0 = c1 = c2 = 0; }
    
    void ScaleFrequency(double scalar) {
      c2 *= scalar * scalar;
      c1 *= scalar;
    }
    
  };
  
  struct TFunc2ndOrder {
    Poly2ndOrder xCoefs;
    Poly2ndOrder yCoefs;
    
    TFunc2ndOrder() { }

    TFunc2ndOrder(Poly2ndOrder xPoly, Poly2ndOrder yPoly) {
      xCoefs = xPoly; yCoefs = yPoly;
    }
    
    void normalizeGain(double xNormFreq) {
      double scalar = 1.0 / yCoefs.c0;
      xCoefs.Scale(scalar);
      yCoefs.Scale(scalar);
      scalar = yCoefs.Eval(xNormFreq)/xCoefs.Eval(xNormFreq);
      xCoefs.Scale(scalar);
    }
    
    void FillCoefs(double *coefs) {
      coefs[0] = xCoefs.c0;
      coefs[1] = xCoefs.c1;
      coefs[2] = xCoefs.c2;
      coefs[3] = yCoefs.c1;
      coefs[4] = yCoefs.c2;
    }

    void ScaleFrequency(double scalar) {
      xCoefs.ScaleFrequency(scalar);
      yCoefs.ScaleFrequency(scalar);
    }
    
  };

  Coefs PeakingCoefs(double fc, double dB, double q, double fs);
  Coefs LfShelvingCoefs(int order, double fc, double dB, double fs);
  Coefs HfShelvingCoefs(int order, double fc, double dB, double fs);

  struct EqSpec {
    enum Type { peaking, loShelf, hiShelf };

    bool enabled = true;
    enum Type type = peaking;
    int order = 2;
    double frequency = 1000;
    double dB = 0;
    double Q = 1;

    bool needsCoefs() {
      return ((enabled == false) || (dB == 0)) ? false : true;
    }

    Coefs Coefs(double sampleRate) {
      switch (type) {
        case loShelf:
          return LfShelvingCoefs(order, frequency, dB, sampleRate);
        case hiShelf:
          return HfShelvingCoefs(order, frequency, dB, sampleRate);
        case peaking:
          return PeakingCoefs(frequency, dB, Q, sampleRate);
        default:
          struct Coefs coefs = { 0,0,0,0,0 };
          return coefs;
      }
    }

    static double* ToCoefs(vector<EqSpec> specs, double sampleRate) {
      double *retval = new double[specs.size() * 5];
      int idx = 0;
      for (auto spec: specs) {
        auto coefs = spec.Coefs(sampleRate);
        coefs.fillArray(&retval[idx]); idx += 5;
      }
      return retval;
    }

  };

  TFunc2ndOrder peaking(double fc, double boost, double q, double fs);
  TFunc2ndOrder lfShelving12(double fc, double boost, double fs);
  TFunc2ndOrder lfShelving6(double fc, double boost, double fs);
  TFunc2ndOrder hfShelving12(double fc, double boost, double fs);
  TFunc2ndOrder hfShelving6(double fc, double boost, double fs);
  Coefs tf2Coefs(TFunc2ndOrder tf);

  vector<float> BiquadChainImpResp(vDSP_biquad_Setup setup, int nStages, int len);


}

