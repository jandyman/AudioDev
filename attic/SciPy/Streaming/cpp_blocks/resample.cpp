#include "resample.h"
#include "platform.h"


float JosFractDelay::fixed_delay(DelayBuf& delaybuf, float delay) {
  auto& p = params;
  auto samps_delay = ceil(delay);
  int h_offset = (samps_delay-delay) * pow(2, p.oversamp_bits);
  vector<float>& h = p.h_coef_set[h_offset];
  delaybuf.get_values(samps_delay, p.buffer);
  array_mult(h,p.buffer,p.buffer);
  return array_sum(p.buffer);
}

void Resampler::proc(vector<vector<float>>& bufs){
  auto& s = state;
  auto n_bufs = bufs.size();
  auto n_outs = (n_bufs-1) / 2;
  auto bufsiz = bufs[0].size();
  s.dly_buf.push(bufs[0]);
  for (int j=1; j<n_outs+1; j++) {
    auto out_buf_idx = j + n_outs;
    for (int i=0; i<bufsiz; i++) {
      bufs[out_buf_idx][i] = s.frac_dly.fixed_delay(s.dly_buf, bufsiz-i + bufs[j][i]);
    }
  }
}
