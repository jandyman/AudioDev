//
//  OSCController.swift
//  GainControl
//
//  OSC message sender for controlling Max
//

import Foundation
import Network

class OSCController: ObservableObject {
  private var connection: NWConnection?
  private let host: String = "127.0.0.1"  // localhost
  private let port: UInt16 = 7400

  init() {
    setupConnection()
  }

  private func setupConnection() {
    let endpoint = NWEndpoint.hostPort(
      host: NWEndpoint.Host(host),
      port: NWEndpoint.Port(rawValue: port)!
    )

    connection = NWConnection(
      to: endpoint,
      using: .udp
    )

    connection?.stateUpdateHandler = { state in
      switch state {
      case .ready:
        print("OSC connection ready")
      case .failed(let error):
        print("OSC connection failed: \(error)")
      default:
        break
      }
    }

    connection?.start(queue: .global())
  }

  func sendGain(_ value: Double) {
    let message = createOSCMessage(address: "/gain", value: Float(value))

    connection?.send(
      content: message,
      completion: .contentProcessed { error in
        if let error = error {
          print("Send error: \(error)")
        }
      }
    )
  }

  func testConnection() -> Bool {
    return connection?.state == .ready
  }

  // MARK: - OSC Message Formatting

  private func createOSCMessage(address: String, value: Float) -> Data {
    var data = Data()

    // OSC address (null-terminated, padded to 4-byte boundary)
    data.append(address.data(using: .utf8)!)
    data.append(0)  // null terminator

    // Pad to 4-byte boundary
    while data.count % 4 != 0 {
      data.append(0)
    }

    // Type tag string (,f = float)
    data.append(",f".data(using: .utf8)!)
    data.append(0)  // null terminator
    data.append(0)  // padding to 4-byte boundary

    // Float value (big-endian)
    var bigEndianValue = value.bitPattern.bigEndian
    data.append(Data(bytes: &bigEndianValue, count: 4))

    return data
  }

  deinit {
    connection?.cancel()
  }
}
