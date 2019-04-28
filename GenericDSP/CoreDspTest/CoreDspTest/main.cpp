#include <iostream>
#include <vector>
#include <algorithm>
#include "AudioFileIO.hpp"
// #include "TestGraph.hpp"
#include "TestGraph2.hpp"

using namespace std;
using namespace DspBlocks;

int main() {
  float SR;
  int nChannels;
  int nSamples;
  int bufSiz = 128;
  
  float** inSamps = ReadTestFile("stereo_impulse.wav", SR, nChannels, nSamples);
  if (nChannels != 2) exit(-1);
  float** outSamps = new float*[2];
  outSamps[0] = new float[nSamples];
  outSamps[1] = new float[nSamples];

  WireSpec ws(nChannels, SR, bufSiz);

  EqMasterGraph eqGraph;
  eqGraph.Init(ws);

  float* iBufs[2];
  float** oBufs = eqGraph.GetOutputPortBuffers();
  Wire* wire = eqGraph.GetOutputPortWire();

  int i;
  for (i = 0; i + bufSiz <= nSamples; i += bufSiz) {
    iBufs[0] = &inSamps[0][i];
    iBufs[1] = &inSamps[1][i];
    eqGraph.SetInputPortBuffers(iBufs);
    eqGraph.SetOutputPortBuffers(outSamps, i);
    eqGraph.Process();
  }
  
  WriteTestFile("testout.wav", SR, nChannels, outSamps, i-1);
  
  return 0;
}
