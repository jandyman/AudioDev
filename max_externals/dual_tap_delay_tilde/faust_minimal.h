// Minimal Faust architecture definitions for Max/MSP integration
// Provides base classes that Faust-generated code expects

#ifndef __FAUST_MINIMAL_H__
#define __FAUST_MINIMAL_H__

#include <string>
#include <vector>

// Faust uses double by default with -double flag
#ifndef FAUSTFLOAT
#define FAUSTFLOAT double
#endif

// Meta class for metadata
struct Meta {
  virtual ~Meta() {}
  virtual void declare(const char* key, const char* value) = 0;
};

// Base DSP class
class dsp {
 public:
  virtual ~dsp() {}
  virtual int getNumInputs() = 0;
  virtual int getNumOutputs() = 0;
  virtual void buildUserInterface(class UI* ui_interface) = 0;
  virtual int getSampleRate() = 0;
  virtual void init(int sample_rate) = 0;
  virtual void instanceInit(int sample_rate) = 0;
  virtual void instanceConstants(int sample_rate) = 0;
  virtual void instanceResetUserInterface() = 0;
  virtual void instanceClear() = 0;
  virtual dsp* clone() = 0;
  virtual void metadata(Meta* m) = 0;
  virtual void compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs) = 0;
};

// UI class for parameter management
class UI {
 public:
  virtual ~UI() {}

  // Layout
  virtual void openTabBox(const char* label) = 0;
  virtual void openHorizontalBox(const char* label) = 0;
  virtual void openVerticalBox(const char* label) = 0;
  virtual void closeBox() = 0;

  // Active widgets
  virtual void addButton(const char* label, FAUSTFLOAT* zone) = 0;
  virtual void addCheckButton(const char* label, FAUSTFLOAT* zone) = 0;
  virtual void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) = 0;
  virtual void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) = 0;
  virtual void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) = 0;

  // Passive widgets
  virtual void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max) = 0;
  virtual void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT min, FAUSTFLOAT max) = 0;

  // Metadata
  virtual void declare(FAUSTFLOAT*, const char*, const char*) {}
};

// Simple UI implementation that just stores parameter references
class MapUI : public UI {
 private:
  struct ParamInfo {
    std::string label;
    FAUSTFLOAT* zone;
    FAUSTFLOAT init;
    FAUSTFLOAT min;
    FAUSTFLOAT max;
  };

  std::vector<ParamInfo> params;

 public:
  MapUI() {}
  virtual ~MapUI() {}

  // Find parameter by label
  FAUSTFLOAT* getParamZone(const char* label) {
    for (auto& p : params) {
      if (p.label == label) return p.zone;
    }
    return nullptr;
  }

  // Set parameter value by label
  void setParamValue(const char* label, FAUSTFLOAT value) {
    FAUSTFLOAT* zone = getParamZone(label);
    if (zone) *zone = value;
  }

  // Get parameter value by label
  FAUSTFLOAT getParamValue(const char* label) {
    FAUSTFLOAT* zone = getParamZone(label);
    return zone ? *zone : 0.0;
  }

  // UI interface implementation
  virtual void openTabBox(const char*) {}
  virtual void openHorizontalBox(const char*) {}
  virtual void openVerticalBox(const char*) {}
  virtual void closeBox() {}

  virtual void addButton(const char* label, FAUSTFLOAT* zone) {
    params.push_back({label, zone, 0, 0, 1});
  }

  virtual void addCheckButton(const char* label, FAUSTFLOAT* zone) {
    params.push_back({label, zone, 0, 0, 1});
  }

  virtual void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) {
    params.push_back({label, zone, init, min, max});
  }

  virtual void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) {
    params.push_back({label, zone, init, min, max});
  }

  virtual void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step) {
    params.push_back({label, zone, init, min, max});
  }

  virtual void addHorizontalBargraph(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void addVerticalBargraph(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT) {}
};

#endif // __FAUST_MINIMAL_H__
