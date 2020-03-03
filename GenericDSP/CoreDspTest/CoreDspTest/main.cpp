#include <iostream>
#include <vector>
#include <algorithm>
#include "AudioFileIO.hpp"
#include "EqDsp.hpp"

using namespace std;
using namespace DspBlocks;
using namespace CoefGen;

int main() {
  float SR;
  int nChannels = 0;
  int nSamples;
  int bufSiz = 128;
  
  float** inSamps = ReadTestFile("stereo_impulse.wav", SR, nChannels, nSamples);
  if (nChannels != 2) exit(-1);
  float** outSamps = new float*[2];
  outSamps[0] = new float[nSamples];
  outSamps[1] = new float[nSamples];

  WireSpec ws(nChannels, SR, bufSiz);

  EqDsp eqGraph;
  // initialize parameters
  auto eqSpecs = vector<EqSpec>(1);
  eqSpecs[0].dB = 12;
  eqSpecs[0].enabled = true;
  eqSpecs[0].type = EqSpec::hiShelf;
  eqSpecs[0].frequency = 3000;
  eqSpecs[0].order = 1;
  eqGraph.EQs[0].eqBlock.SetEqSpecs(eqSpecs);
  eqSpecs[0].type = EqSpec::loShelf;
  eqSpecs[0].frequency = 200;
  eqSpecs[0].enabled = true;
  eqGraph.EQs[1].eqBlock.SetEqSpecs(eqSpecs);

  eqGraph.Describe();
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
