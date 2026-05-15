// LogView.swift — scrollable command log at the bottom of the window.

import SwiftUI

struct LogView: View {
  let entries: [LogEntry]

  var body: some View {
    ScrollViewReader { proxy in
      ScrollView {
        LazyVStack(alignment: .leading, spacing: 2) {
          ForEach(entries) { entry in
            Text(entry.message)
              .font(.system(.caption, design: .monospaced))
              .foregroundStyle(.primary)
              .id(entry.id)
          }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
      }
      .onChange(of: entries.count) { _, _ in
        if let last = entries.last {
          proxy.scrollTo(last.id, anchor: .bottom)
        }
      }
    }
    .background(Color(nsColor: .textBackgroundColor))
  }
}
