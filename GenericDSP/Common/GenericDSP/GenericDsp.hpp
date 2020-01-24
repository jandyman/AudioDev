//
//  GenericDsp.hpp
//  Acoustify
//
//  Created by Andrew Voelkel on 5/28/18.
//  Copyright © 2018 Setpoint Medical. All rights reserved.
//

#pragma once

#include <stdlib.h>
#include <vector>
#include <iostream>
#include <string>
#include <sstream>

#define uint unsigned int

namespace DspBlocks {

  struct DspError {
    const char *msg;
    DspError(const char *msg) : msg(msg) {}
  };

  struct DspInterface;
  struct PinSpec;
  struct GraphBase;

  /// Encapsulates characteristics of a "wire", including number of channels, buffer
  /// size, and sample rate.

  struct WireSpec {
    uint nChannels = 0;
    uint bufSize = 0;
    float sampleRate = 0;

    WireSpec() { }

    WireSpec(int nChannels, float sampleRate, int bufSize) {
      Init(nChannels, sampleRate, bufSize);
    }

    void Init(int nChannels, float sampleRate, int bufSize) {
      this->nChannels = nChannels;
      this->sampleRate = sampleRate;
      this->bufSize = bufSize;
    }

    bool IsEmpty() {
      return (nChannels == 0);
    }

    void Set(WireSpec ws) {
      if (*this == ws) return;
      if (!IsEmpty()) {
        throw new DspError("Can't set wirespec which is not empty and doesn't match");
      } else {
        Init(ws.nChannels, ws.sampleRate, ws.bufSize);
      }
    }

    float **AllocateBuffers() {
      float** retval = new float*[nChannels];
      for (int i = 0; i < nChannels; i++) {
        retval[i] = new float[bufSize];
      }
      return retval;
    }

    bool operator==(const WireSpec &ws) const {
      return (nChannels == ws.nChannels && bufSize == ws.bufSize && sampleRate == ws.sampleRate);
    }

    bool operator!=(const WireSpec &ws) const {
      return (nChannels != ws.nChannels || bufSize != ws.bufSize || sampleRate != ws.sampleRate);
    }

    const std::string Description() const {
      std::ostringstream strm;
      strm << "nChannels: " << nChannels << " ";
      strm << "SR: " << sampleRate << " ";
      strm << "bufSize: " << bufSize;
      return strm.str();
    }

  };
  
  /*
   
   A block is ready for processing if all it inputs have been processed.
   An output has been processed if its block has been processed
   But in the case of ports, that block is indirect, and must be found through forwarding
   
   When a block is processed, an output buffer is allocated from a pool.
   After a block is processed, each input is checked to see if buffers can be released.
   For each input, the source output is asked whether all it's destinations have been processed.
   In this case, forwarding to a "real" block must work the other direction.
   
   */
  
  /// Specification for a "pin" on a DSP block, including which block it belongs to,
  /// and the index of the pin
  
  struct PinSpec {
    DspInterface* block = nullptr;
    unsigned int pinIdx = 0;
    bool isPort = false;
    
    PinSpec() {}
    
    PinSpec(DspInterface* block, unsigned int pinIdx, int isPort) {
      this->block = block; this->pinIdx = pinIdx; this->isPort = isPort;
    }

    bool IsEmpty() { return (block == nullptr); }
    
    bool operator==(const PinSpec &ps) const {
      return (block == ps.block && pinIdx == ps.pinIdx && isPort == ps.isPort);
    }
    
    bool operator!=(const PinSpec &ps) const {
      return (block != ps.block || pinIdx != ps.pinIdx || isPort != ps.isPort);
    }

  };

  struct Wire {
    int Id = 0;
    PinSpec src;
    std::vector<PinSpec> dst;

    void AddConnection(PinSpec src, PinSpec dst) {
      if (!this->src.IsEmpty() && this->src != src) {
        throw new DspError("Attempt to set source of a wire twice");
      }
      this->src = src;
      this->dst.push_back(dst);
    }

