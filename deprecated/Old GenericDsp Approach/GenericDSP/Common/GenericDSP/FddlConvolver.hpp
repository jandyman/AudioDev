#pragma once

#include <Accelerate/Accelerate.h>
#include <mach/mach_time.h>
#include <algorithm>
#include <string>
#include "MiscDsp.hpp"

namespace AWV {
  
  /**
   This class is to support multiple convolvers which share an input buffer. The buffer
   needs to be large enough to support the largest convolver operating in ping pong
   mode, but the write into the buffer will happen with a block size used by the 
   AudioProc function
   
   We want any convolvers with smaller block sizes to be able to share the input buffer, 
   doing appropriate address manipulation to select the proper sub-areas of the master 
   input buffer.
   
   Reading from the master buffer is done by the individual convolvers. The individual
   convolvers view the master buffer as being divided into sectors which correspond to
   the buffer size for the convolver. So an individual convolver must always be able to
   find the sector which immediately precedes the sector into which the Audio Callback
   routine is writing arriving audio data.
   */
  
  struct MasterInBuf { // meant for circular buffers of size 2^N
    float* buffer;     // base pointer of storage
    int writeIdx;
    int log2Size;
    int size;
    int wrapMask;
    int log2BufSize;   // log 2 of size of write sectors
    int bufSize;       // size of write sectors
    int bufMask;
    
    void init(int log2Siz, int log2bufSiz) {
      this->log2Size = log2Siz;
      this->log2BufSize = log2bufSiz;
      size = 1<<log2Siz;
      wrapMask = size-1;
      bufSize = 1<<log2bufSiz;
      bufMask = bufSize-1;
      buffer = new float[size]();
      writeIdx = 0;
    }
    
    ~MasterInBuf() { if (buffer != NULL) delete buffer; }
    
    void write(float* data, int cnt) {
      using namespace std;
      if (size >= cnt + writeIdx) { // simple linear copy
        copy(data, data+cnt, &buffer[writeIdx]);
      } else {
        int hiCnt = writeIdx + cnt + 1 - size;
        copy(data, data+hiCnt, &buffer[writeIdx]);
        copy(data+hiCnt, data+cnt, buffer); 
      }
      writeIdx = (writeIdx + cnt) & wrapMask;
    }
    
    int getIdx(int start, int cnt) {
      // add in Size to accommodate cnt being negative
      return (start + cnt + size) & wrapMask;
    }
    
    int getIdx(int offset) { return (getIdx(writeIdx, offset)); }
    int getPrevIdx(int offset) { return getIdx(offset-bufSize); }
    float* getPrevPtr(int offset) { return &buffer[getPrevIdx(offset)]; }
    
    int sectNum(int log2nSects) {
      return writeIdx >> (log2Size-log2nSects);
    }
    
  };  // MasterInBuf
  
  /**
   FFT Descriptor. Encapsulates useful information for performing FFTs - the block size, 
   the log base 2 of the block size, and the FFTSetup structure used by the vDSP fft
   functions.
   */
  
  struct FftDesc {
    int log2blkSize;
    int blkSize;
    FFTSetup setup = NULL;
    
    FftDesc(int log2blkSize) : log2blkSize(log2blkSize) {
      blkSize = 1<<log2blkSize;
      setup = vDSP_create_fftsetup(log2blkSize, kFFTRadix2);
    }
    
    ~FftDesc() {
      if (setup != NULL) { vDSP_destroy_fftsetup(setup); }
    }
    
  };  // FftDesc
  
  /**
   Frequency Domain Block Array. A building block class to produce a list of blocks of
   frequency domain data. Contains an array of DSPSplitComplex objects and an FftDesc
   object which is used by the vDSP fft functions to convert time domain data into
   frequency domain data to store in the block array.
   */
  
  class FdBlockArray {
    
  public:
    
    FdBlockArray(FftDesc* desc, int nBlocks) {
      init(desc, nBlocks);
    }
    
    FdBlockArray(FftDesc* desc, int nSamples, int nExtraBlocks) {
      fftDesc = desc;
      int nBlocks = blocksNeeded(nSamples) + nExtraBlocks;
      init(desc, nBlocks);
    }
    
