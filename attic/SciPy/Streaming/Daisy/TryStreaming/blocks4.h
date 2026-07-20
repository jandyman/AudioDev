#pragma once
#include <cstdint>
#include <vector>
#include <math.h>

using std::vector;
using std::copy;

namespace AWV {

struct Buffer {
  vector<float> data;
  Buffer(size_t size) {
    data = vector(size);
  }
};

struct BufferPool {
  vector<Buffer> buffers;
} buffer_pool;

int add_buffer(int size) {
  buffer_pool.buffers.push_back(Buffer(size));
  return buffer_pool.buffers.size();
}



/************ Sine Block **************/

struct SineBlockParams {
  float freq;
};

struct SineBlockState {
  float incr;
  float phase;
};

struct SineBlock {
  SineBlockParams p;
  SineBlockState s;

  void init(float fs);
  void update(float freq);
  void proc(vector<int> buf_idxs);

}; // end generated code

void SineBlock::init(float fs) {
  s.phase = 0;
  s.incr = 2 * M_PI * p.freq / fs;
}

void SineBlock::update(float freq) {
  s.freq = freq;
  init();
}

void SineBlock::proc(vector<int> buf_idxs) {
  auto vec = buffers[0];
  const int size = vec.size();
  for (int s=0; vec.size; s++) {
    vec[s] = sin(s.phase);
    s.phase += s.incr;
  }
}