    virtual const std::string Description() const { return ""; }

  };

  struct ConnectionWire : Wire {
    WireSpec wireSpec;
    float** buffers = nullptr;
    int bufferId = -1;

    uint32_t NChannels() { return wireSpec.nChannels; }
    uint32_t BufSize() { return wireSpec.bufSize; }
    float SampleRate() { return wireSpec.sampleRate; }

    virtual const std::string Description() const {
      std::ostringstream strm;
      strm << "bufId: " << bufferId << " ";
      strm << wireSpec.Description() << " ";
      return strm.str();
    }

    ~ConnectionWire() {
      if (buffers != nullptr) {
        for (int i=0; i < wireSpec.nChannels; i++) {
          delete buffers[i];
        }
        delete buffers;
      }
    }

    float **Buffers() { return buffers; }
    bool WireSpecIsEmpty() { return wireSpec.IsEmpty(); }
    WireSpec WireSpec() { return wireSpec; }

  };

  struct Pin;
  struct Pin;
  struct Port;
  struct Port;

  /// Interface specification which all DSP block must implement

  struct DspInterface {
    using string = std::string;
    virtual int nInputPins() = 0;
    virtual Pin& InputPin(int idx) = 0;
    virtual int nOutputPins() = 0;
    virtual Pin& OutputPin(int idx) = 0;
    virtual bool UpdateWireSpecs() = 0;
    virtual bool AllWireSpecsReady() = 0;
    virtual void Init() = 0;
    virtual void Process() = 0;
    virtual const string GetClassName() = 0;
    virtual const string GetInstanceName() = 0;
    virtual void SetInstanceName(const string name) = 0;
    virtual const int GetId() = 0;
    virtual void SetId(const int id) = 0;
    // these are to support heirarchy without forward reference issues
    //virtual int nInputPorts() = 0;
    virtual Pin* InputPort(int idx) = 0;
    //virtual int nOutputPorts() = 0;
    virtual Pin* OutputPort(int idx) = 0;
  };

  /// The pin structure. Encapsulates the WireSpec, buffer pointers, a bufferId for
  /// housekeeping reasons, and a name.

  struct Pin {
    virtual bool IsPort() { return false; }
    ConnectionWire* wire;
  };

  /// A base class for DSP blocks, where reusable functionality can be put

  struct DspBase: DspInterface {
    template<typename T> using vector = std::vector<T>;
    using string = std::string;

    vector<Pin> inputPins;
    vector<Pin> outputPins;
    Pin& InputPin(int idx) override { return inputPins[idx]; }
    Pin& OutputPin(int idx) override { return outputPins[idx]; }
    Pin* InputPort(int idx) override { return nullptr; }
    Pin* OutputPort(int idx) override { return nullptr; }

    int id;
    string instanceName = {""};

    int nInputPins() override { return (int)inputPins.size(); }
    int nOutputPins() override { return (int)outputPins.size(); }

    void Init() override {};
    void Process() override {};

    DspBase(int nInputPins, int nOutputPins) {
      for (int i=0; i < nInputPins; i++) { inputPins.push_back(Pin()); }
      for (int i=0; i < nOutputPins; i++) { outputPins.push_back(Pin()); }
    }

    DspBase(int nInputPins) : DspBase(nInputPins, 1) {}

    DspBase() {}

    ~DspBase() {
      inputPins.clear();
      outputPins.clear();
    }

    const int GetId() override { return id; }
    void SetId(const int id) override { this->id = id; }
    const string GetInstanceName() override { return instanceName; }
    void SetInstanceName(const string name) override { instanceName = name; }

    bool AllWireSpecsReady() override {
      for (auto& pin : inputPins) { if (pin.wire->wireSpec.IsEmpty()) return false; }
      for (auto& pin : outputPins) { if (pin.wire->wireSpec.IsEmpty()) return false; }
      return true;
    }

