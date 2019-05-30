//
//  DspJson.cpp
//  SimpleEQ
//
//  Created by Andrew Voelkel on 5/23/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#include "DspJson.hpp"
#include <cmath>

// json support
using namespace nlohmann;

namespace CoefGen {
  
  void to_json(json& j, const EqSpec& s) {
    j["enabled"] = s.enabled;
    j["type"] = s.type;
    j["order"] = s.order;
    j["frequency"] = round(s.frequency * 100)/100.0;
    j["dB"] = s.dB;
    j["Q"] = s.Q;
  }
  
  void from_json(const json& j, EqSpec& s) {
    j.at("enabled").get_to(s.enabled);
    j.at("type").get_to(s.type);
    j.at("order").get_to(s.order);
    j.at("frequency").get_to(s.frequency);
    j.at("dB").get_to(s.dB);
    j.at("Q").get_to(s.Q);
  }
  
}

namespace DspBlocks {
  template<typename T> using vector = std::vector<T>;

  void to_json(json& j, const BiquadChainBlock& b) {
    j["stages"] = b.GetEqSpecs();
  }
  
  void from_json(const json& j, BiquadChainBlock& b) {
    auto specs = j.at("stages").get<vector<::CoefGen::EqSpec>>();
    b.SetEqSpecs(specs);
  }
  
}
