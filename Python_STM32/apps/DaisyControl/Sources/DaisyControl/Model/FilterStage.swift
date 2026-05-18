// FilterStage.swift — Per-filter parameter state.

import Foundation
import Observation

enum FilterType: Int, CaseIterable, Identifiable {
  case lp = 0, hp, ls, hs, bp
  var id: Int { rawValue }

  var label: String {
    switch self {
    case .lp: "Low Pass"
    case .hp: "High Pass"
    case .ls: "Lo Shelf"
    case .hs: "Hi Shelf"
    case .bp: "Peak EQ"
    }
  }

  var hasGain:  Bool { self == .ls || self == .hs || self == .bp }
  var hasQ:     Bool { self == .bp }
  var hasOrder: Bool { self != .bp }
}

@Observable
final class FilterStage {
  let type: FilterType

  var enabled: Bool  = true
  var fc:      Float  // Hz
  var order:   Int    // 1–4 (BP always uses 2 internally)
  var gainDb:  Float  // LS / HS / BP: boost or cut in dB
  var q:       Float  // BP only: Q factor

  init(_ type: FilterType, fc: Float, order: Int = 2,
       gainDb: Float = 0, q: Float = 0.7071) {
    self.type   = type
    self.fc     = fc
    self.order  = order
    self.gainDb = gainDb
    self.q      = q
  }
}
