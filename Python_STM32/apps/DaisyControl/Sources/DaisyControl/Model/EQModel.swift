// EQModel.swift — observable state and RTT command logic.

import Foundation
import Observation

struct LogEntry: Identifiable {
  let id = UUID()
  let message: String
}

enum ConnectionState: Equatable {
  case disconnected
  case connecting
  case connected
  case failed(String)
}

@MainActor
@Observable
class EQModel {
  // Parameter values indexed by ParamID.rawValue.
  // Defaults match firmware params_init() defaults.
  var values: [Float] = [0.0, 8000.0, 2000.0, 0.0, 8000.0, 2000.0]

  var connectionState: ConnectionState = .disconnected
  var log: [LogEntry] = []

  var isConnected: Bool { connectionState == .connected }

  private let conn = RTTConnection()
  private var seq: UInt8 = 0
  private var debounce: [Int: Task<Void, Never>] = [:]

  // MARK: Connection lifecycle

  func connect() async {
    connectionState = .connecting
    do {
      print("[connect] opening TCP connection to localhost:19021")
      try await conn.connect()
      print("[connect] TCP connected")
      try await conn.drainBanner()

      print("[connect] sending PING")
      let pingSeq = nextSeq()
      let pingBytes = RTTProtocol.ping(seq: pingSeq)
      print("[connect] PING tx: \(hex(pingBytes))")
      try await conn.send(pingBytes)
      let pingResp = try await conn.readBytes(3)
      print("[connect] PING rx: \(hex(pingResp))")
      try RTTProtocol.parseAck(pingResp)
      print("[connect] PING ACK ok")

      for id in 0..<values.count {
        let s = nextSeq()
        let getBytes = RTTProtocol.getParam(seq: s, id: UInt8(id))
        print("[connect] GET_PARAM[\(id)] tx: \(hex(getBytes))")
        try await conn.send(getBytes)
        let resp = try await conn.readGetParamResponse()
        print("[connect] GET_PARAM[\(id)] rx: \(hex(resp))")
        values[id] = try RTTProtocol.parseGetResponse(resp)
        print("[connect] GET_PARAM[\(id)] = \(values[id])")
      }

      connectionState = .connected
      appendLog("Connected — params initialized from firmware")
    } catch {
      connectionState = .failed(error.localizedDescription)
      conn.disconnect()
      appendLog("Connect failed: \(error.localizedDescription)")
      print("[connect] FAILED: \(error)")
    }
  }

  private func hex(_ bytes: [UInt8]) -> String {
    bytes.map { String(format: "%02x", $0) }.joined(separator: " ")
  }

  func disconnect() {
    debounce.values.forEach { $0.cancel() }
    debounce.removeAll()
    conn.disconnect()
    connectionState = .disconnected
    appendLog("Disconnected")
  }

  // MARK: Param writes (called from slider onChange)

  func setValue(_ id: Int, _ value: Float) {
    values[id] = value
    debounce[id]?.cancel()
    debounce[id] = Task { [weak self] in
      do {
        try await Task.sleep(for: .milliseconds(50))
      } catch {
        return  // cancelled while debouncing
      }
      await self?.sendSetParam(id)
    }
  }

  // MARK: Ping (exposed for ConnectionBar button)

  func ping() async {
    let start = Date()
    do {
      try await sendPingInternal()
      let rtt = Date().timeIntervalSince(start) * 1000
      appendLog(String(format: "PING: ACK (%.0f ms)", rtt))
    } catch {
      appendLog("PING: \(error.localizedDescription)")
    }
  }

  // MARK: Private helpers

  private func sendPingInternal() async throws {
    let s = nextSeq()
    try await conn.send(RTTProtocol.ping(seq: s))
    let resp = try await conn.readBytes(3)
    try RTTProtocol.parseAck(resp)
  }

  private func sendSetParam(_ id: Int) async {
    let s = nextSeq()
    do {
      try await conn.send(RTTProtocol.setParam(seq: s, id: UInt8(id), value: values[id]))
      let resp = try await conn.readBytes(3)
      try RTTProtocol.parseAck(resp)
      appendLog("SET param[\(id)] = \(formatValue(id)): ACK")
    } catch {
      appendLog("SET param[\(id)]: \(error.localizedDescription)")
      if case RTTError.connectionClosed = error {
        connectionState = .disconnected
      }
    }
  }

  private func nextSeq() -> UInt8 {
    defer { seq &+= 1 }
    return seq
  }

  private func formatValue(_ id: Int) -> String {
    let v = values[id]
    // Gain params are at IDs 0 and 3
    if id == ParamID.leftShelfGain.rawValue || id == ParamID.rightShelfGain.rawValue {
      return String(format: "%+.1f dB", v)
    }
    return v >= 1000 ? String(format: "%.1f kHz", v / 1000) : String(format: "%.0f Hz", v)
  }

  private func appendLog(_ msg: String) {
    log.append(LogEntry(message: msg))
    if log.count > 100 { log.removeFirst(log.count - 100) }
  }
}