    // These two functions are helpers for derived classes to propagate WireSpecs

    WireSpec GetFirstWireSpec(vector<Pin>& pins) {
      for (auto& pin : pins) {
        auto ws = pin.wire->WireSpec();
        if (ws.IsEmpty()) {
          return ws;
        }
      }
      return WireSpec();
    }

    bool SetWireSpec(vector<Pin>& pins, WireSpec wireSpec) {
      bool did_something = false;
      for (auto& pin : pins) {
        auto ws = pin.wire->WireSpec();
        if (ws.IsEmpty()) {
          pin.wire->wireSpec = wireSpec;
          did_something = true;
        } else {
          if (ws != wireSpec) {
            throw new DspError("wire spec conflict");
          }
        }
      }
      return did_something;
    }

  };

  // Base class for blocks for which all pins have the same WireSpec

  struct DspBlockSingleWireSpec: DspBase {
    WireSpec sharedWireSpec;

    virtual const string GetClassName() override { return "DspBlockSingleWirespec"; }

    bool UpdateWireSpecs() override {

      // first find any pins with wireSpecs, set shared wireSpec var
      if (sharedWireSpec.IsEmpty()) {
        auto func = [&](Pin &pin) {
          auto ws = pin.wire->wireSpec;
          if (!ws.IsEmpty() && sharedWireSpec.IsEmpty()) {
            sharedWireSpec = ws;
          }
        };
        for (auto &pin : outputPins) { func(reinterpret_cast<Pin &>(pin)); }
        for (auto &pin : inputPins) { func(reinterpret_cast<Pin &>(pin)); }
      }

      if (sharedWireSpec.IsEmpty()) {
        return false;
      }

      // now apply the wireSpec to all pins, detecting conflicts
      bool did_something = false;
      auto checkPin = [&](Pin& pin) {
        auto& pinWs = pin.wire->wireSpec;
        if (sharedWireSpec != pinWs) {
          if (!pinWs.IsEmpty()) {
            throw new DspError("Conflicting wirespecs within block");
          } else {
            pinWs = sharedWireSpec;
            did_something = true;
          }
        }
      };
      for (auto& pin : outputPins) { checkPin(reinterpret_cast<Pin&>(pin)); }
      for (auto& pin : inputPins) { checkPin(reinterpret_cast<Pin&>(pin)); }
      return did_something;
    }

    DspBlockSingleWireSpec(int nInputPins, int nOutputPins) :
    DspBase(nInputPins, nOutputPins) {
    }

  };

  struct DesignContext {
    template<typename T> using vector = std::vector<T>;
    using string = std::string;
    std::ostream& cout = std::cout;

    struct BufferSpec {
      int Id;
      WireSpec wireSpec;
      float **buffers;
      bool free = false;

      BufferSpec(int id, WireSpec ws, float** bufs) {
        this->Id = id;
        wireSpec = ws;
        buffers = bufs;
      }

      bool isCompatible(const WireSpec& ws) {
        return (wireSpec.nChannels == ws.nChannels && wireSpec.bufSize == ws.bufSize);
      }
    };

    vector<DspInterface*> processing_order;
    vector<BufferSpec> bufferPool;
    vector<Wire> designWires;
    vector<ConnectionWire> connectionWires;
    vector<DspInterface*> blocks;
    int bufSpecCnt = 0;
    int IdCounter = 0;

    DesignContext() {
      connectionWires.reserve(200);  // TODO TMP KLUDGE
    }

    void AddBlock(DspInterface* block) {
      if (find(blocks.begin(), blocks.end(), block) == blocks.end()) {
        blocks.push_back(block);
      }
    }

