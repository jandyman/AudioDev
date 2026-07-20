//
//  Dynamics.hpp
//  DSP Library
//
//  Created by Andrew Voelkel on 3/11/17.
//
//

#pragma once

#include <stdio.h>
#include <math.h>

namespace DSP {
  
  struct AttRel {
    double AtkCoef;
    double RelCoef;
    double Y;
    
  public:
    
    AttRel(double Fs, double AtkTime, double RelTime) {
      AtkCoef = CoefFromTimeConstant(AtkTime, Fs);
      RelCoef = CoefFromTimeConstant(RelTime, Fs);
      Y = 0;
    }
    
    double Run(double input) {
      if (input > Y) {
        Y = (1 - AtkCoef) * Y + AtkCoef * input;
      } else {
        Y = (1 - RelCoef) * Y + RelCoef * input;
      }
      return Y;
    }
    
    float Run(float* inBuf, int cnt) {
      for (int i=0; i<cnt; i++) {
        Run(inBuf[i]);
      }
      return Y;
    }
    
    static double CoefFromTimeConstant(double tc, double Fs) {
      return 1 - exp(-1 / (Fs * tc));
    }
    
  };
  
}


