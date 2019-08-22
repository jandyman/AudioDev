//
//  AKAudioUnitBase.mm
//  AudioKit
//
//  Created by Andrew Voelkel, revision history on GitHub.
//  Copyright © 2018 AudioKit. All rights reserved.
//

#import "GenericDsp.hpp"
#import "AudioUnitBase.h"
#include <algorithm>

#define MaxBufSize 512

struct IVars {
  DspBlocks::TopLevelGraph* graph;
  float** out_buffers;
  float** in_buffers;
  int bufSize;
  int maxFrames;
  int nChannels;
  bool prepared = false;
  AVAudioPCMBuffer* in_pcmbuffer = nullptr;
  AudioBufferList* in_buffer_list;
  AudioBufferList* out_buffer_list;
  
  void AllocateBuffers(AVAudioFormat* format) {
    nChannels = format.channelCount;
    in_pcmbuffer = [[AVAudioPCMBuffer alloc] initWithPCMFormat:format
                                                 frameCapacity:maxFrames];
  }
  
  AudioBufferList* GetInputBuffers(int frameCnt) {
    auto orig = in_pcmbuffer.audioBufferList;
    auto copy = in_pcmbuffer.mutableAudioBufferList;
      for (UInt32 i = 0; i < orig->mNumberBuffers; ++i) {
      copy->mBuffers[i].mNumberChannels = orig->mBuffers[i].mNumberChannels;
      copy->mBuffers[i].mData = orig->mBuffers[i].mData;
      copy->mBuffers[i].mDataByteSize = sizeof(float) * frameCnt;
    }
    return copy;
  }
  
};

@interface AudioUnitBase ()

@end

@implementation AudioUnitBase {
  // C++ members need to be ivars; they would be copied on access if they were properties.
  IVars iVars;
}

@synthesize parameterTree = _parameterTree;

/**
 This should be overridden. All the base class does is make sure that the pointer to the
 DSP is invalid.
 */

- (void*)getDspWithBufSize:(int*)bufSize {
  // should cause fatal error
  *bufSize = 128;
  return (void*)nullptr;
}


/*************************************************************************************
 Much simpler than the Apple example code version. We don't deal with presets, we don't set up
 a specific parameterTree, etc. The block set for parameterTree is moved to setParameterTree
 *************************************************************************************/

- (instancetype)initWithComponentDescription:(AudioComponentDescription)componentDescription
                                     options:(AudioComponentInstantiationOptions)options
                                       error:(NSError **)outError {
  
  self = [super initWithComponentDescription:componentDescription options:options error:outError];
  if (self == nil) { return nil; }
  
  // Initialize a default format for the busses.
  AVAudioFormat *defaultFormat = [[AVAudioFormat alloc]
                                  initStandardFormatWithSampleRate:44100 channels:2];
  
  iVars.graph = (DspBlocks::TopLevelGraph*)[self getDsp:&iVars.bufSize];
  iVars.maxFrames = self.maximumFramesToRender = iVars.bufSize * 8;
  
  // Create the input and output busses.
  _outputBus = [[AUAudioUnitBus alloc] initWithFormat:defaultFormat error:nil];
  _inputBus = [[AUAudioUnitBus alloc] initWithFormat:defaultFormat error:nil];

  // Create the input and output bus arrays.
  _inputBusArray  = [[AUAudioUnitBusArray alloc] initWithAudioUnit:self
                                                           busType:AUAudioUnitBusTypeInput
                                                            busses: @[self.inputBus]];
  
  _outputBusArray = [[AUAudioUnitBusArray alloc] initWithAudioUnit:self
                                                           busType:AUAudioUnitBusTypeOutput
                                                            busses: @[self.outputBus]];
  
  // Create a default empty parameter tree.
  _parameterTree = [AUParameterTree createTreeWithChildren:@[]];
  
  return self;
}

- (AUAudioUnitBusArray *)inputBusses { return _inputBusArray; }
- (AUAudioUnitBusArray *)outputBusses { return _outputBusArray; }


/*******************************************************************************
 Allocate resources required to render.
 Hosts must call this to initialize the AU before beginning to render.
********************************************************************************/