    Wire* DesignWireForOutput(PinSpec& outPinSpec) {
      for (auto& wire : designWires) {
        auto pinSpec = wire.src;
        auto blk = pinSpec.block;
        if (blk == nullptr) continue;
//        Pin* wpin;
//        if (pinSpec.isPort) {
//          if (blk->InputPort(pinSpec.pinIdx) == nullptr) {
//            throw DspError("PinSpec points to port, but block is not a graph");
//          }
//          wpin = blk->InputPort(pinSpec.pinIdx);
//        } else {
//          wpin = &blk->OutputPin(pinSpec.pinIdx);
//        }
        if (outPinSpec == pinSpec) { return &wire; }
//        if (wpin == &pin) { return &wire; }
      }
      return nullptr;
    }

    Wire* DesignWireForInput(PinSpec& dstPinSpec) {
      for (auto& wire : designWires) {
        auto pinSpecs = wire.dst;
        for (auto& pinSpec : pinSpecs) {
          auto blk = pinSpec.block;
          if (blk == nullptr) continue;
          if (dstPinSpec == pinSpec) { return &wire; }
        }
      }
      return nullptr;
    }

    template <class T> T* AddWire(vector<T>& wires) {
      T wire;
      wire.Id = IdCounter++;
      wires.push_back(wire);
      return &wires[wires.size() - 1];
    }

    Wire* AddDesignWire() { return AddWire(designWires); }
    ConnectionWire* AddConnectionWire() {
      return AddWire(connectionWires);
    }

    int GetId(DspInterface* block) {
      auto it = find(blocks.begin(), blocks.end(), block);
      if (it == blocks.end()) {
        throw DspError("Attempt to get ID of block not in DesignContext");
      }
      return it - blocks.begin();
    }

    int GetInstanceId(DspInterface* block) {
      auto className = block->GetClassName();
      int instanceCount = 0;
      for (auto thisBlock : blocks) {
        if (thisBlock == block) {
          return instanceCount;
        } else if (thisBlock->GetClassName() == className) {
          instanceCount++;
        }
      }
      return -1;
    }

    string GetInstanceName(DspInterface* block) {
      return block->GetClassName() + " " + std::to_string(GetInstanceId(block));
    }

    string DescribePinSpec(PinSpec& ps) {
      std::ostringstream ss;
      auto& block = ps.block;
      if (block == NULL) {
        ss << "{No Connection}";
      } else {
        string type = ps.isPort ? "Port " : "Pin ";
        auto name = GetInstanceName(block);
        ss << "{Blk " << name << " " << type << ps.pinIdx << "}";
      }
      return ss.str();
    }

    void DescribeWire(Wire& wire) {
      string wDesc = wire.Description();
      string psDesc = DescribePinSpec(wire.src);
      cout << "ID: " << wire.Id << " Src: " << psDesc << " Dst:";
      for (auto& pinSpec : wire.dst) {
        cout << " " << DescribePinSpec(pinSpec);
      }
      cout << "\n";
    }

    void Describe(bool connectionMode) {
      cout << "Blocks:" << "\n";
      for (auto& blk : blocks) {
        cout << "ID: " << GetId(blk) << " Type: " << GetInstanceName(blk) << "\n";
      }
      cout << "Wires:" << "\n";
      if (connectionMode) {
        for (auto& wire : connectionWires) { DescribeWire(wire); }
      } else {
        for (auto& wire : designWires) { DescribeWire(wire); }
      }
      if (processing_order.size() > 0) {
        cout << "Processing Order: \n";
        for (auto& blk : processing_order) {
          cout << "ID: " << GetId(blk) << " Type: " << blk->GetClassName() << "\n";
        }
        cout << "Wires by Processing Order: \n";
        for (auto& blk : processing_order) {
          for (int i=0; i < blk->nOutputPins(); i++) {
            auto& pin = blk->OutputPin(i);
            DescribeWire(*pin.wire);
          }
        }
      }
    }