    int getNBlocks() { return nBlocks; }
    
    static int blocksNeeded(FftDesc *desc, int nSamples) {
      int bufSize = desc->blkSize/2;
      return ceil((float)nSamples / bufSize);
    }
    
    int blocksNeeded(int nSamples) {
      return FdBlockArray::blocksNeeded(fftDesc, nSamples);
    }
    
    void changeLength(int nBlocks) {
      if (nBlocks != this->nBlocks) {
        auto oldBlocks = blocks; int oldNBLocks = nBlocks;
        auto newBlocks = new DSPSplitComplex[nBlocks];
        for (int blk=0; blk < nBlocks; blk++) {
          newBlocks[blk].realp = new float[fftDesc->blkSize]();
          newBlocks[blk].imagp = new float[fftDesc->blkSize]();
        }
        // copy old data into new storage
        for (int blk=0; blk < this->nBlocks; blk++) {
          memcpy(blocks[blk].realp, newBlocks[blk].realp, sizeof(float) * fftDesc->blkSize);
          memcpy(blocks[blk].imagp, newBlocks[blk].imagp, sizeof(float) * fftDesc->blkSize);
        }
        // make sure things work in case a render cycle interrupts the update
        if (oldNBLocks > nBlocks) {
          this->nBlocks = nBlocks; blocks = newBlocks;
        } else {
          blocks = newBlocks; this->nBlocks = nBlocks;
        }
        blocks = newBlocks;
        deAlloc(oldBlocks, oldNBLocks);
      }
    }
    
  protected:
    
    FftDesc* fftDesc;
    int nBlocks;
    DSPSplitComplex *blocks;
    
    ~FdBlockArray() {
      deAlloc(blocks, nBlocks);
    }
    
    void init(FftDesc* desc, int nBlocks) {
      this->nBlocks = nBlocks;
      fftDesc = desc;
      blocks = new DSPSplitComplex[nBlocks]();
      // allocate and initialize FD storage
      for (int blk=0; blk<nBlocks; blk++) {
        blocks[blk].realp = new float[fftDesc->blkSize]();
        blocks[blk].imagp = new float[fftDesc->blkSize]();
      }
    }
    
    void deAlloc(DSPSplitComplex *blocks, int nBlocks) {
      // deallocate and initialize FD storage
      for (int blk=0; blk<nBlocks; blk++) {
        delete blocks[blk].realp;
        delete blocks[blk].imagp;
      }
      delete blocks;
    }
    
    
    void realFFT(float *input, int blkIdx) {
      Math::RealFFT(fftDesc->setup, fftDesc->log2blkSize, input, &blocks[blkIdx]);
    }
    
  };  // FdBlockArray
  
  class FdImpulse : public FdBlockArray {
    
  public:
    
    /** 
     Initializes the block array with FD representation of 2:1 overlapping blocks of
     the impulse response. Thus, blkSize is twice the size of the buffer size for
     actual audio processing. 
     
     In the first block, the first half of the TD domain data is zero (represents the 
     "previous" impulse response). In the very last block, the second half of the TD data 
     is zero. Thus, an "extra" block is needed at beginning and end.
     */
    
    FdImpulse(FftDesc* desc, float *data, int nSamples) :
    FdBlockArray(desc, nSamples, 2) { // extra block needed at beginning and end
      using namespace std;
      fftDesc = desc;
      int bufSize = fftDesc->blkSize / 2;
      float fftIn[fftDesc->blkSize];
      auto dst = &fftIn[bufSize];
      for (int idx=0; idx<nBlocks-1; idx++) {
        auto src = &data[bufSize * idx];
        if (nSamples < bufSize) { // last buffer, incomplete
          memset(&fftIn[bufSize], 0, bufSize * sizeof(float));
          std::fill(dst, dst+bufSize, 0);
          copy(src, src+nSamples, dst);
        } else {
          copy(src, src+bufSize, dst);
        }
        realFFT(fftIn, idx);
        copy(dst, dst+bufSize, fftIn);
        nSamples -= bufSize;
        nSamples = max(0, nSamples);
      }
      std::fill(dst, dst+bufSize, 0);
      realFFT(fftIn, nBlocks-1);
    }
    
