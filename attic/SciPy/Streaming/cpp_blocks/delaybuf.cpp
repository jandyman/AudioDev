#include "delaybuf.h"
#include <algorithm>

using std::copy;

void DelayBuf::push(vector<float>& samples) {
  auto dsize = state.data.size();
  auto wr_idx = state.wr_idx;
  auto ssize = samples.size();
  auto to_end_cnt = dsize - wr_idx;
  if (ssize <= to_end_cnt) {
    std::copy(&samples[0], &samples[ssize], &state.data[wr_idx]);
  } else {  // need to split into two different writes
    std::copy(&samples[0], &samples[to_end_cnt], &state.data[wr_idx]);
    std::copy(&samples[to_end_cnt], &samples[ssize], &state.data[0]);
  }
  wr_idx += ssize;
  if (wr_idx >= dsize) { wr_idx -= dsize; }
  state.wr_idx = wr_idx;
}

void DelayBuf::get_values(int dly, vector<float>& output) { 
  auto& s = state;
  auto d = s.data;
  auto dsize = s.data.size();
  auto cnt = output.size();
  auto rd_idx = s.wr_idx - dly;
  if (rd_idx < 0) { rd_idx += dsize; }
  auto to_end_cnt = dsize - rd_idx;
  if (dly <= to_end_cnt) {
    std::copy(&d[rd_idx], &d[rd_idx+cnt], &output[0]);
  } else {  // need to split into two different writes
    std::copy(&d[rd_idx], &d[dsize], &output[0]);
    std::copy(&d[0], &d[cnt-to_end_cnt], &output[dsize-rd_idx]);
  }
}

