import Foundation
import Accelerate

struct ScopeFrame {
    let displaySamples: [Float]
    let frequency: Double?
    let peakToPeak: Float
    let sampleRate: Double
}

class ScopeProcessor {
    private static let ringSize = 131072  // 2^17, ~3s at 44.1kHz
    private var ring = [Float](repeating: 0, count: 131072)
    private var writePos = 0
    private var totalFilled = 0
    private let lock = NSLock()
    var sampleRate: Double = 44100

    func push(channelData: UnsafePointer<Float>, count: Int) {
        lock.lock()
        let n = Self.ringSize
        for i in 0..<count {
            ring[writePos] = channelData[i]
            writePos = (writePos + 1) & (n - 1)
        }
        totalFilled = min(totalFilled + count, n)
        lock.unlock()
    }

    func analyze() -> ScopeFrame? {
        // Snapshot ring buffer state under lock, copy data, then release
        lock.lock()
        let wp = writePos
        let filled = totalFilled
        let sr = sampleRate
        let analysisSize = min(filled, 65536)
        var samples = [Float](repeating: 0, count: analysisSize)
        if analysisSize > 0 {
            let n = Self.ringSize
            let start = (wp - analysisSize + n) & (n - 1)
            ring.withUnsafeBufferPointer { src in
                samples.withUnsafeMutableBufferPointer { dst in
                    if start + analysisSize <= n {
                        memcpy(dst.baseAddress!, src.baseAddress! + start,
                               analysisSize * MemoryLayout<Float>.stride)
                    } else {
                        let first = n - start
                        memcpy(dst.baseAddress!, src.baseAddress! + start,
                               first * MemoryLayout<Float>.stride)
                        memcpy(dst.baseAddress! + first, src.baseAddress!,
                               (analysisSize - first) * MemoryLayout<Float>.stride)
                    }
                }
            }
        }
        lock.unlock()

        guard analysisSize > 512 else { return nil }

        var minVal: Float = 0, maxVal: Float = 0
        vDSP_minv(samples, 1, &minVal, vDSP_Length(analysisSize))
        vDSP_maxv(samples, 1, &maxVal, vDSP_Length(analysisSize))
        let peakToPeak = maxVal - minVal
        guard peakToPeak > 0.00005 else { return nil }
        let midpoint = (maxVal + minVal) * 0.5

        let frequency = detectFrequency(samples: samples, midpoint: midpoint, sr: sr)

        let displayCount: Int
        if let freq = frequency {
            displayCount = min(Int(sr / freq * 2.5) + 1, analysisSize / 2)
        } else {
            displayCount = min(Int(sr * 0.025), analysisSize / 2)  // 25ms default
        }
        guard displayCount > 4 else { return nil }

        let threshold = midpoint + peakToPeak * 0.25
        let preRoll = max(displayCount / 8, 5)
        let searchStart = analysisSize / 4
        let searchEnd = max(searchStart + 2, (analysisSize * 3 / 4) - displayCount)

        var triggerPos = searchStart
        if searchEnd > searchStart + 1 {
            for i in searchStart..<(searchEnd - 1) {
                if samples[i] < threshold && samples[i + 1] >= threshold {
                    triggerPos = max(0, i - preRoll)
                    break
                }
            }
        }

        let endPos = min(triggerPos + displayCount, analysisSize)
        guard endPos > triggerPos else { return nil }

        return ScopeFrame(
            displaySamples: Array(samples[triggerPos..<endPos]),
            frequency: frequency,
            peakToPeak: peakToPeak,
            sampleRate: sr
        )
    }

    private func detectFrequency(samples: [Float], midpoint: Float, sr: Double) -> Double? {
        var crossings: [Int] = []
        for i in 1..<samples.count {
            if samples[i - 1] < midpoint && samples[i] >= midpoint {
                crossings.append(i)
                if crossings.count >= 40 { break }
            }
        }
        guard crossings.count >= 3 else { return nil }
        // Use first-to-last span for accuracy, averaged over all intervals
        let avgPeriod = Double(crossings.last! - crossings.first!) / Double(crossings.count - 1)
        guard avgPeriod > 2 else { return nil }
        let freq = sr / avgPeriod
        return (freq >= 10 && freq <= 22000) ? freq : nil
    }
}
