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

  struct PinSpec {
    int blockId = -1;
    int pinIdx = -1;
    bool isPort = false;

    PinSpec(int id, int idx, bool isPort) : blockId(id), pinIdx(idx), isPort(isPort) {}
    PinSpec() {}
    bool operator==(const PinSpec &ps) const {
      return (blockId == ps.blockId && pinIdx == ps.pinIdx && isPort == ps.isPort);
    }
    bool operator!=(const PinSpec &ps) const { return !(*this == ps); }
  };

  struct DspNode {
    using string = std::string;
    virtual int NInputPins() = 0;
    virtual int NOutputPins() = 0;
    virtual const string GetClassName() = 0;
    virtual const string GetInstanceName() = 0;
    virtual void SetInstanceName(const string name) = 0;
    const int GetId() { return id; }
    void SetId(const int id) { this->id = id; }
    virtual bool IsGraph() = 0;
  private:
    int id = -1;
  };

  struct DspBlock;
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

    void FreeBuffers(float** buffers) {
      for (int i = 0; i < nChannels; i++) {
        delete buffers[i];
      }
      delete buffers;
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

  struct Wire {
    int Id = 0;
    PinSpec src = {-1, 0, false};  // set block to illegal value initially
    std::vector<PinSpec> dst;

    void AddConnection(PinSpec src, PinSpec dst) {
      if (this->src.blockId != -1 && this->src != src) {
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

    float **Buffers() { return buffers; }
    bool WireSpecIsEmpty() { return wireSpec.IsEmpty(); }
    WireSpec WireSpec() { return wireSpec; }

  };

  struct Pin;
  struct Pin;
  struct Port;
  struct Port;

  /// Interface specification which all DSP block must implement

  struct DspBlock : DspNode {
    using string = std::string;
    virtual Pin& InputPin(int idx) = 0;
    virtual Pin& OutputPin(int idx) = 0;
    virtual bool UpdateWireSpecs() = 0;
    virtual bool AllWireSpecsReady() = 0;
    virtual void Init() = 0;
    virtual void Process() = 0;
  };

  /// The pin structure. Encapsulates the WireSpec, buffer pointers, a bufferId for
  /// housekeeping reasons, and a name.

  struct Pin {
    virtual bool IsPort() { return false; }
    ConnectionWire* wire;
  };

  /// A base class for DSP blocks, where reusable functionality can be put

  struct DspBase: DspBlock {
    template<typename T> using vector = std::vector<T>;
    using string = std::string;

    vector<Pin> inputPins;
    vector<Pin> outputPins;
    Pin& InputPin(int idx) override { return inputPins[idx]; }
    Pin& OutputPin(int idx) override { return outputPins[idx]; }

    int id;
    string instanceName = {""};

    int NInputPins() override { return (int)inputPins.size(); }
    int NOutputPins() override { return (int)outputPins.size(); }
    bool IsGraph() override { return true; }

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

    vector<DspBlock*> processing_order;
    vector<BufferSpec> bufferPool;
    vector<Wire> designWires;
    vector<ConnectionWire> connectionWires;
    vector<DspNode*> blocks;
    int bufSpecCnt = 0;
    int WireIdCounter = 0;
    int blockCounter = 0;

//    DesignContext();
    DesignContext() {
      connectionWires.reserve(200);  // TODO TMP KLUDGE
      blocks.reserve(200);           // TODO TMP KLUDGE
    }

    ~DesignContext() {
      // FreeBufferPool();
    }

    void AddBlock(DspNode* block) {
      if (find(blocks.begin(), blocks.end(), block) == blocks.end()) {
        block->SetId(blockCounter++);
        blocks.push_back(block);
      }
    }

    DspNode* GetBlock(int id) { return blocks[id]; }

    Wire* DesignWireForOutput(PinSpec& outPinSpec) {
      for (auto& wire : designWires) {
        auto pinSpec = wire.src;
        auto blk = GetBlock(pinSpec.blockId);
        if (blk == nullptr) continue;
        if (outPinSpec == pinSpec) { return &wire; }
      }
      return nullptr;
    }

    Wire* DesignWireForInput(PinSpec& dstPinSpec) {
      for (auto& wire : designWires) {
        auto pinSpecs = wire.dst;
        for (auto& pinSpec : pinSpecs) {
          auto blk = GetBlock(pinSpec.blockId);
          if (blk == nullptr) continue;
          if (dstPinSpec == pinSpec) { return &wire; }
        }
      }
      return nullptr;
    }

    template <class T> T* AddWire(vector<T>& wires) {
      T wire;
      wire.Id = WireIdCounter++;
      wires.push_back(wire);
      return &wires[wires.size() - 1];
    }

    Wire* AddDesignWire() { return AddWire(designWires); }
    ConnectionWire* AddConnectionWire() {
      return AddWire(connectionWires);
    }

    int GetId(DspNode* block) {
      auto it = find(blocks.begin(), blocks.end(), block);
      if (it == blocks.end()) {
        throw DspError("Attempt to get ID of block not in DesignContext");
      }
      return it - blocks.begin();
    }

    int GetInstanceId(DspNode* block) {
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

    string GetInstanceName(DspNode* block) {
      return block->GetClassName() + " " + std::to_string(GetInstanceId(block));
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

    void FreeBufferPool() {
      for (auto& bufSpec : bufferPool) {
        bufSpec.wireSpec.FreeBuffers(bufSpec.buffers); 
      }
    }

    int ProcessingOrderPosition(DspBlock* block) {
      auto it = std::find(processing_order.begin(), processing_order.end(), block);
      return std::distance(processing_order.begin(), it);
    }

  };

  //  Base class of a graph. A graph is itself a block, to support heirarchy. It can
  //  organize and prepare all the blocks within itself. But if it is a "top level"
  //  graph, it can be used standalone by a host

  struct GraphBase: DspNode {
    template<typename T> using vector = std::vector<T>;

    DesignContext* dc;
    vector<DspNode*> blocks;
    int nInputPins;
    int nOutputPins;

    GraphBase(DesignContext* dc, int nInputPins, int nOutputPins) :
    dc(dc), nInputPins(nInputPins), nOutputPins(nOutputPins) { }

    const string GetClassName() override { return "Graph"; }
    const string GetInstanceName() override { return ""; }
    void SetInstanceName(const string name) override {}

    int NInputPins() override { return nInputPins; }
    int NOutputPins() override { return nOutputPins; }
    bool IsGraph() override { return true; }

    // only adds the block if the block wasn't there before
    void AddBlock(DspNode* block) {
      dc->AddBlock(block);
      if (block != this) {
        auto it = find(blocks.begin(), blocks.end(), block);
        if (it == blocks.end()) {
          blocks.push_back(block);
        }
      }
    }

    void Connect(DspNode* src, int srcPinIdx, DspNode* dst, int dstPinIdx) {
      AddBlock(src);
      AddBlock(dst);
      auto srcPinSpec = PinSpec(src->GetId(), srcPinIdx, src == this);
      auto dstPinSpec = PinSpec(dst->GetId(), dstPinIdx, dst == this);
      // if the srcPin has no associated wire, create one
      auto srcWire = dc->DesignWireForOutput(srcPinSpec);
      if (dc->DesignWireForInput(dstPinSpec) != nullptr) {
        throw new DspError("attempt to connect output which is already connected");
      }
      if (srcWire == nullptr) {
        srcWire = dc->AddDesignWire();
      }
      srcWire->AddConnection(srcPinSpec, dstPinSpec);
    }

    void Connect(DspNode* src, DspNode* dst) { Connect(src, 0, dst, 0); }

    void Connect(DspNode* src, int srcPinIdx, DspNode* dst) {
      Connect(src, srcPinIdx, dst, 0);
    }

    void Connect(DspNode* src, DspNode* dst, int dstPinIdx) {
      Connect(src, 0, dst, dstPinIdx);
    }

  };

  struct TopLevelGraph : GraphBase {
    std::ostream& cout = std::cout;
    
    vector<DspNode*> sources;  // used for determining processing order
    WireSpec wireSpec;         // master WireSpec
    vector<Pin> inputPins;
    vector<Pin> outputPins;
    vector<Pin> inputPorts;
    vector<Pin> outputPorts;

    TopLevelGraph(WireSpec ws, int nInputPins, int nOutputPins) :
    TopLevelGraph(nInputPins, nOutputPins) {
      wireSpec = ws;
    }

    TopLevelGraph(int nInputPins, int nOutputPins) :
    GraphBase(dc, nInputPins, nOutputPins) {
      inputPins = vector<Pin>(nInputPins);
      outputPins = vector<Pin>(nOutputPins);
      inputPorts = vector<Pin>(nInputPins);
      outputPorts = vector<Pin>(nOutputPins);
      dc = new DesignContext();
      dc->AddBlock(this);
    }

    ~TopLevelGraph() {
      delete dc;
    }

    virtual void Init(WireSpec wiresSpec) {}

    // When used by a host, it is assumed all WireSpecs are the same. So this setup
    // function sets the WireSpecs of all input and output ports of the graph.

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

    DspNode* GetBlock(int id) { return dc->GetBlock(id); }

    vector<PinSpec> FlattenDestinationNet(PinSpec& source) {
      vector<PinSpec> dsts;
      auto sourceWire = dc->DesignWireForOutput(source);
      for (auto& dst : sourceWire->dst) {
        // if destination block is a simple block, just add to dsts
        auto gb = dynamic_cast<GraphBase*>(GetBlock(dst.blockId));
        if (gb == nullptr) {
          dsts.push_back(dst);
        } else {  // destination block is a subgraph
          vector<PinSpec> nextDsts;
          if (dst.isPort) { // step over the port
            if (GetBlock(dst.blockId) == this) { // end of the line
              dsts.push_back(PinSpec(dst.blockId, dst.pinIdx, true));
            } else {
              auto nextDstPinSpec = PinSpec(dst.blockId, dst.pinIdx, false);
              nextDsts = FlattenDestinationNet(nextDstPinSpec);
            }
          } else {
            auto nextDstPinSpec = PinSpec(dst.blockId, dst.pinIdx, true);
            nextDsts = FlattenDestinationNet(nextDstPinSpec);
          }
          dsts.insert(dsts.end(), nextDsts.begin(), nextDsts.end());
        }
      }
      return dsts;
    }

    Pin& GetSourcePin(PinSpec ps) {
      auto* block = GetBlock(ps.blockId);
      int idx = ps.pinIdx;
      if (block == this) {
        return inputPorts[idx];
      } else {
        if (ps.isPort) { throw new DspError("can't get Source Pin for a graph"); }
        auto gb = dynamic_cast<DspBlock*>(block);
        if (gb == nullptr) { throw new DspError("GetSourcePin: Expecting a Block"); }
        return gb->OutputPin(ps.pinIdx);
      }
    }

    Pin& GetDestPin(PinSpec ps) {
      auto* block = GetBlock(ps.blockId);
      int idx = ps.pinIdx;
      if (block == this) {
        return outputPorts[idx];
      } else {
        if (ps.isPort) { throw new DspError("can't get Destination Pin for a graph"); }
        auto gb = dynamic_cast<DspBlock*>(block);
        if (gb == nullptr) { throw new DspError("GetDestPin: Expecting a Block"); }
        return gb->InputPin(ps.pinIdx);
      }
    }

    // This function creates a second set of wires which bypass the ports of internal
    // graphs, essentially flattening the graph, which make subsequent operations simpler

    void CompleteComposition() {
      dc->connectionWires.clear();
      // utility function to create and add wire
      auto addWire = [&](PinSpec src, vector<PinSpec> dst) {
        auto wire = dc->AddConnectionWire();
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
        PinSpec src(this->GetId(), i, true);
        auto dsts = FlattenDestinationNet(src);
        addWire(src, dsts);
      }
      // flatten destination for all blocks in designContext
      for (auto block : dc->blocks) {
        auto bptr = dynamic_cast<DspBlock*>(block);
        if (bptr != nullptr) { // ignore subgraphs
          for (int i=0; i < block->NOutputPins(); i++) {
            auto outPin = bptr->OutputPin(i);
            PinSpec src = PinSpec(bptr->GetId(), i, false);
            auto dstPinSpecs = FlattenDestinationNet(src);
            addWire(src, dstPinSpecs);
          }
        }
      }
      // determine processing order
      DetermineProcessingOrder();
    }

    // ------------------ Graph Preparation ---------------------

    /* ------------------ Signal Propagation --------------------

     For each block,

     1. If the wirespec of any pins can be set based on any of the input pins, set it.

     2. If the wirespec of any pins can be set based on any of the output pins, set them.

     3. For each pin, follow through to any other pins, For each pin, if the
     wire spec is blank, set it. If not, check to make sure there is no conflict
     and signal an error if there is one.

     Lather rinse repeat until nothing more can be propagated or we encounter an error
     */

    DspBlock* AssertIsBlock(DspNode* node) {
      auto bptr = dynamic_cast<DspBlock*>(node);
      if (bptr == nullptr) {
        throw DspError("Expecting Dsp Block, got a graph");
      }
      return bptr;
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

    bool UpdateWireSpecs() {
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
        for (auto& node : dc->processing_order) {
          auto block = AssertIsBlock(node);
          if (block->UpdateWireSpecs()) {
            did_something = true;
            did_something_this_time = true;
          }
        }
      } while (did_something_this_time);
      func(inputPorts, inputPins);
      func(outputPorts, outputPins);
      if (!AllWireSpecsReady()) {
        throw DspError("can't resolve all WireSpecs for graph");
      }
      return did_something;
    }

    virtual bool AllWireSpecsReady() {
      bool allReady = true;
      // check all contained blocks
      for (auto& node : dc->blocks) {
        auto block = dynamic_cast<DspBlock*>(node);
        if (block) {
          if (!block->AllWireSpecsReady()) {
            return false;
          }
        }
      }
      return true;
    }

    void PrepareForOperation(WireSpec ws) {
      TopLevelSetup(ws);
      UpdateWireSpecs();
      AllocateBuffers();
      InitBlocks();
    }

    bool HasBeenProcessed(DspNode* block) {
      if (block == this) { return true; }
      auto bptr = AssertIsBlock(block);
      // the outermost ports don't need processing
      auto &po = dc->processing_order;
      return (find(po.begin(), po.end(), block) != po.end());
      return false;
    }

    // Look for blocks which are either pure sources by nature (they have no input pins), 
    // or have all inputs connected to the top level graph ports.

    void FindSources() {
      sources.clear();
      for (DspNode* node : dc->blocks) {
        auto blk = dynamic_cast<DspBlock*>(node);
        if (blk) {  // ignore subgraphs
          bool addToSources = true;
          for (int i=0; i < blk->NInputPins(); i++) {
            auto pin = blk->InputPin(i);
            if (GetBlock(pin.wire->src.blockId) != this) {
              addToSources = false;
              break;
            }
          }
          if (addToSources) {
            sources.push_back(blk);
          }
        }
      }
    }

    // A block can be processed if all its input data is ready, which means that all the
    // blocks connected to its input pins have already been processed. Input ports by
    // definition have already been processed, to make sure they won't be in processing_order.
    // OutputPorts are also not processed, since they merely forward buffer pointers and
    // don't copy data.

    bool CanProcessBlock(DspBlock* node) {
      auto block = AssertIsBlock(node);
      for (int i=0; i < block->NInputPins(); i++) {
        auto& pin = block->InputPin(i);
        if (!HasBeenProcessed(GetBlock(pin.wire->src.blockId))) { return false; }
      }
      return true;
    }

    void MarkAsProcessed(DspBlock* node) {
      auto block = AssertIsBlock(node);
      dc->processing_order.push_back(block);
    }

    // After a block has been processed, we usually will be able to reuse the input
    // buffers, because they are not needed anymore. One exception to this is when
    // another block that has not been processed is also connected to the pin which
    // the source for our input pin(s). Another is when the source is an input port,
    // and we are at "top level", meaning the buffer was supplied by the host.

    void FreeInputBuffers(DspBlock* block) {
      int proc_position = dc->ProcessingOrderPosition(block);
      for (int i=0; i < block->NInputPins(); i++) {
        auto& wire = block->InputPin(i).wire;
        for (auto& dst : wire->dst) {
          auto dst_ptr = AssertIsBlock(GetBlock(dst.blockId));
          int dst_position = dc->ProcessingOrderPosition(dst_ptr);
          if (dst_position <= proc_position) continue;
          return;
        }
        if (dc->GetBlock(wire->src.blockId) == this) {
          return;
        }
        dc->FreeBuffer(wire);
      }
    }

    /*
     Find a block which is a source. It starts the list.
     for each output, find what it is connected to. If we are the only input of that next block,
     continue until we either reach a sink, or find a block with an input which hasn't
     been processed yet. as we go, mark each processed block
     */

    void DetermineProcessingOrder(DspBlock* block) {
      if (!HasBeenProcessed(block)) {
        if (CanProcessBlock(block)) {
          MarkAsProcessed(block);
          for (int i=0; i < block->NOutputPins(); i++) {
            auto& pin = block->OutputPin(i);
            for (auto& sink : pin.wire->dst) {
              auto* nextBlock = GetBlock(sink.blockId);
              if (nextBlock == this) continue;
              DetermineProcessingOrder(AssertIsBlock(nextBlock));
            }
          }
        }
      }
    }

    void DetermineProcessingOrder() {
      FindSources();
      for (auto& block : sources) {
        DetermineProcessingOrder(AssertIsBlock(block));
      }
    }

    void AllocateBuffers() {
      for (auto& block: dc->processing_order) {
        AllocateOutputBuffers(block);
        FreeInputBuffers(block);
        Describe(true);   // tmp
      }
    }

    void AllocateOutputBuffers(DspBlock* block) {
      for (int i=0; i < block->NOutputPins(); i++) {
        auto& pin = block->OutputPin(i);
        dc->AllocateOutputBuffer(pin);
      }
    }

    void InitBlocks() {
      for (auto& block : dc->processing_order) {
        AssertIsBlock(block)->Init();
      }
    }

    void Process() {
      for (auto& block : dc->processing_order) {
        block->Process();
      }
    }

    string DescribePinSpec(PinSpec& ps) {
      std::ostringstream ss;
      auto* block = GetBlock(ps.blockId);
      string type = ps.isPort ? "Port " : "Pin ";
      auto name = dc->GetInstanceName(block);
      ss << "{Blk " << name << " " << type << ps.pinIdx << "}";
      return ss.str();
    }

    void DescribeWire(Wire& wire, bool bufferId = false, bool wireSpec = false) {
      string wDesc = wire.Description();
      string psDesc = DescribePinSpec(wire.src);
      auto* cWire = dynamic_cast<ConnectionWire*>(&wire);
      cout << "ID: " << wire.Id;
      if (cWire != nullptr) {
        if (bufferId) { cout << " BufId: " << cWire->bufferId; }
        if (wireSpec) { cout << " " << cWire->wireSpec.Description(); }
      }
      cout << " Src: " << psDesc << " Dst:";
      for (auto& pinSpec : wire.dst) {
        cout << " " << DescribePinSpec(pinSpec);
      }
      cout << "\n";
    }

    void Describe(bool bufferIds = false, bool wireSpecs = false) {
      cout << "\nBlocks:" << "\n";
      auto& dc = *this->dc;
      for (auto& blk : dc.blocks) {
        cout << "ID: " << dc.GetId(blk) << " Type: " << dc.GetInstanceName(blk) << "\n";
      }
      if (dc.processing_order.size() > 0) {
        cout << "\nProcessing Order: \n";
        for (auto& blk : dc.processing_order) {
          cout << "ID: " << dc.GetId(blk) << " Type: " << blk->GetClassName() << "\n";
        }
        cout << "\nWires by Processing Order: \n";
        for (auto& blk : dc.processing_order) {
          for (int i = 0; i < blk->NOutputPins(); i++) {
            auto& pin = blk->OutputPin(i);
            DescribeWire(*pin.wire, bufferIds, wireSpecs);
          }
        }
      } else {
        cout << "\nWires:" << "\n";
        for (auto& wire : dc.designWires) {
          DescribeWire(wire);
        }
      }
    }

  };

}

