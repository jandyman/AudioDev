//
//  DspJson.hpp
//  SimpleEQ
//
//  Created by Andrew Voelkel on 5/23/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#pragma once

#include "json.hpp"
#include "BiquadChain.hpp"

// json support
using namespace nlohmann;

namespace CoefGen {
  void to_json(json& j, const EqSpec& s);
  void from_json(const json& j, EqSpec& s);
}

namespace DspBlocks {
  void to_json(json& j, const BiquadChainBlock& b);
  void from_json(const json& j, BiquadChainBlock& b);
}
  


