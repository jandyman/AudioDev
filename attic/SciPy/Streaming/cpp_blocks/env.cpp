#include "env.h"


void FollowPeaks::init() {
  this->state = FollowPeaksState {};
}

void FollowPeaks::proc(vector<vector<float>>& buffers) {
  const auto& in = buffers[0];
  auto& out = buffers[1];
  auto& st = state;
  for (int i=0; i<in.size(); i++) {
    auto samp = in[i];
    if (samp > st.lastout) {
      st.lastout = params.attCoef * (samp - st.lastout) + st.lastout;
      st.lastpeak = st.lastout;
      st.sampSincePeak = 0;
      out[i] = st.lastout;
    } else {
      auto incr = st.lastpeak * st.sampSincePeak / params.div;
      st.lastout = st.lastout - incr;
      if (st.lastout < 0) { st.lastout = 0; }
      st.sampSincePeak += 1;
      out[i] = st.lastout;
    }
  }
}

void AttRel::init() {}

void AttRel::proc(vector<vector<float>>& buffers) {
  auto& st = state;
  auto& p = params;
  auto& in_buf = buffers[0];
  auto& out_buf = buffers[1];
  for (int i=0; i<in_buf.size(); i++) {
    auto samp = in_buf[i];
    auto lastout = st.lastout;
    if (samp > lastout) {
      st.lastout = p.attCoef * (samp - lastout) + lastout;
    } else {
      st.lastout = p.relCoef * (samp - lastout) + lastout;
    }
    out_buf[i] = st.lastout;
  }
}