// FreqResponseView.swift — Log-scale frequency response plot.
//
// X axis: 20 Hz – 20 kHz (log scale)
// Y axis: ±30 dB (linear)
// Computed locally from FilterStage parameters via FilterDesign.swift.
// Redraws automatically whenever any observed stage property changes.

import SwiftUI

struct FreqResponseView: View {
  let stages: [FilterStage]

  private let fMin   = 20.0,  fMax  = 20000.0
  private let dbMin  = -30.0, dbMax = 30.0
  private let nPlot  = 400

  // Padding inside the Canvas reserved for axis labels.
  private let padL: CGFloat = 44
  private let padR: CGFloat = 12
  private let padT: CGFloat = 8
  private let padB: CGFloat = 28

  var body: some View {
    Canvas { ctx, size in
      let pw = size.width  - padL - padR
      let ph = size.height - padT - padB
      let ox = padL,  oy = padT   // plot origin (top-left of plot area)

      func xOf(_ f: Double) -> CGFloat {
        ox + CGFloat(log10(f/fMin) / log10(fMax/fMin)) * pw
      }
      func yOf(_ db: Double) -> CGFloat {
        oy + CGFloat(1 - (db - dbMin) / (dbMax - dbMin)) * ph
      }

      // ---- Background ----
      ctx.fill(Path(CGRect(x: ox, y: oy, width: pw, height: ph)),
               with: .color(Color(.controlBackgroundColor)))

      // ---- dB grid lines ----
      let dbGrids: [Double] = [-24, -18, -12, -6, 0, 6, 12, 18, 24]
      for db in dbGrids {
        let y = yOf(db)
        var p = Path()
        p.move(to: CGPoint(x: ox, y: y))
        p.addLine(to: CGPoint(x: ox + pw, y: y))
        let isZero = db == 0
        ctx.stroke(p, with: .color(.primary.opacity(isZero ? 0.35 : 0.15)),
                   lineWidth: isZero ? 1.5 : 0.5)

        // dB label
        let label = db == 0 ? "0" : (db > 0 ? "+\(Int(db))" : "\(Int(db))")
        ctx.draw(Text(label).font(.system(size: 9)).foregroundStyle(.secondary),
                 at: CGPoint(x: ox - 6, y: y), anchor: .trailing)
      }

      // ---- Frequency grid lines ----
      let decades: [Double] = [10, 100, 1000, 10000]
      let multiples: [Double] = [2, 3, 4, 5, 6, 7, 8, 9]

      for dec in decades {
        // Minor lines first (thinner, lower opacity)
        for m in multiples {
          let f = dec * m
          guard f >= fMin, f <= fMax else { continue }
          let x = xOf(f)
          var p = Path()
          p.move(to: CGPoint(x: x, y: oy))
          p.addLine(to: CGPoint(x: x, y: oy + ph))
          ctx.stroke(p, with: .color(.primary.opacity(0.08)), lineWidth: 0.5)
        }
        // Major line at decade
        let f = dec * 10   // e.g. 100, 1k, 10k
        guard f >= fMin, f <= fMax else { continue }
        let x = xOf(f)
        var p = Path()
        p.move(to: CGPoint(x: x, y: oy))
        p.addLine(to: CGPoint(x: x, y: oy + ph))
        ctx.stroke(p, with: .color(.primary.opacity(0.2)), lineWidth: 0.5)

        // Frequency label
        let labelStr = f >= 1000 ? "\(Int(f/1000))k" : "\(Int(f))"
        ctx.draw(Text(labelStr).font(.system(size: 9)).foregroundStyle(.secondary),
                 at: CGPoint(x: x, y: oy + ph + 14), anchor: .center)
      }
      // Add 20 Hz and 20 kHz edge labels
      ctx.draw(Text("20").font(.system(size: 9)).foregroundStyle(.secondary),
               at: CGPoint(x: xOf(20), y: oy + ph + 14), anchor: .center)
      ctx.draw(Text("20k").font(.system(size: 9)).foregroundStyle(.secondary),
               at: CGPoint(x: xOf(20000), y: oy + ph + 14), anchor: .center)

      // ---- Plot border ----
      ctx.stroke(Path(CGRect(x: ox, y: oy, width: pw, height: ph)),
                 with: .color(.primary.opacity(0.25)), lineWidth: 0.5)

      // ---- Frequency response curve ----
      var curvePts: [CGPoint] = []
      curvePts.reserveCapacity(nPlot)
      for i in 0..<nPlot {
        let t = Double(i) / Double(nPlot - 1)
        let f = fMin * pow(fMax/fMin, t)
        let db = combinedMagnitudeDb(stages: stages, freqHz: f).clamped(to: dbMin...dbMax)
        curvePts.append(CGPoint(x: xOf(f), y: yOf(db)))
      }

      // Filled area under curve (between curve and 0 dB line)
      var fillPath = Path()
      fillPath.move(to: CGPoint(x: curvePts[0].x, y: yOf(0)))
      for pt in curvePts { fillPath.addLine(to: pt) }
      fillPath.addLine(to: CGPoint(x: curvePts.last!.x, y: yOf(0)))
      fillPath.closeSubpath()
      ctx.fill(fillPath, with: .color(.blue.opacity(0.12)))

      // Curve line
      var linePath = Path()
      linePath.move(to: curvePts[0])
      for pt in curvePts.dropFirst() { linePath.addLine(to: pt) }
      ctx.stroke(linePath, with: .color(.blue), lineWidth: 1.5)

    } // Canvas
    .clipShape(Rectangle())
  }
}

// MARK: - Helpers

private extension Double {
  func clamped(to range: ClosedRange<Double>) -> Double {
    min(max(self, range.lowerBound), range.upperBound)
  }
}