    void AllocateOutputBuffer(Pin& pin) {
      bool found_buffer = false;
      auto ws = pin.wire->wireSpec;
      for (auto &bufSpec : bufferPool) {
        if (bufSpec.free && bufSpec.isCompatible(ws)) {
          pin.wire->buffers = bufSpec.buffers;
          pin.wire->bufferId = bufSpec.Id;
          bufSpec.free = false;
          found_buffer = true;
          break;
        }
      }
      if (!found_buffer) {
        float **newBuffers = ws.AllocateBuffers();
        pin.wire->buffers = newBuffers;
        auto newBufSpec = BufferSpec(bufSpecCnt++, ws, newBuffers);
        pin.wire->bufferId = newBufSpec.Id;
        bufferPool.push_back(newBufSpec);
      }
    }

    void FreeBuffer(ConnectionWire* wire) {
      for (auto &bufSpec : bufferPool) {
        if (bufSpec.buffers == wire->buffers) {
          bufSpec.free = true;
        }
      }
    }

  };

  //  Base class of a graph. A graph is itself a block, to support heirarchy. It can
  //  organize and prepare all the blocks within itself. But if it is a "top level"
  //  graph, it can be used standalone by a host

  struct GraphBase: DspInterface {
    template<typename T> using vector = std::vector<T>;

    DesignContext& designContext;

    vector<DspInterface*> blocks;
    vector<Pin> inputPins;
    vector<Pin> outputPins;
    vector<Pin> inputPorts;
    vector<Pin> outputPorts;

    // GraphBase() {}

    GraphBase(DesignContext& dc, int nInputPins, int nOutputPins) : designContext(dc) {
      for (int i=0; i < nInputPins; i++) {
        inputPorts.push_back(Pin());
        inputPins.push_back(Pin());
      }
      for (int i=0; i < nOutputPins; i++) {
        outputPorts.push_back(Pin());
        outputPins.push_back(Pin());
      }
    }

    const string GetClassName() override { return "Graph"; }

    const string GetInstanceName() override { return ""; }
    void SetInstanceName(const string name) override {}
    const int GetId() override { return 0; }
    void SetId(const int id) override {}

    int nInputPins() override { return (int)inputPins.size(); }
    int nOutputPins() override { return (int)outputPins.size(); }

    Pin& InputPin(int idx) override { return inputPins[idx]; }
    Pin& OutputPin(int idx) override { return outputPins[idx]; }
    Pin* InputPort(int idx) override { return &inputPorts[idx]; }
    Pin* OutputPort(int idx) override { return &outputPorts[idx]; }

    void Init() override {};

    // only adds the block if the block wasn't there before
    void AddBlock(DspInterface* block) {
      designContext.AddBlock(block);
      if (block != this) {
        auto it = find(blocks.begin(), blocks.end(), block);
        if (it == blocks.end()) {
          blocks.push_back(block);
        }
      }
    }

    void Connect(DspInterface* src, int srcPinIdx, DspInterface* dst, int dstPinIdx) {
      AddBlock(src);
      AddBlock(dst);
      auto srcPin = PinSpec(src, srcPinIdx, src == this);
      auto dstPin = PinSpec(dst, dstPinIdx, dst == this);
      // if the srcPin has no associated wire, create one
      auto srcWire = designContext.DesignWireForOutput(srcPin);
      if (designContext.DesignWireForInput(dstPin) != nullptr) {
        throw new DspError("attempt to connect output which is already connected");
      }
      if (srcWire == nullptr) {
        srcWire = designContext.AddDesignWire();
      }
      auto srcPinSpec = PinSpec(src, srcPinIdx, src == this);
      auto dstPinSpec = PinSpec(dst, dstPinIdx, dst == this);
      srcWire->AddConnection(srcPinSpec, dstPinSpec);
    }

    void Connect(DspInterface* src, DspInterface* dst) { Connect(src, 0, dst, 0); }

    void Connect(DspInterface* src, int srcPinIdx, DspInterface* dst) {
      Connect(src, srcPinIdx, dst, 0);
    }

    void Connect(DspInterface* src, DspInterface* dst, int dstPinIdx) {
      Connect(src, 0, dst, dstPinIdx);
    }