    DSPSplitComplex* getBlockN(int n) {
      return &blocks[n];
    }
    
  };
  
  /**
   Frequency Domain Delay Line. Adds instance data to FdBlockArray to implement a delay
   line for frequency domain data.
   */
  
  class Fddl : public FdBlockArray {
    // indices into arrays of DSPSplitComplex
    int writeIdx; // idx of first free block
    float *fftBuf;
    
  public:
    
    Fddl(FftDesc* desc, int nBlocks) : FdBlockArray(desc, nBlocks) {
      fftBuf = new float[fftDesc->blkSize]();
      writeIdx = -1;
    }
    
    ~Fddl() { if (fftBuf != NULL) delete fftBuf; }
    
    void transformBlock(float *data) {
      std::copy(data, data+fftDesc->blkSize/2, fftBuf);
      writeIdx = ++writeIdx % nBlocks;
      realFFT(fftBuf, writeIdx);
    }
    
    /** n = 0 means most recent */
    DSPSplitComplex* getBlockN(int n) {
      return &blocks[(writeIdx + nBlocks - n) % nBlocks];
    }
    
  };

  /// A class for vector processing version of a complex multiply accumulate operation

  class ComplexMac {
    
    DSPSplitComplex product;
    DSPSplitComplex accum;
    int length;
    
  public:
    
    ComplexMac(int length) {
      this->length = length;
      product.realp = new float[length]();
      product.imagp = new float[length]();
      accum.realp = new float[length]();
      accum.imagp = new float[length]();
    }
    
    void clearAccum() {
      memset((void*)accum.realp, 0, length*sizeof(float));
      memset((void*)accum.imagp, 0, length*sizeof(float));
    }
    
    void fdMac(DSPSplitComplex* x, DSPSplitComplex* y) {
      vDSP_zvmul(x, 1, y, 1, &product, 1, length, 1);
      // first element is special format, don't do complex multiply
      // (overwrites result from vDSP_zcvmul above)
      product.realp[0] = x->realp[0] * y->realp[0]; // DC
      product.imagp[0] = x->imagp[0] * y->imagp[0]; // Nyquist
      vDSP_zvadd(&accum, 1, &product, 1, &accum, 1, length);
    }
    
    DSPSplitComplex* GetAccum() { return &accum; }
  };
  
  class FddlConvolver {
    
  protected:
    int log2blkSize;
    FftDesc fftSetup;
    float *impulse = NULL;
    int impulseLen;
    FdImpulse* _FdImpulse = NULL;
    Fddl* fddl = nullptr;
    ComplexMac* mac = nullptr;
    float* ifftBuf;
    
    int nBlocks() { return fddl->getNBlocks(); }
    
    void MacBlocks() {
      mac->clearAccum();
      for (int i=0; i<nBlocks(); i++) {
        mac->fdMac(_FdImpulse->getBlockN(i), fddl->getBlockN(i));
      }
    }
    
    void init(int log2bufSize) {
      log2blkSize = log2bufSize+1;
      mac = new ComplexMac(1<<log2bufSize);
      ifftBuf = new float[fftSetup.blkSize]();
      updateImpulse();
    }
    
    void updateImpulse() {
      if (impulse != NULL) {
        FdImpulse *oldFdImpulse = _FdImpulse;
        FdImpulse *newImpulse = new FdImpulse(&fftSetup, impulse, impulseLen);
        if (fddl == NULL) {
          fddl = new Fddl(&fftSetup, newImpulse->getNBlocks());
        } else {
          fddl->changeLength(newImpulse->getNBlocks());
        }
        _FdImpulse = newImpulse;
        delete oldFdImpulse;
      }
    }
    
  public:
    float gain = 1.0;
    
    FddlConvolver(int log2bufSize, float *impulse, int len) : fftSetup(log2bufSize+1) {
      init(log2bufSize);
    }
    
    FddlConvolver(int log2bufSize) : fftSetup(log2bufSize+1) { init(log2bufSize); }
    
    ~FddlConvolver() {
      if (fddl != NULL) delete fddl;
      if (_FdImpulse != NULL) delete _FdImpulse;
      if (mac != NULL) delete mac;
      if (ifftBuf != NULL) delete ifftBuf;
    }
    
