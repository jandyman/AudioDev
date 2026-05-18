// EQModel.swift — Observable state and RTT command logic.
//
// Filter state: two channels × five filter stages (LP, HP, LS, HS, BP).
// Stage types and positions are fixed — only parameters change at runtime.
// param_id encoding: channel*25 + stage*5 + field (see RTTProtocol.swift).
//
// Defaults match firmware gen_eq_params defaults so both sides agree at startup
// without a full-push sync on connect. A future improvement could add a
// syncAll() call on connect to handle firmware resets mid-session.

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

  // MARK: Filter state — [channel][stageIndex], L=0 R=1, LP/HP/LS/HS/BP = 0–4

  var stages: [[FilterStage]] = [
    defaultStages(),  // Left
    defaultStages(),  // Right
  ]

  // MARK: Connection state

  var connectionState: ConnectionState = .disconnected
  var log: [LogEntry] = []

  var isConnected: Bool { connectionState == .connected }

  private let conn = RTTConnection()
  private var seq: UInt8 = 0
  private var debounce: [String: Task<Void, Never>] = [:]

  // MARK: Connection lifecycle

  func connect() async {
    connectionState = .connecting
    do {
      try await conn.connect()
      try await conn.drainBanner()

      let pingSeq = nextSeq()
      try await conn.send(RTTProtocol.ping(seq: pingSeq))
      let pingResp = try await conn.readBytes(3)
      try RTTProtocol.parseAck(pingResp)

      connectionState = .connected
      appendLog("Connected")
    } catch {
      connectionState = .failed(error.localizedDescription)
      conn.disconnect()
      appendLog("Connect failed: \(error.localizedDescription)")
    }
  }

  func disconnect() {
    debounce.values.forEach { $0.cancel() }
    debounce.removeAll()
    conn.disconnect()
    connectionState = .disconnected
    appendLog("Disconnected")
  }

  // MARK: Ping

  func ping() async {
    let start = Date()
    do {
      let s = nextSeq()
      try await conn.send(RTTProtocol.ping(seq: s))
      let resp = try await conn.readBytes(3)
      try RTTProtocol.parseAck(resp)
      let rtt = Date().timeIntervalSince(start) * 1000
      appendLog(String(format: "PING: ACK (%.0f ms)", rtt))
    } catch {
      appendLog("PING: \(error.localizedDescription)")
    }
  }

  // MARK: Stage change (debounced RTT send)

  func stageChanged(channel: Int, filter: Int) {
    let key = "\(channel)-\(filter)"
    debounce[key]?.cancel()
    debounce[key] = Task { [weak self] in
      do { try await Task.sleep(for: .milliseconds(50)) } catch { return }
      await self?.syncStage(channel: channel, filter: filter)
    }
  }

  // MARK: Private helpers

  private func syncStage(channel: Int, filter: Int) async {
    guard isConnected else { return }
    let stage = stages[channel][filter]
    let ch    = channel == 0 ? "L" : "R"

    // Send fc/gain/q first (smooth update), then order and enabled last
    // (both trigger delay-line reset on the firmware side). This way the
    // reset recompute sees the correct fc/gain/q values already applied.
    let fields: [(ParamField, Float)] = [
      (.fcHz,    stage.fc),
      (.gainDb,  stage.gainDb),
      (.q,       stage.q),
      (.order,   Float(stage.order)),
      (.enabled, stage.enabled ? 1.0 : 0.0),
    ]

    do {
      for (field, val) in fields {
        let id = paramID(channel: channel, stage: filter, field: field)
        let s  = nextSeq()
        try await conn.send(RTTProtocol.setParam(seq: s, id: id, value: val))
        let resp = try await conn.readBytes(3)
        try RTTProtocol.parseAck(resp)
      }
      appendLog("Ch\(ch) \(stage.type.label) synced")
    } catch {
      appendLog("Ch\(ch) \(stage.type.label) sync failed: \(error.localizedDescription)")
    }
  }

  private func nextSeq() -> UInt8 {
    defer { seq &+= 1 }
    return seq
  }

  private func appendLog(_ msg: String) {
    log.append(LogEntry(message: msg))
    if log.count > 100 { log.removeFirst(log.count - 100) }
  }
}

// MARK: - Default filter stages

private func defaultStages() -> [FilterStage] {
  [
    FilterStage(.lp, fc: 20000, order: 2),
    FilterStage(.hp, fc:    20, order: 1),
    FilterStage(.ls, fc:   200, order: 2, gainDb: 0),
    FilterStage(.hs, fc:  8000, order: 2, gainDb: 0),
    FilterStage(.bp, fc:  1000,           gainDb: 0, q: 0.7071),
  ]
}