    void SyncWireSpec(Pin& port, Pin& pin, bool& did_something) {
      if (port.wire == nullptr || pin.wire == nullptr) {
        throw new DspError("unconnected pin while syncing port wire specs");
      }
      WireSpec& ws1 = port.wire->wireSpec;
      WireSpec& ws2 = pin.wire->wireSpec;
      if (ws1.IsEmpty() && !ws2.IsEmpty()) { ws1 = ws2; did_something = true; }
      if (ws2.IsEmpty() && !ws1.IsEmpty()) { ws2 = ws1; did_something = true; }
      else if (ws1 != ws2) {
        throw new DspError("conflicting types while syncing wire specs");
      }
    }

    void SyncPortAndPins() {
      auto func = [&](vector<Pin>& ports, vector<Pin>& pins) {
        for (int i=0; i < pins.size(); i++) {
          bool dummy;
          SyncWireSpec(ports[i], pins[i], dummy);
        }
      };
      func(inputPorts, inputPins);
      func(outputPorts, outputPins);
    }

    /* ------------------ Signal Propagation --------------------

     For each block,

     1. If the wirespec of any pins can be set based on any of the input pins, set it.

     2. If the wirespec of any pins can be set based on any of the output pins, set them.

     3. For each pin, follow through to any other pins, For each pin, if the
     wire spec is blank, set it. If not, check to make sure there is no conflict
     and signal an error if there is one.

     Lather rinse repeat until nothing more can be propagated or we encounter an error
     */

    bool UpdateWireSpecs() override {
      bool did_something = false;
      auto func = [&](vector<Pin>& ports, vector<Pin>& pins) {
        for (int i=0; i < ports.size(); i++) {
          SyncWireSpec(ports[i], pins[i], did_something);
        }
      };
      func(inputPorts, inputPins);
      func(outputPorts, outputPins);
      bool did_something_this_time = false;
      do {
        did_something_this_time = false;
        for (auto& block : blocks) {
          if (block->UpdateWireSpecs()) {
            did_something = true;
            did_something_this_time = true; }
        }
      } while (did_something_this_time);
      func(inputPorts, inputPins);
      func(outputPorts, outputPins);
      if (!AllWireSpecsReady()) {
        throw DspError("can't resolve all WireSpecs for graph");
      }
      return did_something;
    }

    virtual bool AllWireSpecsReady() override {
      // check all contained blocks
      for (auto& block : blocks) {
        if (!block->AllWireSpecsReady()) { return false; }
      }
      return true;
    }

    void Process() override {}  // should never be called

    void Describe(bool connectionMode) { designContext.Describe(connectionMode); }

  };

  struct TopLevelGraph : GraphBase {

    // used for determining processing order
    vector<DspInterface*> sources;
    // master WireSpec
    WireSpec wireSpec;

    TopLevelGraph(DesignContext& dc, WireSpec ws, int nInputPins, int nOutputPins) : wireSpec(ws),
    GraphBase(dc, nInputPins, nOutputPins) {}

    TopLevelGraph(DesignContext& dc, int nInputPins, int nOutputPins) :
    GraphBase(dc, nInputPins, nOutputPins) {}

    virtual void Init(WireSpec wiresSpec) {}

    // When used by a host, it is assumed all WireSpecs are the same. So this setup
    // function set the WireSpecs of all input and output ports of the graph.

    void TopLevelSetup(WireSpec wireSpec) {
      auto func = [&](vector<Pin>& pins) {
        for (auto& pin : pins) {
          pin.wire = new ConnectionWire;
          pin.wire->wireSpec = wireSpec;
        }
      };
      func(inputPins); func(outputPins);
    }

    void TopLevelSetup() {
      assert(!wireSpec.IsEmpty());
      TopLevelSetup(wireSpec);
    }

    void SetInputPortBuffers(float **inputBuffers) {
      inputPorts[0].wire->buffers = inputBuffers;
    }