    void setImpulse(float *newImpulse, int len) {
      if (impulse != NULL) { delete impulse; }
      impulse = newImpulse;
      impulseLen = len;
      updateImpulse();
    }
    
    void processBuffer(float* input) {
      // Transform input, push onto FDDL
      fddl->transformBlock(input);
      MacBlocks();
      Math::RealIFFT(fftSetup.setup, fftSetup.log2blkSize, mac->GetAccum(), ifftBuf);
    }
    
    void processBuffer(float* input, float* output) {
      processBuffer(input);
      int bufSize = 1<<(log2blkSize-1);
      auto src = &ifftBuf[bufSize];
      std::copy(src, src+bufSize, output);
      if (gain != 1.0) {
        vDSP_vsmul(output, 1, &gain, output, 1, bufSize);
      }
    }
    
    float* getOutBuf() { return &ifftBuf[fftSetup.blkSize/2]; }
  };
  
  /**
   Time sliced convolver. Rather than run a convolver with a larger block size in a 
   separate thread to even out processing load, it is possible to run part of the 
   convolution each time the audio proc runs. Although it isn't perfect, dividing up 
   the processing load this way turns out to be not be all that hard.
   */
  
  class TsFddlConvolver : public FddlConvolver {  // time sliced version, 8x for now
    int bufSize;
    int smLog2bufSize;   // log2 of buf size of smallest convolver
    int blkSizRatio;     // blk size ratio between this and smallest
    
    MasterInBuf* inBuffer;   // pointer to external shared circular buffer
    
    // these are for housekeeping for the MacBlocks timeslicing process
    int phase;
    int blkQuot, blkRem; // quotient and remainder for scheduling
    int currMacIdx;
    
    void macBlocks(int phase) {
      if (phase == 0) { mac->clearAccum(); }
      int cnt = blkQuot + ((phase >= blkRem) ? 0 : 1);
      for (int i=0, Idx=currMacIdx; i<cnt; i++, Idx++, currMacIdx++) {
        mac->fdMac(_FdImpulse->getBlockN(Idx), fddl->getBlockN(Idx));
      }
    }
    
    void updateImpulse() {
      FddlConvolver::updateImpulse();
      blkQuot = nBlocks() / (blkSizRatio-2);
      blkRem = nBlocks() % (blkSizRatio-2);
    }
    
    int getPhase() {
      return (inBuffer->sectNum(log2blkSize-smLog2bufSize) - 1) & (blkSizRatio-1);
    }
    
  public:
    
    TsFddlConvolver(int smLog2bufSize, int log2blkSizRatio, float *impulse, int len, MasterInBuf* sigInBuf)
    : TsFddlConvolver(smLog2bufSize, log2blkSizRatio, sigInBuf) {
      setImpulse(impulse, len);
    }
    
    TsFddlConvolver(int smLog2bufSize, int log2blkSizRatio, MasterInBuf* sigInBuf)
    : FddlConvolver(smLog2bufSize + log2blkSizRatio), smLog2bufSize(smLog2bufSize) {
      int log2bufSize = smLog2bufSize + log2blkSizRatio;
      int blkSize = 1<<(log2bufSize+1);
      bufSize = blkSize/2;
      init(log2bufSize);
      inBuffer = sigInBuf;
      blkSizRatio = 1<<log2blkSizRatio;
    }
    
    
    void processBuffer() {
      phase = getPhase();
      if (phase == 0) {                       // first block
        // Transform input, push onto FDDL
        fddl->transformBlock(inBuffer->getPrevPtr(-bufSize));
        currMacIdx = 0;
      } else if (phase != (blkSizRatio-1)) {  // intermediate blocks
        // Accumulate some Fd products
        macBlocks(phase-1);
      } else {                                // last block
        // Do inverse FFT
        Math::RealIFFT(fftSetup.setup, fftSetup.log2blkSize, mac->GetAccum(), ifftBuf);
      }
    }
    
    float* getOutBuf() {
      return &ifftBuf[bufSize + getPhase() * inBuffer->bufSize];
    }
    
  };

  /// This class combines an FDDL convolver for low latency with a TsFddlConvolver (time sliced)
  /// convolver to handle the longer impulse response tail
  
