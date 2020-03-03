//
//  GenericDsp.cpp
//  SimpleEQ
//
//  Created by Andrew Voelkel on 10/31/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

#include "GenericDsp.hpp"

namespace DspBlocks {

  // This file is just for debug, since Xcode/Clang make debugging header-only miserable.

  DesignContext::DesignContext() {
    connectionWires.reserve(200);  // TODO TMP KLUDGE
    blocks.reserve(200);           // TODO TMP KLUDGE
  }

}