    float** GetOutputPortBuffers() {
      return outputPorts[0].wire->buffers;
    }

    void SetOutputPortBuffers(float** ptrs, int offset) {
      ConnectionWire& wire = *outputPorts[0].wire;
      for (int i=0; i < wire.wireSpec.nChannels; i++) {
        wire.buffers[i] = &ptrs[i][offset];
      }
    }

    Wire* GetOutputPortWire() {
      return outputPorts[0].wire;
    }

    vector<PinSpec> FlattenDestinationNet(PinSpec& source) {
      vector<PinSpec> dsts;
      auto sourceWire = designContext.DesignWireForOutput(source);
      for (auto& dst : sourceWire->dst) {
        // if destination block is a simple block, just add to dsts
        auto gb = dynamic_cast<GraphBase*>(dst.block);
        if (gb == nullptr) {
          dsts.push_back(dst);
        } else {  // destination block is a subgraph
          vector<PinSpec> nextDsts;
          if (dst.isPort) { // step over the port
            if (dst.block == this) { // end of the line
              dsts.push_back(PinSpec(this, dst.pinIdx, true));
            } else {
              auto nextDstPinSpec = PinSpec(dst.block, dst.pinIdx, false);
              nextDsts = FlattenDestinationNet(nextDstPinSpec);
            }
          } else {
            auto nextDstPinSpec = PinSpec(dst.block, dst.pinIdx, true);
            nextDsts = FlattenDestinationNet(nextDstPinSpec);
          }
          dsts.insert(dsts.end(), nextDsts.begin(), nextDsts.end());
        }
      }
      return dsts;
    }

    Pin& GetSourcePin(PinSpec ps) {
      auto& block = ps.block;
      int idx = ps.pinIdx;
      if (ps.isPort) {
        auto gb = dynamic_cast<GraphBase*>(block);
        if (gb == nullptr) { throw new DspError("Port not connected to GraphBase"); }
        return gb->inputPorts[idx];
      } else {
        return block->OutputPin(idx);
      }
    }

    Pin& GetDestPin(PinSpec ps) {
      auto& block = ps.block;
      int idx = ps.pinIdx;
      if (ps.isPort) {
        auto gb = dynamic_cast<GraphBase*>(block);
        if (gb == nullptr) { throw new DspError("Port not connected to GraphBase"); }
        return gb->outputPorts[idx];
      } else {
        return block->InputPin(idx);
      }
    }

    // This function creates a second set of wires which bypass the ports of internal
    // graphs, essentially flattening the graph, which make subsequent operations simpler

    void CompleteComposition() {
      designContext.connectionWires.clear();
      // utility function to create and add wire
      auto addWire = [&](PinSpec src, vector<PinSpec> dst) {
        auto wire = designContext.AddConnectionWire();
        wire->dst = dst;
        wire->src = src;

        // now patch the blocks to use the wire
        GetSourcePin(wire->src).wire = wire;
        for (auto& dst : wire->dst) {
          GetDestPin(dst).wire = wire;
        }
      };
      // flatten destinations from all input ports
      for (int i=0; i < inputPorts.size(); i++) {
        PinSpec src(this, i, true);
        auto dsts = FlattenDestinationNet(src);
        addWire(src, dsts);
      }
      // flatten destination for all blocks in designContext
      for (auto block : designContext.blocks) {
        if (dynamic_cast<GraphBase*>(block) == nullptr) { // ignore subgraphs
          for (int i=0; i < block->nOutputPins(); i++) {
            auto outPin = block->OutputPin(i);
            PinSpec src = PinSpec(block, i, false);
            auto dstPinSpecs = FlattenDestinationNet(src);
            addWire(src, dstPinSpecs);
          }
        }
      }
      // determine processing order
      DetermineProcessingOrder();
    }

    // ------------------ Graph Preparation ---------------------

