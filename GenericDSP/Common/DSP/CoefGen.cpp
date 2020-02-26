      //
//  CoefGen.cpp
//
//  Created by Andrew Voelkel on 4/13/15.
//  Copyright (c) 2015 Andrew Voelkel. All rights reserved.
//

#include "CoefGen.hpp"

namespace CoefGen {

  double prewarp(double sfreq, double Fs) {
    double c = 2 * M_PI;
    double T = 1/Fs;
    return (2/T) * tan(sfreq * c * (T/2)) / c;
  }
  
  complex<double> s2z(complex<double> s, double T) {
    return (1.0+s*T/2.0)/(1.0-s*T/2.0);
  }

  // See WikiPedia page for generalized 2nd order transform

  TFunc2ndOrder bilinear(TFunc2ndOrder atf, double fs) {
    float c = 2 * fs;
    float c_sq = powf(c, 2);

    TFunc2ndOrder dcoefs;
    Poly2ndOrder& xz = dcoefs.xCoefs;
    Poly2ndOrder& yz = dcoefs.yCoefs;
    Poly2ndOrder& xs = atf.xCoefs;
    Poly2ndOrder& ys = atf.yCoefs;

    yz.c0 = ys.c0 * c_sq + ys.c1 * c + ys.c2;

    xz.c0 = (xs.c0 * c_sq + xs.c1 * c + xs.c2) / yz.c0;
    xz.c1 = (xs.c0 * -2 * c_sq + xs.c2 * 2) / yz.c0;
    xz.c2 = (xs.c0 * c_sq - xs.c1 * c + xs.c2) / yz.c0;

    yz.c1 = (ys.c0 * -2 * c_sq + ys.c2 * 2) / yz.c0;
    yz.c2 = (ys.c0 * c_sq - ys.c1 * c + ys.c2) / yz.c0;
    yz.c0 = 1.0;

    return dcoefs;
  }

  // takes a 1 radian/sec prototype, scales frequency and gain, and converts

  TFunc2ndOrder bilinear(Poly2ndOrder num, Poly2ndOrder den,
                         double fc, double fs, double gain = 1.0) {
    num.Scale(gain);
    TFunc2ndOrder stf(num, den);
    double wfc = prewarp(fc, fs);
    stf.ScaleFrequency(2 * M_PI * wfc);
    return bilinear(stf, 44100);
  }

  TFunc2ndOrder peaking(double fc, double boost, double q, double fs) {
    double gain = pow(10, (boost/20.0));
    Poly2ndOrder snum(1.0, 0.0, 1.0);
    Poly2ndOrder sden(1.0, 0.0, 1.0);
    if (gain > 1) {
      snum.c1 = gain/q;
      sden.c1 = 1/q;
    } else {
      snum.c1 = 1/q;
      sden.c1 = 1.0/(gain*q);
    }
    return bilinear(snum, sden, fc, fs);
  }
  
  TFunc2ndOrder lfShelving6(double fc, double boost, double fs) {
    double gain = pow(10,abs(boost/20));
    double zero, pole;
    if (boost <= 0) {
      zero = -1; pole = -gain;
    } else {
      zero = -gain; pole = -1;
    }
    Poly2ndOrder polyNum(zero, 0);
    Poly2ndOrder polyDen(pole, 0);
    return bilinear(polyNum, polyDen, fc, fs);
  }

  TFunc2ndOrder hfShelving6(double fc, double boost, double fs) {
    double gain = pow(10,-abs(boost/20));
    double gaincomp;
    double zero, pole;
    if (boost >= 0) {
      pole = -1; zero = -gain; gaincomp = 1/gain;
    } else {
      zero = -gain; pole = -1; gaincomp = gain;
    }
    Poly2ndOrder polyNum(zero, 0);
    Poly2ndOrder polyDen(pole, 0);
    return bilinear(polyNum, polyDen, fc, fs, gaincomp);
  }

  TFunc2ndOrder lfShelving12(double fc, double boost, double fs) {
    complex<double> r1, r2, rz, rp;
    complex<double> x(-1,1);
    complex<double> y(1/sqrt(2.0), 0);
    r1 = x * y;
    boost = sqrt(pow(10,boost/20));
    if (boost > 1) {
      r2 = r1 * boost;
      rz = r2;
      rp = r1;
    } else {
      r2 = r1 / boost;
      rz = r1;
      rp = r2;
    }
    Poly2ndOrder snum(rz,conj(rz));
    Poly2ndOrder sden(rp,conj(rp));
    return bilinear(snum, sden, fc, fs);
  }
  
  TFunc2ndOrder hfShelving12(double fc, double boost, double fs) {
    complex<double> r1, r2, rz, rp;
    complex<double> x(-1,1);
    r1 = (1/sqrt(2.0)) * x;
    boost = sqrt(pow(10,boost/20));
    if (boost > 1) {
      r2 = r1 / boost;
      rz = r2;
      rp = r1;
    } else {
      r2 = r1 * boost;
      rz = r1;
      rp = r2;
    }
    Poly2ndOrder snum(rz, conj(rz));
    Poly2ndOrder sden(rp, conj(rp));
    return bilinear(snum, sden, fc, fs, pow(boost,2));
  }

  Coefs tf2Coefs(TFunc2ndOrder tf) {
    Coefs retval;
    tf.FillCoefs((double*)&retval);
    return retval;
  }

  Coefs PeakingCoefs(double fc, double dB, double q, double fs) {
    return tf2Coefs(peaking(fc, dB, q, fs));
  }

  Coefs LfShelvingCoefs(int order, double fc, double dB, double fs) {
    if (order == 2) {
      return tf2Coefs(lfShelving12(fc, dB, fs));
    } else {
      return tf2Coefs(lfShelving6(fc, dB, fs));
    }
  }

  Coefs HfShelvingCoefs(int order, double fc, double dB, double fs) {
    if (order == 2) {
      return tf2Coefs(hfShelving12(fc, dB, fs));
    } else {
      return tf2Coefs(hfShelving6(fc, dB, fs));
    }
  }

  int EqCoefs(double *coefs, uint32_t type, uint32_t order,
              double fc, double boost, double q, double fs) {
    if (order > 2 || order == 0) { return -1; }
    TFunc2ndOrder tf;
    switch(type) {
      case 0:
        tf = (order == 1) ? lfShelving6(fc, boost, fs) : lfShelving12(fc, boost, fs);
        break;
      case 1:
        tf = (order == 1) ? hfShelving6(fc, boost, fs) : lfShelving12(fc, boost, fs);
        break;
      case 2:
        if (order == 1) { return -1; }
        tf = peaking(fc, boost, q, fs);
        break;
      default:
        return -1;
    }
    tf.FillCoefs(coefs);
    return 0;
  }

  extern "C" void AddTwo(double in, double* out) {
    out[0] = in;
    out[1] = in + 2.5;
  }

//  vector<float> BiquadChainImpResp(vDSP_biquad_Setup setup, int nStages, int len) {
//    vector<float> impulse(len, 0); impulse[0] = 1;
//    vector<float> response(len);
//    vector<float> dlyBuf(4 * nStages);
//    vDSP_biquad(setup, &dlyBuf[0], &impulse[0], 1, &response[0], 1, len);
//    return response;
//  }

}
