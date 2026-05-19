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

  // One pending control change. Keyed "channel-filter-field" in pendingFields
  // so rapid slider moves coalesce to the latest value before being sent.
  private struct FieldRef { let channel: Int; let filter: Int; let field: ParamField }
  private var pendingFields: [String: FieldRef] = [:]

  // drainPending() runs as this task and is the ONLY code that writes to the
  // socket, so SET_PARAM round-trips never overlap and the ACK stream stays
  // aligned. nil when idle.
  private var sendLoop: Task<Void, Never>?

  // MARK: Connection lifecycle

  func connect() async {
    connectionState = .connecting
    do {
      try await conn.connect()
      // Send PING immediately then scan for [RESP_ACK, seq, 0x00], discarding
      // any JLinkGDBServer banner bytes that arrive before the ACK.
      let pingSeq = nextSeq()
      try await conn.send(RTTProtocol.ping(seq: pingSeq))
      try await conn.syncToAck(seq: pingSeq)

      connectionState = .connected
      appendLog("Connected")
    } catch {
      connectionState = .failed(error.localizedDescription)
      conn.disconnect()
      appendLog("Connect failed: \(error.localizedDescription)")
    }
  }

  func disconnect() {
    sendLoop?.cancel()
    sendLoop = nil
    pendingFields.removeAll()
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

  // MARK: Field change (throttled single-field RTT send)

  // Called by FilterStripView whenever one control changes. Records the field
  // as pending and starts the send loop if it isn't already running. While a
  // slider is dragged this coalesces to ~one send per throttle interval.
  func fieldChanged(channel: Int, filter: Int, field: ParamField) {
    pendingFields["\(channel)-\(filter)-\(field.rawValue)"] =
      FieldRef(channel: channel, filter: filter, field: field)
    if sendLoop == nil {
      sendLoop = Task { [weak self] in await self?.drainPending() }
    }
  }

  // MARK: Private helpers

  // Gap between send passes. The round-trip itself is ~15 ms; a 20 ms pause
  // caps updates near 30/s — smooth on the scope without flooding the link.
  private static let throttleMs = 20

  // Drains pendingFields until empty: each pass sends every pending field once
  // (freshest value, sampled at send time), then sleeps one throttle interval
  // so further drag motion coalesces into the next pass.
  private func drainPending() async {
    defer { sendLoop = nil }
    while !pendingFields.isEmpty {
      guard isConnected else { pendingFields.removeAll(); return }

      let batch = pendingFields.values.sorted { sendRank($0.field) < sendRank($1.field) }
      pendingFields.removeAll()

      for ref in batch {
        let value = fieldValue(stages[ref.channel][ref.filter], ref.field)
        await sendField(ref, value: value)
      }
      do { try await Task.sleep(for: .milliseconds(Self.throttleMs)) } catch { return }
    }
  }

  // order/enabled trigger a delay-line reset on the firmware, so within a pass
  // they go after fc/gain/q — the reset recompute then sees updated values.
  private func sendRank(_ field: ParamField) -> Int {
    switch field {
    case .fcHz, .gainDb, .q: return 0
    case .order, .enabled:   return 1
    }
  }

  private func sendField(_ ref: FieldRef, value: Float) async {
    guard isConnected else { return }
    do {
      let id = paramID(channel: ref.channel, stage: ref.filter, field: ref.field)
      try await conn.send(RTTProtocol.setParam(seq: nextSeq(), id: id, value: value))
      try RTTProtocol.parseAck(try await conn.readBytes(3))
    } catch {
      appendLog("Param send failed: \(error.localizedDescription)")
    }
  }

  private func fieldValue(_ stage: FilterStage, _ field: ParamField) -> Float {
    switch field {
    case .enabled: return stage.enabled ? 1.0 : 0.0
    case .fcHz:    return stage.fc
    case .order:   return Float(stage.order)
    case .gainDb:  return stage.gainDb
    case .q:       return stage.q
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
