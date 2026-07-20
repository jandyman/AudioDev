// Block and Param Definitions

// ------ AccumulateData ------

struct AccumulateDataParams {
  int n_buffers;
};

class AccumulateData;

struct AccumulateDataChan : SingleChanBlock {
  AccumulateData* c;
  vector<float*> data;
  AccumulateDataChan(void* c) : c((AccumulateData*)c) {}
  void proc(vector<float*> buffers);
};

struct AccumulateData : SingleChanContainer<AccumulateDataChan, AccumulateDataParams> {
  int buf_idx;
  AccumulateData(int n_chans, AccumulateDataParams params) :
    SingleChanContainer(1, n_chans, params) {}

  void proc() {
    SingleChanContainer::proc();
    buf_idx += 1;
  }

  void signal_specs_finalized() {
    for (auto block : blocks) {
      for (int i=0; i<params.n_buffers; i++) {
        block.data.push_back(new float[bufsiz]);
      }
    }
    SingleChanContainer::signal_specs_finalized();
  }
};

void AccumulateDataChan::proc(vector<float*> buffers) {
  auto in_buf = buffers[0];
  auto& buf_idx = c->buf_idx;
  if (buf_idx < c->params.n_buffers) {
    std::copy(in_buf, in_buf + c->bufsiz, data[buf_idx]);
    buf_idx += 1; 
  }
}

// ------ GainBlock ------

struct GainBlockParams {
  float gain;
};

class GainBlock;

struct GainBlockChan : SingleChanBlock {
  GainBlock* c;
  GainBlockChan(void* c) : c((GainBlock*)c) {}
  void proc(vector<float*> buffers);
};

struct GainBlock : SingleChanContainer<GainBlockChan, GainBlockParams> {
  GainBlock(int n_chans, GainBlockParams params) :
    SingleChanContainer(2, n_chans, params) {}
};

void GainBlockChan::proc(vector<float*> buffers) {
  // multiply gain by input buffer
  float* i_ptr = buffers[0];
  float* o_ptr = buffers[1];
  for (int s=0; s < c->bufsiz; s++) {
    o_ptr[s] = i_ptr[s] * c->params.gain;
  }
}

// ------ SineBlock ------

struct SineBlockParams {
  float freq;
  float fs;
};

class SineBlock;

struct SineBlockChan : SingleChanBlock {
  SineBlock* c;
  float phase;
  SineBlockChan(void* c) : c((SineBlock*)c) {}
  void proc(vector<float*> buffers);
  void init();
};

struct SineBlock : SingleChanContainer<SineBlockChan, SineBlockParams> {
  float incr;
  SineBlock(int n_chans, SineBlockParams params) :
    SingleChanContainer(1, n_chans, params) {}

  void init() {
    auto fs = pins[0].fs;
    incr = 2 * M_PI * params.freq / fs;
    // call channel inits
    SingleChanContainer::init();
  }
};

void SineBlockChan::proc(vector<float*> buffers) {
  float* ptr = buffers[0];
  for (int s=0; s < c->bufsiz; s++) {
    ptr[s] = sin(phase);
    phase += c->incr;
  }
}

void SineBlockChan::init() {
  phase = 0;
}

// Allocate buffers
float bufdata_0[128];
float bufdata_1[128];
float bufdata_2[128];
float bufdata_3[128];
float bufdata_4[128];
float bufdata_5[128];

Buffer buffer_pool[6] = {
  Buffer(128, bufdata_0),
  Buffer(128, bufdata_1),
  Buffer(128, bufdata_2),
  Buffer(128, bufdata_3),
  Buffer(128, bufdata_4),
  Buffer(128, bufdata_5),
};

// Allocate Blocks
SineBlock sine_block_0(2, SineBlockParams{1000, 44100}); // freq, fs
GainBlock gain_block_1(2, GainBlockParams{2}); // gain
GainBlock gain_block_2(2, GainBlockParams{0.5}); // gain
AccumulateData accumulate_data_3(2, AccumulateDataParams{4}); // n_buffers

void graph_init() {

  // Setup Pins
  sine_block_0.set_signal_specs(0, Pin(44100, 2, 128));
  sine_block_0.signal_specs_finalized();
  gain_block_1.set_signal_specs(0, Pin(44100, 2, 128));
  gain_block_1.set_signal_specs(1, Pin(44100, 2, 128));
  gain_block_1.signal_specs_finalized();
  gain_block_2.set_signal_specs(0, Pin(44100, 2, 128));
  gain_block_2.set_signal_specs(1, Pin(44100, 2, 128));
  gain_block_2.signal_specs_finalized();
  accumulate_data_3.set_signal_specs(0, Pin(44100, 2, 128));
  accumulate_data_3.signal_specs_finalized();

  // Assign Buffers (args are buf_idx, pin_idx, chan_idx)
  sine_block_0.assign_buffer(0, 0, 0);
  sine_block_0.assign_buffer(0, 0, 1);
  gain_block_1.assign_buffer(0, 0, 0);
  gain_block_1.assign_buffer(0, 0, 1);
  gain_block_1.assign_buffer(2, 1, 0);
  gain_block_1.assign_buffer(2, 1, 1);
  gain_block_2.assign_buffer(2, 0, 0);
  gain_block_2.assign_buffer(2, 0, 1);
  gain_block_2.assign_buffer(4, 1, 0);
  gain_block_2.assign_buffer(4, 1, 1);
  accumulate_data_3.assign_buffer(4, 0, 0);
  accumulate_data_3.assign_buffer(4, 0, 1);

  // Call init functions
  sine_block_0.init();
  gain_block_1.init();
  gain_block_2.init();
  accumulate_data_3.init();
}

void graph_proc() {
  sine_block_0.proc();
  gain_block_1.proc();
  gain_block_2.proc();
  accumulate_data_3.proc();
}
