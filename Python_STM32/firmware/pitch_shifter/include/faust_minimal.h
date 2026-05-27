#pragma once

// Bare-metal Faust support — no STL.
// Overrides the desktop version in python/bindings/ via include path ordering
// (firmware include/ comes before python/bindings/).

#ifndef FAUSTFLOAT
#define FAUSTFLOAT float
#endif

#include <cstring>

struct Meta {
  virtual ~Meta() {}
  virtual void declare(const char* key, const char* value) = 0;
};

class UI {
public:
  virtual ~UI() {}
  virtual void openTabBox(const char*) {}
  virtual void openHorizontalBox(const char*) {}
  virtual void openVerticalBox(const char*) {}
  virtual void closeBox() {}
  virtual void addButton(const char*, FAUSTFLOAT*) {}
  virtual void addCheckButton(const char*, FAUSTFLOAT*) {}
  virtual void addVerticalSlider(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void addHorizontalSlider(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void addNumEntry(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void addHorizontalBargraph(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void addVerticalBargraph(const char*, FAUSTFLOAT*, FAUSTFLOAT, FAUSTFLOAT) {}
  virtual void declare(FAUSTFLOAT*, const char*, const char*) {}
};

class dsp {
public:
  virtual ~dsp() {}
  virtual int getNumInputs() = 0;
  virtual int getNumOutputs() = 0;
  virtual void buildUserInterface(UI* ui) = 0;
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

// Minimal param-registration UI — fixed-size table, no heap.
#define FAUST_MAX_PARAMS 16
struct MapUI : public UI {
  struct Entry { const char* label; FAUSTFLOAT* zone; };
  Entry entries[FAUST_MAX_PARAMS];
  int count = 0;

  void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) override {
    if (count < FAUST_MAX_PARAMS) entries[count++] = {label, zone};
  }
  void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) override {
    if (count < FAUST_MAX_PARAMS) entries[count++] = {label, zone};
  }
  void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT, FAUSTFLOAT) override {
    if (count < FAUST_MAX_PARAMS) entries[count++] = {label, zone};
  }

  void setParamValue(const char* label, FAUSTFLOAT value) {
    for (int i = 0; i < count; ++i)
      if (!strcmp(entries[i].label, label)) { *entries[i].zone = value; return; }
  }
  FAUSTFLOAT getParamValue(const char* label) const {
    for (int i = 0; i < count; ++i)
      if (!strcmp(entries[i].label, label)) return *entries[i].zone;
    return 0.0f;
  }
};
