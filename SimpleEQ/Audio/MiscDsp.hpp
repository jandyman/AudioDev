
#pragma once

#include <stdio.h>
#include <tgmath.h>
#include <Accelerate/Accelerate.h>

#ifdef __cplusplus
#define EXTERNC extern "C"
#else
#define EXTERNC
#endif

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
  
  void FastConv(const float* x, int nX, const float* y, int nY, float** z, int* nZ);
  void ApplyDecayEnvelope(float SR, float dbPerSecond, float* dst, float* src, int len);
  
  class Math {
    
  public:
    
    static void RealFFT(FFTSetup setup, int log2size, float *input, DSPSplitComplex *output) {
      // seems like we need to tweak gain
      float gain = .5;
      int size = 1<<log2size;
      float adjusted[size]; // don't overwrite input
      vDSP_vsmul(input, 1, &gain, adjusted, 1, size);
      vDSP_ctoz((const DSPComplex *)adjusted, 2, output, 1, size/2);
      vDSP_fft_zrip(setup, output, 1, log2size, kFFTDirection_Forward);
    }
    
    static void RealIFFT(FFTSetup setup, int log2size, DSPSplitComplex *input, float *output) {
      vDSP_fft_zrip(setup, input, 1, log2size, kFFTDirection_Inverse);
      vDSP_ztoc(input, 1, (DSPComplex*)output, 2, 1<<(log2size-1));
      // seems like we need to tweak gain
      float gain = 1.0/(1<<(log2size));
      vDSP_vsmul(output, 1, &gain, output, 1, 1<<log2size);
    }
        
    static double Lin2Log(double lin, double minVal, double maxVal) {
      double minLog = log10(minVal);
      double maxLog = log10(maxVal);
      double exp = minLog + (maxLog - minLog) * lin;
      return pow(10, exp);
    }
    
    static double LinToDb(double src) { return 20 * log10(src); }
    static double DbToLin(double src) { return pow(10, src/20.0); }
    
    static vector<float> LogSpacedArray(float minVal, float maxVal, int nPoints) {
      vector<float> retval(nPoints);
      for (int i=0; i<nPoints; i++) {
        float mapIn = (float)i / nPoints;
        float minLog = log10(minVal);
        float maxLog = log10(maxVal);
        float exp = minLog + (maxLog - minLog) * mapIn;
        retval[i] = pow(10, exp);
      }
      return retval;
    }
    
  };
  
  class FftAnalyzer {
    int log2len;  // length of the fft as power of 2
    int intLen;   // length of the fft as int
    vector<float> real;
    vector<float> imag;
    DSPSplitComplex fftOut;
    FFTSetup fftSetup;

    float minFreq = 10;
    float maxFreq = 20000;
    float nFreqPoints = 100;
    float SR = 0;
    vector<float> frequencies;
    vector<int> idxs;
    vector<float> dB;
    
    void SetupIdxArray() {
      dB = vector<float>(nFreqPoints);
      if (SR != 0 && frequencies.size() > 0) {
        idxs = vector<int>(nFreqPoints);
        for (int i=0; i<nFreqPoints; i++) {
          idxs[i] = frequencies[i] / (SR/2.0) * (intLen/2 + 1);
        }
      }
    }

  public:

    FftAnalyzer(int log2len) : log2len(log2len) {
      intLen = 1 << log2len;
      real = vector<float>(intLen);
      imag = vector<float>(intLen);
      fftOut.imagp = &imag[0];
      fftOut.realp = &real[0];
      fftSetup = vDSP_create_fftsetup(log2len, kFFTRadix2);
    }
    
    void SetSampleRate(float SR) {
      this->SR = SR;
      SetupIdxArray();
    }
    
    void SetFrequencies(float minFreq, float maxFreq, int nFreqPoints) {
      this->minFreq = minFreq; this->maxFreq = maxFreq;
      this->nFreqPoints = nFreqPoints;
      frequencies = Math::LogSpacedArray(minFreq, maxFreq, nFreqPoints);
      SetupIdxArray();
    }
    
    vector<float>& GetFrequencies() { return frequencies; }
    
    vector<float>& GetFrequencyResponse(vector<float> impulseResponse) {
      Math::RealFFT(fftSetup, log2len, &impulseResponse[0], &fftOut);
      for (int i=0; i < nFreqPoints; i++) {
        int idx = idxs[i];
        if (idx == 0) {
          dB[i] = abs(fftOut.realp[0]);
        } else if (idx == intLen) {
          dB[i] = abs(fftOut.imagp[0]);
        } else {
          float realp = fftOut.realp[idx];
          float imagp = fftOut.imagp[idx];
          dB[i] = 20 * log10(sqrt(pow(realp,2) + pow(imagp,2)));
        }
      }
      return dB;
    }
    
  };
  
}

#endif