  class TwoFddlConvolver {
    FddlConvolver* smallConvolver;
    TsFddlConvolver* largeConvolver;
    int log2bufSize, log2blkSizRatio;
    MasterInBuf SigInBuf;
    int bufSize;
    
  public:
    float *inBuf = NULL, *outBuf = NULL;
    float gain = 1.0;
    
    TwoFddlConvolver(int log2bufSize, int log2blkSizRatio, vector<float> impulse) :
    TwoFddlConvolver(log2bufSize, log2blkSizRatio)
    { setImpulse(impulse); }
    
    TwoFddlConvolver(int log2bufSize, int log2blkSizRatio) {
      this->log2bufSize = log2bufSize;
      this->log2blkSizRatio = log2blkSizRatio;
      bufSize = 1<<log2bufSize;
      SigInBuf.init(log2bufSize+log2blkSizRatio+1, log2bufSize);
      smallConvolver = new FddlConvolver(log2bufSize);
      largeConvolver = new TsFddlConvolver(log2bufSize, log2blkSizRatio, &SigInBuf);
    }
    
    TwoFddlConvolver (const TwoFddlConvolver &obj) {
      log2bufSize = obj.log2bufSize;
      log2blkSizRatio = obj.log2blkSizRatio;
      bufSize = obj.bufSize;
      SigInBuf.init(obj.getLog2LgBlockSize(), log2bufSize);
      smallConvolver = new FddlConvolver(log2bufSize);
      largeConvolver = new TsFddlConvolver(log2bufSize, log2blkSizRatio, &SigInBuf);
    }
    
    ~TwoFddlConvolver() {
      if (smallConvolver != NULL) delete smallConvolver;
      if (largeConvolver != NULL) delete largeConvolver;
    }
    
    int getLog2LgBlockSize() const {
      return log2bufSize+log2blkSizRatio+1;
    }
    
    void setImpulse(vector<float> impulse) {
      int blkSize = 1<<(getLog2LgBlockSize());
      if (impulse.size() <= blkSize) { impulse.resize(blkSize, 0); }
      smallConvolver->setImpulse(&impulse[0], SigInBuf.size);
      largeConvolver->setImpulse(&impulse[blkSize], impulse.size() - blkSize);
    }
    
    void process() {
      // first, write input into large circular input buffer
      SigInBuf.write(inBuf, bufSize);
      smallConvolver->processBuffer(inBuf);
      // sum the convolver outputs
      vDSP_vadd(smallConvolver->getOutBuf(), 1, largeConvolver->getOutBuf(), 1, outBuf, 1, bufSize);
      // this sequence is because LgConv may overwrite previous results
      largeConvolver->processBuffer();
      vDSP_vsmul(outBuf, 1, &gain, outBuf, 1, bufSize);
      
    }
    
  };
  
}

namespace DspBlocks {
  
  /// --- FDDL (Frequency Domain Delay line) Block ---
  
  struct FddlBlock : DspBlockSingleWireSpec {
    
    FddlBlock() : DspBlockSingleWireSpec(1,1) {}
    vector<AWV::TwoFddlConvolver> convolvers;
    vector<float> impulse;
    int bufferSize;
    
    int nChans() { return inputPins[0].wire->wireSpec.nChannels; }
    
    const string GetClassName() override { return "Fddl Convolver"; }
    
    void Init() override {
      using namespace AWV;
      convolvers = vector<TwoFddlConvolver>(nChans(), TwoFddlConvolver(7, 2));
      for (int i=0; i < nChans(); i++) {
        convolvers[i].inBuf = inputPins[0].wire->buffers[i];
        convolvers[i].outBuf = outputPins[0].wire->buffers[i];
      }
    }
    
    void SetImpulse(vector<float> impulse) {
      this->impulse = impulse;
      for (auto& convolver : convolvers) { convolver.setImpulse(impulse); }
    }
    
    void Process() override {
      for (auto& convolver : convolvers) {
        convolver.process();
      }
    }
    
    void CheckBufferSize(int bufferSize) {
      float logBufSize = log2(bufferSize);
      if (floor(logBufSize) != logBufSize) {
        throw "buffer size must be power of two";
      }
    }
    
  };
  
}


