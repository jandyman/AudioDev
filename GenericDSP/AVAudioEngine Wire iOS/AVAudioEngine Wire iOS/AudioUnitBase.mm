//
//  AKAudioUnitBase.mm
//  AudioKit
//
//  Created by Andrew Voelkel, revision history on GitHub.
//  Copyright © 2018 AudioKit. All rights reserved.
//

#import "AudioUnitBase.h"
#include <algorithm>

#define MaxBufSize 512

struct IVars {
  float** out_buffers;
  float** in_buffers;
  int maxFrames;
  int nChannels;
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

@interface ThruAudioUnit ()

@end

@implementation ThruAudioUnit {
  // C++ members need to be ivars; they would be copied on access if they were properties.
  IVars iVars;
}

@synthesize parameterTree = _parameterTree;

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
  
  iVars.maxFrames = self.maximumFramesToRender = 4096;
  
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


//- (BOOL)shouldChangeToFormat:(AVAudioFormat *)format forBus:(AUAudioUnitBus *)bus {
//  return YES;
//}


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
  
  // allocate space for input and output buffers for buffering adapter
  iVars.AllocateBuffers(_inputBus.format);
    
  return YES;
}

// Deallocate resources allocated by allocateRenderResourcesAndReturnError:
// Hosts should call this after finishing rendering.

- (void)deallocateRenderResources {
  // iVars.graph->deinit();
  [super deallocateRenderResources];
}

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
  
  // first deal with the nonsense where the host may or may not supply output buffers
  // at completion
  float* auInPtrs[iVars.nChannels];
  float* auOutPtrs[iVars.nChannels];
  for (int ch=0; ch < iVars.nChannels; ch++) {
    float* auOutPtr = (float*)out_buflist->mBuffers[ch].mData;
    if (auOutPtr == NULL) {
      auOutPtrs[ch] = iVars.out_buffers[ch];
    } else {
      auOutPtrs[ch] = auOutPtr;
    }
    auInPtrs[ch] = (float*)in_buflist->mBuffers[ch].mData;
  }
  
  // just copy input to output
  for (int chan=0; chan < iVars.nChannels; chan++) {
    for (int frame=0; frame < nFrames; frame++) {
      auOutPtrs[chan][frame] = auInPtrs[chan][frame];
    }
  }
  
}

- (BOOL)canProcessInPlace {
  return NO;   // OK THIS IS DIFFERENT FROM APPLE EXAMPLE CODE
}

@end