- (BOOL)allocateRenderResourcesAndReturnError:(NSError **)outError {
  if (![super allocateRenderResourcesAndReturnError:outError]) {
    return NO;
  }
  
  if (_outputBus.format.channelCount != _inputBus.format.channelCount) {
    if (outError) {
      *outError = [NSError errorWithDomain:NSOSStatusErrorDomain
                                      code:kAudioUnitErr_FailedInitialization
                                  userInfo:nil];
    }
    // Notify superclass that initialization was not successful
    self.renderResourcesAllocated = NO;
    return NO;
  }
  
  // Initialize the graph
  if (!iVars.prepared) {
    // allocate space for input and output buffers for buffering adapter
    iVars.AllocateBuffers(_inputBus.format);
    DspBlocks::WireSpec ws;
    ws.nChannels = 2;  // _inputBus.format.channelCount;
    ws.sampleRate = _inputBus.format.sampleRate;
    ws.bufSize = iVars.bufSize;
    iVars.graph->PrepareForOperation(ws, true);
    iVars.graph->InitBlocks();
    iVars.graph->Describe();
    iVars.prepared = true;
  } else {
    auto& ws = iVars.graph->wireSpec;
    auto fmt = _inputBus.format;
    if (ws.sampleRate != fmt.sampleRate) {
      return NO;
    }
  }
  
  return YES;
}

// Deallocate resources allocated by allocateRenderResourcesAndReturnError:
// Hosts should call this after finishing rendering.

- (void)deallocateRenderResources {
  // iVars.graph->deinit();
  [super deallocateRenderResources];
}


/********************************************************************************
 Subclassers must provide a AUInternalRenderBlock (via a getter) to implement rendering.
********************************************************************************/

- (AUInternalRenderBlock)internalRenderBlock {
  
  // Capture in locals to avoid ObjC member lookups.
  // Specify captured objects are mutable.
  __block IVars* _iVars = &iVars;
  
  return ^AUAudioUnitStatus(AudioUnitRenderActionFlags *actionFlags,
                            const AudioTimeStamp *timestamp,
                            AVAudioFrameCount frameCount,
                            NSInteger outputBusNumber,
                            AudioBufferList *outputData,
                            const AURenderEvent *realtimeEventListHead,
                            AURenderPullInputBlock pullInputBlock) {
    
    // pull the input buffer
    AudioBufferList *inAudioBufferList = _iVars->GetInputBuffers(frameCount);
    pullInputBlock(actionFlags, timestamp, frameCount, 0, inAudioBufferList);
                   
    // process the graph
    Process(_iVars, inAudioBufferList, outputData, frameCount);
    return noErr;
  };
}

void Process(IVars* _iVars, AudioBufferList* in_buflist, AudioBufferList* out_buflist, int nFrames) {
  auto& iVars = *_iVars;
  // only the happy case for now. nFrames must be integer multiple of bufSiz
  auto quot = nFrames / iVars.bufSize;
  auto rem = nFrames % iVars.bufSize;
  assert(nFrames >= iVars.bufSize && rem == 0);
  
  // first deal with the nonsense where the host may or may not supply output buffers
  // at completion, auOutPtrs holds the float** we need for the GenericDsp API
  float* auOutPtrs[iVars.nChannels];
  for (int ch=0; ch < iVars.nChannels; ch++) {
    float* auOutPtr = (float*)out_buflist->mBuffers[ch].mData;
    if (auOutPtr == NULL) {
      auOutPtrs[ch] = iVars.out_buffers[ch];
    } else {
      auOutPtrs[ch] = auOutPtr;
    }
  }
  
  // Now we process subframe by subframe, to match buffer sizes with the graph
  float* inPtrs[iVars.nChannels];
  float* outPtrs[iVars.nChannels];
  for (int subFrame=0; subFrame < quot; subFrame++) {
    int idx = subFrame * iVars.bufSize;
    // set up input buffer pointers
    for (int ch=0; ch < iVars.nChannels; ch++) {
      inPtrs[ch] = &((float*)in_buflist->mBuffers[ch].mData)[idx];
      outPtrs[ch] = &auOutPtrs[ch][idx];
    }
    iVars.graph->SetInputPortBuffers(inPtrs);
    iVars.graph->SetOutputPortBuffers(outPtrs, 0);
    
    // run the graph
    iVars.graph->Process();
    
  }
}

- (BOOL)canProcessInPlace {
  return NO;   // OK THIS IS DIFFERENT FROM APPLE EXAMPLE CODE
}

@end
