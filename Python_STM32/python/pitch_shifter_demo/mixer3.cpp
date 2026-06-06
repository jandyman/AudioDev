/* @block
(define-block mixer3
 (inputs in1 in2 in3 gain1 gain2 gain3 gate)
 (outputs out))
*/

#include "mixer3.h"

void mixer3::process(const float* const* inputs, float* const* outputs, int n) {
  const float* in1   = inputs[0];
  const float* in2   = inputs[1];
  const float* in3   = inputs[2];
  const float* gain1 = inputs[3];
  const float* gain2 = inputs[4];
  const float* gain3 = inputs[5];
  const float* gate  = inputs[6];
        float* out   = outputs[0];

  for (int i = 0; i < n; i++)
    out[i] = (in1[i] * gain1[i] + in2[i] * gain2[i] + in3[i] * gain3[i]) * gate[i];
}
