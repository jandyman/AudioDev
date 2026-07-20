// The purpose of this file is to reduce platform dependency at the higher 
// block level, by making platform specific features more generic

#pragma once
#include "filtering_functions.h"
#include "arm_math.h"
#include <vector>
#include <cstdint>

__attribute__((weak)) float array_sum(std::vector<float>& arr) {
  float sum = 0;
  for (float item : arr) { sum += item; }
  return sum;
}

__attribute__((weak)) void array_mult(std::vector<float>& x, std::vector<float>& y, std::vector<float>& out) {
  return arm_mult_f32(&x[0], &y[0], &out[0], (uint32_t)x.size());
}


typedef arm_biquad_casd_df1_inst_f32 P_BiquadChainState;