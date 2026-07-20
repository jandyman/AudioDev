#include "Envelopes.h"

void AttRelProc(D_AttRel* s, float newSamp) {
  float diff = newSamp - s->PrevOut;
  if (newSamp > s->PrevOut) {
    s->PrevOut += s->AttCf * diff;
  } else {
    s->PrevOut += s->RelCf * diff;
  }
}