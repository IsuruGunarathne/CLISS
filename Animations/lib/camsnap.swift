// camsnap <dir> <count> <interval>: save <count> photos from the default camera
// into <dir> as 01.jpg, 02.jpg, ..., one every <interval> seconds.
// Exit codes: 0 saved, 2 no camera, 3 camera access denied, 4 timed out, 5 couldn't write.
import AVFoundation
import AppKit

final class Burst: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let dir: URL
    let count: Int
    let interval: Double
    var next: Date? = nil
    var saved: [(url: URL, brightness: Double)] = []
    init(_ dir: URL, _ count: Int, _ interval: Double) {
        self.dir = dir
        self.count = count
        self.interval = interval
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput buffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard saved.count < count, let pixels = CMSampleBufferGetImageBuffer(buffer) else { return }
        let now = Date()
        if let due = next, now < due { return }
        next = (next ?? now).addingTimeInterval(interval)
        let url = dir.appendingPathComponent(String(format: "%02d.jpg", saved.count + 1))
        let rep = NSBitmapImageRep(ciImage: CIImage(cvPixelBuffer: pixels))
        guard let jpeg = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.85]),
              (try? jpeg.write(to: url)) != nil else { exit(5) }
        saved.append((url, brightness(pixels)))
        if saved.count == count {
            dropWarmUp()
            exit(0)
        }
    }

    /// The first frames are dark while the camera sets its exposure: drop the
    /// ones at the start that are much darker than the brightest frame.
    func dropWarmUp() {
        let brightest = saved.map { $0.brightness }.max() ?? 0
        for frame in saved {
            if frame.brightness >= brightest * 0.4 { break }
            try? FileManager.default.removeItem(at: frame.url)
        }
    }

    /// Average brightness (0-255) of a frame, from every 16th pixel of its luma plane.
    func brightness(_ pixels: CVPixelBuffer) -> Double {
        CVPixelBufferLockBaseAddress(pixels, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixels, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddressOfPlane(pixels, 0) else { return 0 }
        let luma = base.assumingMemoryBound(to: UInt8.self)
        let width = CVPixelBufferGetWidthOfPlane(pixels, 0)
        let height = CVPixelBufferGetHeightOfPlane(pixels, 0)
        let row = CVPixelBufferGetBytesPerRowOfPlane(pixels, 0)
        var sum = 0, samples = 0
        for y in stride(from: 0, to: height, by: 16) {
            for x in stride(from: 0, to: width, by: 16) {
                sum += Int(luma[y * row + x])
                samples += 1
            }
        }
        return samples > 0 ? Double(sum) / Double(samples) : 0
    }
}

let args = CommandLine.arguments
guard args.count == 4, let count = Int(args[2]), count > 0,
      let interval = Double(args[3]), interval > 0 else {
    FileHandle.standardError.write("usage: camsnap <dir> <count> <interval>\n".data(using: .utf8)!)
    exit(64)
}
let asked = DispatchSemaphore(value: 0)
var granted = false
AVCaptureDevice.requestAccess(for: .video) { ok in granted = ok; asked.signal() }
asked.wait()
guard granted else { exit(3) }

guard let camera = AVCaptureDevice.default(for: .video),
      let input = try? AVCaptureDeviceInput(device: camera) else { exit(2) }
let session = AVCaptureSession()
session.sessionPreset = .high
let output = AVCaptureVideoDataOutput()
// a luma plane to measure brightness with
output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange]
let burst = Burst(URL(fileURLWithPath: args[1]), count, interval)
output.setSampleBufferDelegate(burst, queue: DispatchQueue(label: "camsnap"))
guard session.canAddInput(input), session.canAddOutput(output) else { exit(2) }
session.addInput(input)
session.addOutput(output)
session.startRunning()
DispatchQueue.main.asyncAfter(deadline: .now() + 5 + Double(count) * interval) { exit(4) }
dispatchMain()