    void PrepareForOperation(WireSpec ws) {
      TopLevelSetup(ws);
      UpdateWireSpecs();
      InitBlocks();
    }

    bool HasBeenProcessed(DspInterface* block) {
      // the outermost ports don't need processing
      if (block == this) { return true; }
      auto &po = designContext.processing_order;
      return (find(po.begin(), po.end(), block) != po.end());
      return false;
    }

    // Look for blocks which are either pure sources by nature (they have no input pins),
    // or have all their input pins connected to input ports. Input ports themselves are
    // not considered sources, because they do not need to be processed and already are
    // connected to buffers.

    void FindSources() {
      sources.clear();
      for (DspInterface* blk : designContext.blocks) {
        if (!dynamic_cast<GraphBase*>(blk)) {  // ignore subgraphs
          if (blk->nInputPins() == 0) { sources.push_back(blk); }
          else {
            for (int i=0; i < blk->nInputPins(); i++) {
              Pin& pin = blk->InputPin(i);
              if (pin.wire->src.block != this) { continue; }
              sources.push_back(blk);
            }
          }
        }
      }
    }

    // A block can be processed if all its input data is ready, which means that all the
    // blocks connected to its input pins have already been processed. Input ports by
    // definition have already been processed, to make sure they won't be in processing_order.
    // OutputPorts are also not processed, since they merely forward buffer pointers and
    // don't copy data.

    bool CanProcessBlock(DspInterface* block) {
      for (int i=0; i < block->nInputPins(); i++) {
        auto& pin = block->InputPin(i);
        if (!HasBeenProcessed(pin.wire->src.block)) { return false; }
      }
      return true;
    }

    void MarkAsProcessed(DspInterface* block) {
      designContext.processing_order.push_back(block);
    }

    // After a block has been processed, we usually will be able to reuse the input
    // buffers, because they are not needed anymore. One exception to this is when
    // another block that has not been processed is also connected to the pin which
    // the source for our input pin(s). Another is when the source is an input port,
    // and we are at "top level", meaning the buffer was supplied by the host.

    void FreeInputBuffers(DspInterface* block) {
      for (int i=0; i < block->nInputPins(); i++) {
        auto& wire = block->InputPin(i).wire;
        bool canFree = true;
        for (auto& dst : wire->dst) {
          if (HasBeenProcessed(dst.block)) continue;
          canFree = false;
        }
        if (canFree) { designContext.FreeBuffer(wire); }
      }
    }

    /*
     Find a block which is a source. It starts the list.
     for each output, find what it is connected to. If we are the only input of that next block,
     continue until we either reach a sink, or find a block with an input which hasn't
     been processed yet. as we go, mark each processed block
     */

    void DetermineProcessingOrder(DspInterface* block) {
      if (!HasBeenProcessed(block)) {
        if (CanProcessBlock(block)) {
          MarkAsProcessed(block);
          for (int i=0; i < block->nOutputPins(); i++) {
            auto& pin = block->OutputPin(i);
            for (auto& sink : pin.wire->dst) {
              auto& nextBlock = sink.block;
              DetermineProcessingOrder(nextBlock);
            }
          }
        }
      }
    }

    void DetermineProcessingOrder() {
      FindSources();
      for (auto& block : sources) {
        DetermineProcessingOrder(block);
      }
      // ConnectOutputPorts();
    }

    void AllocateOutputBuffers() {
      for (auto& block: designContext.processing_order) {
        AllocateOutputBuffers(block);
        FreeInputBuffers(block);
      }
    }

    void AllocateOutputBuffers(DspInterface* block) {
      for (int i=0; i < block->nOutputPins(); i++) {
        auto& pin = block->OutputPin(i);
        designContext.AllocateOutputBuffer(pin);
      }
    }

    void InitBlocks() {
      for (auto& block: designContext.blocks) { block->Init(); }
    }

    void Process() override {
      for (auto& block: designContext.processing_order) { block->Process(); }
    }

  };

}

