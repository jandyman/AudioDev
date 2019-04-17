//
//  MiscDsp.cpp
//  AcoustifyCpp
//
//  Created by Andrew Voelkel on 4/3/15.
//  Copyright (c) 2015 Andrew Voelkel. All rights reserved.
//

#include "MiscDsp.hpp"
#include "GenericDsp.hpp"

// For flexibility, dst and src can be the same.
void ApplyDecayEnvelope(float SR, float dbPerSecond, float* dst, float* src, int len) {
  float dbPerSample = dbPerSecond/SR;
  float K = pow(10, -dbPerSample/20);
  float Env = 1.0;
  for (int i=0; i<len; i++) {
    dst[i] = src[i] * Env;
    Env *= K;
  }
}

namespace AWV {

  void FloatCpy(float* dst, float* src, int cnt) {
    memcpy(dst, src, cnt * sizeof(float));
  }

  int HighBit(int x) {
    return ceil(log2(ceil((double)x)));
  }
  
  DSPSplitComplex* NewSplitComplexArray(int cnt) {
    DSPSplitComplex* retval = new DSPSplitComplex;
    retval->realp = new float[cnt];
    retval->imagp = new float[cnt];
    return retval;
  }
  
  void FreeSplitComplexArray(DSPSplitComplex* x) {
    delete [] x->realp;
    delete [] x->imagp;
    delete x;
  }
  
  float* PadFloatArray(const float* x, int size, int cnt) {
    float *out = new float[size];
    memset(out, 0, size * sizeof(float));
    memcpy(out, x, cnt * sizeof(float));
    return out;
  }
  
  /**
   Performs a convolution using FFTs and multiplies in the frequency domain. This will be 
   much faster than time domain convolution for longer convolutions, but not for very 
   short convolution
   */
  
  void FastConv(const float* x, int nX, const float* y, int nY, float** z, int* nZ) {
    *nZ = nX + nY - 1;
    int log2len = HighBit(*nZ);
    int fftLen = 1 << log2len;
    float* xI = PadFloatArray(x, fftLen, nX);
    float* yI = PadFloatArray(y, fftLen, nY);
    DSPSplitComplex* xT = NewSplitComplexArray(fftLen);
    DSPSplitComplex* yT = NewSplitComplexArray(fftLen);
    DSPSplitComplex* zT = NewSplitComplexArray(fftLen);
    FFTSetup setup = vDSP_create_fftsetup(log2len, 2);
    Math::RealFFT(setup, log2len, xI, xT);
    Math::RealFFT(setup, log2len, yI, yT);
    // Do complex multiply of the two outputs
    vDSP_zvmul(xT, 1, yT, 1, zT, 1, fftLen, 1);
    // now overwrite the first results, which are not complex because they are packed
    zT->realp[0] = xT->realp[0] * yT->realp[0];
    zT->imagp[0] = xT->imagp[0] * yT->imagp[0];
    float* ifftBuf = new float[fftLen];
    *z = new float[*nZ];
    Math::RealIFFT(setup, log2len, zT, ifftBuf);
    memcpy(*z, ifftBuf, (*nZ * sizeof(float)));
    delete [] ifftBuf;
    delete [] xI;
    delete [] yI;
    FreeSplitComplexArray(xT);
    FreeSplitComplexArray(yT);
    FreeSplitComplexArray(zT);
    vDSP_destroy_fftsetup(setup);
  }

//  void ImpRespToFreqRespDb(int implenLog2) {
//    FFTSetup fftSetup = vDSP_create_fftsetup(implenLog2, kFFTRadix2);
//    int impLen = 1<<implenLog2;
//    
//    vDSP_hann_window(win, impLen*2, vDSP_HALF_WINDOW);
//    vDSP_vmul(resp, 1, &win[impLen-1], -1, resp, 1, impLen);
//    RealFFT(fftSetup, implenLog2, resp, &fftOut);
//    vector<complex<double>> vfftOut = ConvertFftResults<double>(fftOut, impLen/2);
//    function<double(complex<double>)> func = [] (complex<double> x) { return LinToDb(abs(x)); };
//    dbVal = XForm(func, vfftOut);
//  }
  
}
