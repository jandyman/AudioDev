#pragma once

#include "GenericDsp.hpp"
#include <vector>
#import <AudioToolBox/AudioToolbox.h>

namespace DspBlocks {
  using namespace std;
  
  struct AUBufferingAdapter {
    float** out_buffers;
    TopLevelGraph* graph;
    int bufSize;
    int nChannels;
    int maxBufSize = 512;
    
    AUBufferingAdapter(int* maxFramesToRender) {
      bufSize = graph->wireSpec.bufSize;
      nChannels = graph->wireSpec.nChannels;
      // create buffers in case AU doesn't supply them
      out_buffers = new float*[nChannels];
      *maxFramesToRender = maxBufSize;
      for (int ch=0; ch < nChannels; ch++) { out_buffers[ch] = new float[maxBufSize]; }
    }
    
    void Process(AudioBufferList* in_buflist, AudioBufferList* out_buflist, int nFrames) {
      // only the happy case for now. nFrames must be integer multiple of bufSiz
      auto quot = nFrames / bufSize;
      auto rem = nFrames % bufSize;
      assert(nFrames >= bufSize && rem == 0);
    
      // first deal with the nonsense where the host may or may not supply output buffers
      float* auOutPtrs[nChannels];
      for (int ch=0; ch < nChannels; ch++) {
        float* auOutPtr = (float*)in_buflist->mBuffers[ch].mData;
        if (auOutPtr == NULL) {
          auOutPtrs[ch] = out_buffers[ch];
        } else {
          auOutPtrs[ch] = auOutPtr;
        }
      }

      float* inPtrs[nChannels];
      // process by subframe to match buffer sizes
      for (int subFrame=0; subFrame < quot; subFrame++) {
        int idx = subFrame * bufSize;
        // set up input buffer pointers
        for (int ch=0; ch < nChannels; ch++) {
          inPtrs[ch] = (float*)in_buflist->mBuffers[ch].mData + idx;
        }
        graph.SetInputPortBuffers(inPtrs);
        // run the graph
        graph.Process();
        // copy the outputs to the output buffers used by the host
        float** outPtrs = graph.GetOutputPortBuffers();
        for (int ch=0; ch < nChannels; ch++) {
          float* outBase = auOutPtrs[ch] + idx;
          copy(outBase, outBase+bufSize, outPtrs[ch] + idx);
        }
      }
    }
    
  };
  
}
