//
//  OSCController.swift
//  GainControl (iOS)
//
//  OSC message sender for controlling Max over WiFi
//

import Foundation
import Network

class OSCController: ObservableObject {
  @Published var host: String = "192.168.1.100"  // Placeholder - update in settings to your Mac's IP

  private var connection: NWConnection?
  private let port: UInt16 = 7400

  init() {
    setupConnection()
  }

  func setHost(_ newHost: String) {
    objectWillChange.send()
    host = newHost
    setupConnection()
  }

  private func setupConnection() {
    // Cancel existing connection
    connection?.cancel()

    let endpoint = NWEndpoint.hostPort(
      host: NWEndpoint.Host(host),
      port: NWEndpoint.Port(rawValue: port)!
    )

    connection = NWConnection(
      to: endpoint,
      using: .udp
    )

    // Start connection (UDP is connectionless - this just prepares to send)
    connection?.start(queue: .global())
  }

  func sendGain(_ value: Double) {
    if connection == nil {
      setupConnection()
    }

    let message = createOSCMessage(address: "/gain", value: Float(value))

    connection?.send(
      content: message,
      completion: .contentProcessed { error in
        if let error = error {
          print("OSC send error: \(error)")
        }
      }
    )
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
