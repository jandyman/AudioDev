// RTTProtocol.swift — packet encode/decode mirroring rtt_protocol.h exactly.
//
// Down channel (host → target):
//   CMD_PING      0x01: [cmd][seq]                    2 bytes
//   CMD_SET_PARAM 0x02: [cmd][seq][id][f0][f1][f2][f3] 7 bytes
//   CMD_GET_PARAM 0x03: [cmd][seq][id]                 3 bytes
//
// Up channel (target → host):
//   RESP_ACK      0x01: [resp][seq][0x00]              3 bytes
//   RESP_ACK+val  0x01: [resp][seq][0x00][f0][f1][f2][f3]  7 bytes (GET_PARAM reply)
//   RESP_NAK      0x02: [resp][seq][reason]            3 bytes

import Foundation

enum RTTError: Error, LocalizedError {
  case connectionFailed(String)
  case unexpectedResponse
  case connectionClosed
  case nakResponse(reason: UInt8)

  var errorDescription: String? {
    switch self {
    case .connectionFailed(let s): return "Connection failed: \(s)"
    case .unexpectedResponse:     return "Unexpected response"
    case .connectionClosed:       return "Connection closed"
    case .nakResponse(let r):     return "NAK (reason 0x\(String(r, radix: 16)))"
    }
  }
}

enum RTTProtocol {
  // MARK: Encode

  static func ping(seq: UInt8) -> [UInt8] {
    [0x01, seq]
  }

  static func setParam(seq: UInt8, id: UInt8, value: Float) -> [UInt8] {
    let bits = value.bitPattern   // UInt32, host byte order (macOS is LE = ARM native)
    return [
      0x02, seq, id,
      UInt8(bits & 0xFF),
      UInt8((bits >> 8)  & 0xFF),
      UInt8((bits >> 16) & 0xFF),
      UInt8((bits >> 24) & 0xFF),
    ]
  }

  static func getParam(seq: UInt8, id: UInt8) -> [UInt8] {
    [0x03, seq, id]
  }

  // MARK: Decode

  // Parses a 3-byte ACK/NAK. Throws on NAK or malformed response.
  static func parseAck(_ bytes: [UInt8]) throws {
    guard bytes.count >= 3 else { throw RTTError.unexpectedResponse }
    if bytes[0] == 0x02 { throw RTTError.nakResponse(reason: bytes[2]) }
    guard bytes[0] == 0x01 else { throw RTTError.unexpectedResponse }
  }

  // Parses a GET_PARAM response (3 bytes for NAK, 7 bytes for ACK). Returns the float value.
  static func parseGetResponse(_ bytes: [UInt8]) throws -> Float {
    guard bytes.count >= 3 else { throw RTTError.unexpectedResponse }
    if bytes[0] == 0x02 { throw RTTError.nakResponse(reason: bytes[2]) }
    guard bytes.count >= 7, bytes[0] == 0x01 else { throw RTTError.unexpectedResponse }
    let bits = UInt32(bytes[3])
             | (UInt32(bytes[4]) << 8)
             | (UInt32(bytes[5]) << 16)
             | (UInt32(bytes[6]) << 24)
    return Float(bitPattern: bits)
  }
}

// Flat param_id encoding — mirrors rtt_protocol.h / rtt_cmd.cpp.
//   id = channel*25 + stage*5 + field
//   channel: 0=L, 1=R
//   stage:   0=LP, 1=HP, 2=LS, 3=HS, 4=BP
//   field:   0=enabled, 1=fc_hz, 2=order, 3=gain_db, 4=q
// PARAM_COUNT = 50

enum ParamField: Int {
  case enabled = 0
  case fcHz    = 1
  case order   = 2
  case gainDb  = 3
  case q       = 4
}

func paramID(channel: Int, stage: Int, field: ParamField) -> UInt8 {
  UInt8(channel * 25 + stage * 5 + field.rawValue)
}
