// RTTConnection.swift — TCP socket to JLinkGDBServer's RTT telnet port.
//
// JLinkGDBServer exposes RTT channel 0 as a raw byte stream on localhost:19021.
// This class wraps NWConnection with async/await helpers for send and receive.
//
// NWConnection only allows one receive in flight at a time, so we run a
// continuous pumpReceive loop that feeds a buffer. readBytes consumes from
// that buffer; drainBanner races the buffer vs a DispatchSource timer so it
// can stop when no data arrives for 200ms (matching Python's settimeout(0.2)
// pattern) without leaving a stale inflight receive.
//
// All methods are @MainActor because NWConnection callbacks are dispatched to
// .main and we want to avoid actor hopping.

import Foundation
import Network

@MainActor
class RTTConnection {
  private var nwConn: NWConnection?

  // Receive pump state
  private var rxBuf: [UInt8] = []
  private var rxWaiter: (n: Int, cont: CheckedContinuation<[UInt8], Error>)?
  // Called by pumpReceive when bannerWaiter is set (drainBanner timer race).
  private var bannerWaiter: (([UInt8]) -> Void)?

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

    pumpReceive()
  }

  // Keeps exactly one NWConnection receive in flight at all times.
  // Incoming bytes go to bannerWaiter (during drainBanner) or rxBuf/rxWaiter.
  private func pumpReceive() {
    guard let conn = nwConn else { return }
    conn.receive(minimumIncompleteLength: 1, maximumLength: 4096) { [weak self] data, _, isComplete, error in
      guard let self else { return }
      if let data = data, !data.isEmpty {
        let bytes = [UInt8](data)
        if let bw = self.bannerWaiter {
          self.bannerWaiter = nil
          bw(bytes)
        } else {
          self.rxBuf += bytes
          self.satisfyWaiter()
        }
      }
      if let error = error {
        self.rxWaiter?.cont.resume(throwing: error)
        self.rxWaiter = nil
      } else if isComplete {
        self.rxWaiter?.cont.resume(throwing: RTTError.connectionClosed)
        self.rxWaiter = nil
      } else {
        self.pumpReceive()
      }
    }
  }

  private func satisfyWaiter() {
    guard let w = rxWaiter, rxBuf.count >= w.n else { return }
    rxWaiter = nil
    let result = Array(rxBuf.prefix(w.n))
    rxBuf = Array(rxBuf.dropFirst(w.n))
    w.cont.resume(returning: result)
  }

  // Drains the JLinkGDBServer greeting banner by reading until 200ms of silence.
  // The banner may arrive as several TCP segments, so stopping at the first \n races.
  func drainBanner() async throws {
    guard nwConn != nil else { throw RTTError.connectionClosed }
    var drained: [UInt8] = []
    while drained.count < 1024 {
      guard let chunk = await bannerChunkWithTimeout(0.2) else { break }
      drained += chunk
    }
    let text = String(bytes: drained, encoding: .utf8) ?? "<binary: \(drained.count) bytes>"
    print("[drainBanner] \(text.trimmingCharacters(in: .whitespacesAndNewlines))")
  }

  // Returns bytes currently in rxBuf, or waits up to `timeout` seconds for
  // pumpReceive to deliver more. Returns nil when the timer fires first.
  private func bannerChunkWithTimeout(_ timeout: TimeInterval) async -> [UInt8]? {
    // Fast path: bytes already buffered.
    if !rxBuf.isEmpty {
      let chunk = rxBuf
      rxBuf = []
      return chunk
    }
    // Slow path: race pumpReceive vs DispatchSource timer.
    return await withCheckedContinuation { (cont: CheckedContinuation<[UInt8]?, Never>) in
      var fired = false
      let src = DispatchSource.makeTimerSource(queue: .main)
      src.schedule(deadline: .now() + timeout)
      src.setEventHandler { [weak self] in
        guard !fired else { return }
        fired = true
        src.cancel()
        self?.bannerWaiter = nil
        cont.resume(returning: nil)
      }
      src.resume()
      self.bannerWaiter = { bytes in
        guard !fired else { return }
        fired = true
        src.cancel()
        cont.resume(returning: bytes)
      }
    }
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
  func readGetParamResponse() async throws -> [UInt8] {
    let header = try await readBytes(3)
    guard header[0] == 0x01 else { return header }
    let value = try await readBytes(4)
    return header + value
  }

  // Reads exactly n bytes from rxBuf, waiting for pumpReceive to deliver more if needed.
  func readBytes(_ n: Int) async throws -> [UInt8] {
    guard nwConn != nil else { throw RTTError.connectionClosed }
    if rxBuf.count >= n {
      let result = Array(rxBuf.prefix(n))
      rxBuf = Array(rxBuf.dropFirst(n))
      return result
    }
    return try await withCheckedThrowingContinuation { cont in
      rxWaiter = (n: n, cont: cont)
    }
  }

  func disconnect() {
    nwConn?.cancel()
    nwConn = nil
    rxBuf = []
    rxWaiter?.cont.resume(throwing: RTTError.connectionClosed)
    rxWaiter = nil
    bannerWaiter = nil
  }
}
