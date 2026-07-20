#pragma once
#include <cstdint>
#include <vector>
#include <math.h>

using std::vector;
using std::copy;


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
  Buffer(size_t size, float* storage) : size(size), data(storage) {}
};


extern Buffer buffer_pool[];

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
    float* ptr = buffer_pool[buf_n].data;
    pins[pin].buffers[chan] = ptr;
  }

  virtual void init() = 0;
  virtual void proc() = 0;
};


struct SingleChanBlock{
  virtual void proc(vector<float*> buffers) = 0;
  virtual void init() {}
};


template <class B, class P> struct SingleChanContainer : Block {
  int n_chans;
  P params;
  vector<B> blocks;
  vector<vector<float*>> buffers;  // indexed by channel, then pin
  int bufsiz = 0;  // utility var for single fs blocks

  SingleChanContainer(int n_pins, int n_blks, P params) : Block(n_pins) {
    this->params = params;
    for (int i=0; i<n_blks; i++) {
      blocks.push_back(B(this));
    }
  }

  void alloc_buf_vector(int chan_idx) {
    for (size_t p=0; p<pins.size(); p++) {
      buffers[chan_idx].push_back(nullptr);
    }
  }

  void signal_specs_finalized() {
    n_chans = pins[0].n_chans;
    bufsiz = pins[0].bufsiz;
    for (int c=0; c<n_chans; c++) {
      buffers.push_back(vector<float*>());
      alloc_buf_vector(c);
    }
  }

  virtual void init() {
    n_chans = pins[0].n_chans;
    for (int i=0; i<n_chans; i++) { blocks[i].init(); }
  }

  virtual void proc() {
    for (int i=0; i<n_chans; i++) {
      blocks[i].proc(buffers[i]);
    }
  }

  void assign_buffer(int buf_n, int pin, int chan) {
    Block::assign_buffer(buf_n, pin, chan);
    float* ptr = buffer_pool[buf_n].data;
    buffers[chan][pin] = ptr;
  }
};



