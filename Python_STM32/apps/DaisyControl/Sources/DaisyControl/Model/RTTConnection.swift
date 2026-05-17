// RTTConnection.swift — TCP socket to JLinkGDBServer's RTT telnet port.
//
// JLinkGDBServer exposes RTT channel 0 as a raw byte stream on localhost:19021.
// This class wraps NWConnection with async/await helpers for send and receive.
//
// All methods are @MainActor because NWConnection callbacks are dispatched to
// .main and we want to avoid actor hopping.

import Foundation
import Network

@MainActor
class RTTConnection {
  private var nwConn: NWConnection?

  var isConnected: Bool { nwConn != nil }

  func connect(host: String = "127.0.0.1", port: UInt16 = 19021) async throws {
    let endpoint = NWEndpoint.hostPort(
      host: NWEndpoint.Host(host),
      port: NWEndpoint.Port(rawValue: port)!
    )
    let conn = NWConnection(to: endpoint, using: .tcp)
    nwConn = conn

    try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
      conn.stateUpdateHandler = { state in
        switch state {
        case .ready:
          conn.stateUpdateHandler = nil
          cont.resume()
        case .failed(let err):
          conn.stateUpdateHandler = nil
          cont.resume(throwing: RTTError.connectionFailed(err.localizedDescription))
        case .waiting(let err):
          // Nothing is listening on the port — fail immediately rather than retrying.
          conn.stateUpdateHandler = nil
          conn.cancel()
          cont.resume(throwing: RTTError.connectionFailed(err.localizedDescription))
        default:
          break
        }
      }
      conn.start(queue: .main)
    }
  }

  // Drains the JLinkGDBServer greeting banner (e.g. "SEGGER J-Link V7.x ...\r\n")
  // that arrives immediately after TCP connect, before the raw RTT stream begins.
  func drainBanner() async throws {
    guard let conn = nwConn else { throw RTTError.connectionClosed }
    var drained: [UInt8] = []
    while !drained.contains(UInt8(ascii: "\n")) && drained.count < 512 {
      let chunk: [UInt8] = try await withCheckedThrowingContinuation { cont in
        conn.receive(minimumIncompleteLength: 1, maximumLength: 256) { data, _, isComplete, error in
          if let error = error {
            cont.resume(throwing: error)
          } else if let data = data, !data.isEmpty {
            cont.resume(returning: [UInt8](data))
          } else if isComplete {
            cont.resume(throwing: RTTError.connectionClosed)
          } else {
            cont.resume(throwing: RTTError.unexpectedResponse)
          }
        }
      }
      drained += chunk
    }
    let banner = String(bytes: drained, encoding: .utf8) ?? drained.map { String(format: "%02x", $0) }.joined(separator: " ")
    print("[drainBanner] \(banner.trimmingCharacters(in: .whitespacesAndNewlines))")
  }

  func send(_ bytes: [UInt8]) async throws {
    guard let conn = nwConn else { throw RTTError.connectionClosed }
    try await withCheckedThrowingContinuation { (cont: CheckedContinuation<Void, Error>) in
      conn.send(content: Data(bytes), completion: .contentProcessed { error in
        if let error = error {
          cont.resume(throwing: error)
        } else {
          cont.resume()
        }
      })
    }
  }

  // Reads the response to CMD_GET_PARAM: 3-byte header, then 4 more bytes only if RESP_ACK.
  // Returns the full byte array (3 or 7 bytes) for RTTProtocol.parseGetResponse() to decode.
  func readGetParamResponse() async throws -> [UInt8] {
    let header = try await readBytes(3)
    guard header[0] == 0x01 else { return header }  // NAK or unknown — return 3 bytes
    let value = try await readBytes(4)
    return header + value
  }

  // Reads exactly n bytes. Returns them or throws on connection close / error.
  func readBytes(_ n: Int) async throws -> [UInt8] {
    guard let conn = nwConn else { throw RTTError.connectionClosed }
    return try await withCheckedThrowingContinuation { (cont: CheckedContinuation<[UInt8], Error>) in
      conn.receive(minimumIncompleteLength: n, maximumLength: n) { data, _, isComplete, error in
        if let error = error {
          cont.resume(throwing: error)
        } else if let data = data, data.count >= n {
          cont.resume(returning: [UInt8](data))
        } else if isComplete {
          cont.resume(throwing: RTTError.connectionClosed)
        } else {
          cont.resume(throwing: RTTError.unexpectedResponse)
        }
      }
    }
  }

  func disconnect() {
    nwConn?.cancel()
    nwConn = nil
  }
}
