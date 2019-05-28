//
//  main.cpp
//  Test_json
//
//  Created by Andrew Voelkel on 5/22/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#include <iostream>
#include <vector>
#include "json.hpp"

using namespace nlohmann;
// using namespace std;

namespace outer {
  
  namespace inner {
    
    typedef std::string string;

    struct innerS {
      int x;
      string str = "inner";
      innerS(int x, string str) : x(x), str(str) {}
      innerS() {}
    };
    
    void to_json(json& j, const innerS& s) {
      j = json{ {"x", s.x}, {"str", s.str} };
    }
    
    void from_json(const json& j, innerS& s) {
      j.at("str").get_to(s.str);
      j.at("x").get_to(s.x);
    }
    
  }
  
  using namespace inner;
  template<typename T> using vector = std::vector<T>;
  typedef ::std::string string;
  
  struct outerS {
    vector<innerS> s;
    string str = "outer";
    outerS(string str, vector<innerS> s) : str(str), s(s) {}
    outerS() {}
    vector<innerS> GetS() const { return s; }
  };
  
  void to_json(json& j, const outerS& s) {
    j["s"] = s.GetS();
    j["str"] = s.str;
    //j = json{ {"s", s.s}, {"str", s.str} };
  }
  
  void from_json(const json& j, outerS& s) {
    j.at("str").get_to(s.str);
    j.at("s").get_to(s.s);
  }
  
  void main() {
    json j;
    j["orko"] = "borko";
    j["foo"] = 3;
    std::cout << j << std::endl;
    std::cout << j.dump(2) << std::endl;
    
    outerS s = outerS("garbo", vector<innerS>(2, innerS(4, "flynn")));
    json js1(s);
    string encoded = js1.dump(2);
    std::cout << js1.dump(2) << std::endl;
    
    outerS decoded = js1.get<outerS>();
  }
  
}

int main(int argc, const char * argv[]) { outer::main(); return 0; }

