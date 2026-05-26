/* @block
(define-block Mixer2
 (inputs in1 in2 gain1 gain2)
 (outputs out))
*/

#include "mixer2.h"

void Mixer2::process(const float* const* inputs, float* const* outputs, int n) {
  const float* in1   = inputs[0];
  const float* in2   = inputs[1];
  const float* gain1 = inputs[2];
  const float* gain2 = inputs[3];
        float* out   = outputs[0];

  for (int i = 0; i < n; i++)
    out[i] = in1[i] * gain1[i] + in2[i] * gain2[i];
}
