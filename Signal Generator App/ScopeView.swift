import SwiftUI

struct ScopeView: View {
    let frame: ScopeFrame?

    private static let hDiv = 10
    private static let vDiv = 8

    var body: some View {
        VStack(spacing: 4) {
            Canvas { ctx, size in
                drawGrid(ctx: ctx, size: size)
                if let f = frame { drawWaveform(ctx: ctx, size: size, frame: f) }
            }
            .frame(maxWidth: .infinity, minHeight: 200)
            .background(Color(red: 0.04, green: 0.10, blue: 0.04))
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .overlay(alignment: .center) {
                if frame == nil {
                    Text("no signal")
                        .font(.system(.caption, design: .monospaced))
                        .foregroundColor(.green.opacity(0.4))
                }
            }

            readoutBar
        }
    }

    // MARK: - Drawing

    private func drawGrid(ctx: GraphicsContext, size: CGSize) {
        let dim    = Color.green.opacity(0.18)
        let center = Color.green.opacity(0.38)
        let H = Self.hDiv, V = Self.vDiv

        for i in 0...H {
            let x = size.width * CGFloat(i) / CGFloat(H)
            var p = Path()
            p.move(to: CGPoint(x: x, y: 0))
            p.addLine(to: CGPoint(x: x, y: size.height))
            ctx.stroke(p, with: .color(i == H / 2 ? center : dim), lineWidth: 0.5)
        }
        for i in 0...V {
            let y = size.height * CGFloat(i) / CGFloat(V)
            var p = Path()
            p.move(to: CGPoint(x: 0, y: y))
            p.addLine(to: CGPoint(x: size.width, y: y))
            ctx.stroke(p, with: .color(i == V / 2 ? center : dim), lineWidth: 0.5)
        }
    }

    private func drawWaveform(ctx: GraphicsContext, size: CGSize, frame: ScopeFrame) {
        let samples = frame.displaySamples
        guard samples.count >= 2 else { return }

        let vdiv  = vDivision(frame.peakToPeak)
        let range = vdiv * Float(Self.vDiv)
        let mid   = (samples.max()! + samples.min()!) * 0.5
        let lo    = mid - range * 0.5
        let hi    = mid + range * 0.5
        guard hi > lo else { return }

        var path = Path()
        for (i, s) in samples.enumerated() {
            let x    = size.width  * CGFloat(i) / CGFloat(samples.count - 1)
            let norm = CGFloat((s - lo) / (hi - lo))
            let y    = size.height * (1.0 - norm)
            i == 0 ? path.move(to: CGPoint(x: x, y: y)) : path.addLine(to: CGPoint(x: x, y: y))
        }
        ctx.stroke(path, with: .color(.green), lineWidth: 1.5)
    }

    // MARK: - Readout bar

    private var readoutBar: some View {
        HStack(spacing: 20) {
            readout("f",      frame.flatMap { $0.frequency }.map(fmtFreq)       ?? "---")
            readout("pk-pk",  frame.map { fmtAmp($0.peakToPeak) }              ?? "---")
            readout("t/div",  frame.map { fmtTime(timePerDiv($0)) }            ?? "---")
            readout("V/div",  frame.map { fmtAmp(vDivision($0.peakToPeak)) }   ?? "---")
            Spacer()
        }
        .font(.system(size: 11, design: .monospaced))
        .padding(.horizontal, 2)
    }

    private func readout(_ key: String, _ val: String) -> some View {
        HStack(spacing: 2) {
            Text(key + ":").foregroundColor(.secondary)
            Text(val)
        }
    }

    // MARK: - Scale helpers

    private func vDivision(_ pkpk: Float) -> Float {
        let perDiv = pkpk * 1.5 / Float(Self.vDiv)
        let steps: [Float] = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
        return steps.first { $0 >= perDiv } ?? steps.last!
    }

    private func timePerDiv(_ f: ScopeFrame) -> Double {
        Double(f.displaySamples.count) / f.sampleRate / Double(Self.hDiv)
    }

    // MARK: - Formatters

    private func fmtFreq(_ f: Double) -> String {
        f >= 1000 ? String(format: "%.2f kHz", f / 1000) : String(format: "%.1f Hz", f)
    }

    private func fmtAmp(_ v: Float) -> String {
        if v < 0.001 { return String(format: "%.4f", v) }
        if v < 0.01  { return String(format: "%.4f", v) }
        return String(format: "%.3f", v)
    }

    private func fmtTime(_ t: Double) -> String {
        if t < 0.001 { return String(format: "%.0f µs", t * 1e6) }
        if t < 1     { return String(format: "%.2f ms", t * 1e3) }
        return String(format: "%.2f s", t)
    }
}
