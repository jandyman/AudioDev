
#pragma once

#include <stdio.h>
#include <tgmath.h>
#include <Accelerate/Accelerate.h>

#ifdef __cplusplus
#define EXTERNC extern "C"
#else
#define EXTERNC
#endif

EXTERNC void FloatCpy(float* dst, float* src, int cnt);
EXTERNC void RealFFT(FFTSetup setup, int log2size, float *input, DSPSplitComplex *output);
EXTERNC void RealIFFT(FFTSetup setup, int log2size, DSPSplitComplex *input, float *output);
EXTERNC void FastConv(const float* x, int nX, const float* y, int nY, float** z, int* nZ);
EXTERNC void ApplyDecayEnvelope(float SR, float dbPerSecond, float* dst, float* src, int len);

EXTERNC double Lin2Log(double lin, double minVal, double maxVal);

EXTERNC double LinToDb(double src) { return 20 * log10(src); }
EXTERNC double DbToLin(double src) { return pow(10, src/20.0); }

#ifdef __cplusplus
#include <vector>

namespace AWV {
  
  using namespace std;
  
  template <class S, class D> vector<double> XForm(function<D(S)> func, vector<S> src) {
    vector<D> dst(src.size(),0);
    for (long i=0; i<src.size(); i++) {
      dst[i] = func(src[i]);
    }
    return dst;
  }

  template <class T> vector<complex<T>> ConvertFftResults(DSPSplitComplex sc, int cnt) {
    vector<complex<T>> retval(cnt+1,{0,0});
    retval[0].real(sc.realp[0]);
    retval[cnt].real(sc.imagp[0]);
    for (int i=1; i<cnt; i++) {
      retval[i].real(sc.realp[i]);
      retval[i].imag(sc.imagp[i]);
    }
    return retval;
  }  
}

#endif

