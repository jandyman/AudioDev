
#define uint unsigned int

namespace DspBlocks {

  struct DspError {
    const char *msg;
    DspError(const char *msg) : msg(msg) {}
  };

  struct Wire {
    std::string name = "";
    uint nChannels = 0;
    uint bufSize = 0;
    float sampleRate = 0;
    float **buffers = nullptr;

    Wire(uint nChannels, float SR, uint bufSize) {
      this->nChannels = nChannels;
      this->sampleRate = SR;
      this->bufSize = bufSize;
    }

    Wire() {}
    bool IsEmpty() { return (nChannels == 0); }
  };

  struct DspBlock;

  typedef void (DspBlock::*ParamSetter)(void *arg);

  enum class Units : uint8_t {
    none,
    hz,
    db
  };

  struct Parameter {
    std::string name;
    uint16_t size = 4;  // size of float
    Units type = Units::none;  
    ParamSetter param_setter;
    void set_callbacks(ParamSetter setter) {
      param_setter = setter;
    }
  };

  struct Pin {
    std::string name;
    Wire* wire = nullptr;
    Pin(std::string name) : name(name) {}
  };

  struct DspBlock {
    using str = std::string;
    char* name;
    std::vector<Pin> input_pins;
    std::vector<Pin> output_pins;
    std::vector<Parameter> parameters;
    
    void set_param(Parameter& p, float param) {
      (this->*p.param_setter)(&param);
    }

    void setup_pins(std::vector<str> in_pin_names, std::vector<str> out_pin_names) {
      for (auto pin_name : in_pin_names) {
        input_pins.push_back(Pin(pin_name));
      }
      for (auto pin_name : out_pin_names) {
        output_pins.push_back(Pin(pin_name));
      }
    }

  };

  struct MyDspBlock : DspBlock {
    float param1, param2;

    void set_param1(void* param) {
      param1 = *((float*)param);
    }

    void set_param2(void* param) {
      param2 = *((float*)param);
    }

    MyDspBlock() {
      std::vector<std::string> in_pin_names= { "in1", "in2" };
      std::vector<std::string> out_pin_names = { "out1", "out2" };
      setup_pins(in_pin_names, out_pin_names);
      using c = MyDspBlock;
      parameters = std::vector<Parameter>(2);
      parameters[0].set_callbacks((ParamSetter)&c::set_param1);
      parameters[1].set_callbacks((ParamSetter)&c::set_param2);
    }
  };

  void tryit() {
    MyDspBlock block;
    (block.*block.parameters[1].param_setter)(nullptr);
  }



  

}
