
#define uint unsigned int

namespace DspBlocks {

  struct BaseClass {};
  typedef void (BaseClass::*BaseMethod)(void *arg);

  struct DerivedClass : BaseClass {
    void Action1(void* param) {  /* do something */ }
    void Action2(void* param) {  /* do something */ }
    void Action3(void* param) {  /* do something */ }
  };

  void SetupMethodPointers(BaseMethod& m1, BaseMethod& m2) { 
    m1 = (BaseMethod)&DerivedClass::Action3;
    m2 = (BaseMethod)&DerivedClass::Action1;
  }

  void Caller() {
    DerivedClass* obj1;  // these need to be initialized somehow, of course
    DerivedClass* obj2;
    BaseMethod method1;
    BaseMethod method2;
    SetupMethodPointers(method1, method2);
    // now the caller doesn't know the names of the methods being invoked
    (obj1->*method1)(nullptr);
    (obj2->*method2)(nullptr);
  }

  struct DspError {
    const char *msg;
    DspError(const char *msg) : msg(msg) {}
  };

  struct WireSpec {
    uint nChannels = 0;
    uint bufSize = 0;
    float sampleRate = 0;
    float **buffers;

    WireSpec(uint nChannels, float SR, uint bufSize) {
      this->nChannels = nChannels;
      this->sampleRate = SR;
      this->bufSize = bufSize;
    }

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
    uint16_t size = 4;  // size of float
    Units type = Units::none;  
    ParamSetter param_setter;
    void SetCallbacks(ParamSetter setter) {
      param_setter = setter;
    }
  };

  struct DspBlock {
    std::vector<WireSpec> wireSpecs;
    std::vector<Parameter> parameters;
    
    DspBlock() {
      wireSpecs.push_back(WireSpec(2, 44100, 128));
      wireSpecs.push_back(WireSpec(4, 44100, 64));
    }
    
    void SetParam(Parameter& p, float param) {
      (this->*p.param_setter)(&param);
    }

  };

  struct MyDspBlock : DspBlock {
    float param1, param2;

    void SetParam1(void* param) {
      param1 = *((float*)param);
    }

    void SetParam2(void* param) {
      param2 = *((float*)param);
    }

    MyDspBlock() {
      using c = MyDspBlock;
      parameters = std::vector<Parameter>(2);
      parameters[0].SetCallbacks((ParamSetter)&c::SetParam1);
      parameters[1].SetCallbacks((ParamSetter)&c::SetParam2);
    }
  };

  void tryit() {
    MyDspBlock block;
    (block.*block.parameters[1].param_setter)(nullptr);
  }



  

}
