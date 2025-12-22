//
//  GainControlApp.swift
//  GainControl
//
//  SwiftUI app for controlling andy.gain~ via OSC
//

import SwiftUI

@main
struct GainControlApp: App {
  var body: some Scene {
    WindowGroup {
      ContentView()
    }
    .windowResizability(.contentSize)
  }
}
