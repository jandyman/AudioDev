#pragma once
#include <cstdint>
#include <vector>
#include <math.h>

using std::vector;
using std::copy;

namespace AWV {

struct Pin {
  float fs = 0;
  int n_chans = 0;
  int bufsiz = 0;
  vector<float*> buffers;

  Pin() {}
  Pin(float f, int n, int b) : fs(f), n_chans(n), bufsiz(b) {
    for (int i=0; i<n_chans; i++) { buffers.push_back(nullptr); }
  }
};

struct Buffer {
  size_t size;
  float* data;
  Buffer(size_t size) {
    data = new float[size];
    this->size = size;
  }
};

struct BufferPool {
  vector<Buffer> buffers;
} buffer_pool;

int add_buffer(int size) {
  buffer_pool.buffers.push_back(Buffer(size));
  return buffer_pool.buffers.size();
}

struct Block {
  vector<Pin> pins;

  Block(int n_pins) {
    for (int p=0; p<n_pins; p++) {
       pins.push_back(Pin());
    }
  }

  void set_signal_specs(int pin_idx, Pin src) {
    pins[pin_idx] = src;
  }

  // Called after all signal specs are set
  void signal_specs_finalized() {}

  void assign_buffer(int buf_n, int pin, int chan) {
    float* ptr = buffer_pool.buffers[buf_n].data;
    pins[pin].buffers[chan] = ptr;
  }

};


struct ch_state { };

template <class S, class P> struct SingleChanBlock{
  P* params;
  S state;
  int bufsiz;

  SingleChanBlock(P* params) : params(params) {}

  virtual void proc(int chan, vector<float*> buffers) = 0;
  virtual void init(int chan) = 0;

};


template <class B, class P> struct SingleChanContainer : Block {
  int n_chans;
  P params;
  vector<B> blocks;
  vector<vector<float*>> buffers;  // indexed by channel, then pin
  int bufsiz = 0;  // utility var for single fs blocks

  SingleChanContainer(int n_pins, int n_blks, P params) : params(params) {
    for (int i=0; i<n_blks; i++) {
      blocks.add(new B(&params));
    }
  }

  void alloc_buf_vector(int chan_idx) {
    for (int p=0; p<pins.size(); p++) {
      buffers[chan_idx].push_back(nullptr);
    }
  }

  void signal_specs_finalized() {
    n_chans = pins[0].n_chans;
    bufsiz = pins[0].bufsiz;
    for (int c=0; c<n_chans; c++) {
      blocks(c).bufsiz = bufsiz;
      buffers.push_back(vector<float*>());
      alloc_buf_vector(c);
    }
  }

  virtual void init() {
    n_chans = pins[0].n_chans;
    for (int i=0; i<n_chans; i++) { ch_init(i); }
  }

  virtual void proc() {
    for (int i=0; i<n_chans; i++) {
      ch_proc(i, buffers[i]);
    }
  }

  void assign_buffer(int buf_n, int pin, int chan) {
    Block::assign_buffer(buf_n, pin, chan);
    float* ptr = buffer_pool.buffers[buf_n].data;
    buffers[chan][pin] = ptr;
  }
};


#include "structs.h"


/************ Sine Block **************/


struct SineBlockChan : SingleChanBlock<SineBlockState, SineBlockParams> {

  void init() override {
    // start substituted
    params->incr = 2 * M_PI * freq / params->fs;
    state.phase = 0;
    // end substituted
  }

  void proc(vector<float*> buffers) override {
    // start substituted
    float* ptr = buffers[0];
    for (int s=0; s<bufsiz; s++) {
      ptr[s] = sin(state.phase);
      state.phase += incr;
    }
    // end substituted
  }

}; // end generated code

// this could be generated (goes in pygen.h)

struct SineBlock : SingleChanContainer<SineBlockChan, SineBlockParams> {
  SineBlock(int n_chans, SineBlockParams params) :
    SingleChanContainer(1, n_chans, params) {}
};


/************ Gain Block **************/

struct GainBlock : SingleChanBlock<GainBlockState, GainBlockParams> {

  void proc(vector<float*> buffers) override {
    // multiply gain by input buffer
    float* i_ptr = buffers[0];
    float* o_ptr = buffers[1];
    for (int s=0; s<bufsiz; s++) {
      o_ptr[s] = i_ptr[s] * params->gain;
    }
  }

  GainBlock(float gain) : SingleChanWrapper(2), gain(gain) {}
};

struct GainBlock : SingleChanContainer<GainBlockChan, GainBlockParams> {
  GainBlock(int n_chans, SineBlockParams params) :
    SingleChanContainer(2, n_chans, params) {}
};



/************ Accumulate Data **************/

struct AccumulateData : SingleChanBlock<AccumulateDataState, AccumulateDataParams> {

  // add buf_idx to params struct somehow

  void proc(vector<float*> buffers) override {
    // multiply gain by input buffer
    float* i_ptr = buffers[0];
    float* o_ptr = buffers[1];
    for (int s=0; s<bufsiz; s++) {
      o_ptr[s] = i_ptr[s] * params->gain;
    }
  }

  GainBlock(float gain) : SingleChanWrapper(2), gain(gain) {}
};

struct AccumulateData : Block {
  int n_buffers; // n_buffers to accumulate
  int buf_idx = 0;
  vector<float*> data;

  void init() {
    buf_idx = 0;
    auto pin = pins[0];
    for (int i=0; i<pin.n_chans; i++) {
      data.push_back(new float[pin.bufsiz]);
    }
  }

  void proc() {
    auto pin = pins[0];
    auto bufsiz = pin.bufsiz;
    if (buf_idx < n_buffers) {
      for (int c = 0; c < pin.n_chans; c++) {
        auto src = pin.buffers[c];
        auto dst = data[c];
        auto dst_ptr = &dst[buf_idx * bufsiz];
        copy(src, src + bufsiz, dst_ptr);
      }
      buf_idx++;
    }
  }

  AccumulateData(int n_buffers) : Block(1), n_buffers(n_buffers) {}
};

}



