// camsnap <out.jpg>: take one photo with the default camera and save it as a JPEG.
// Exit codes: 0 saved, 2 no camera, 3 camera access denied, 4 timed out, 5 couldn't write.
import AVFoundation
import AppKit

final class Grabber: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let out: URL
    let start = Date()
    var frames = 0
    var last = -1.0
    var done = false
    init(_ out: URL) { self.out = out }

    func captureOutput(_ output: AVCaptureOutput, didOutput buffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard !done, let pixels = CMSampleBufferGetImageBuffer(buffer) else { return }
        frames += 1
        // The first frames are dark while the camera sets its exposure. Wait
        // until the brightness stops changing, or give up waiting after 2.5s.
        let now = brightness(pixels)
        let steady = frames > 2 && abs(now - last) < 3
        last = now
        if !steady && Date().timeIntervalSince(start) < 2.5 { return }
        done = true
        let rep = NSBitmapImageRep(ciImage: CIImage(cvPixelBuffer: pixels))
        let jpeg = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.85])
        exit((try? jpeg?.write(to: out)) != nil ? 0 : 5)
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
        var sum = 0, count = 0
        for y in stride(from: 0, to: height, by: 16) {
            for x in stride(from: 0, to: width, by: 16) {
                sum += Int(luma[y * row + x])
                count += 1
            }
        }
        return count > 0 ? Double(sum) / Double(count) : 0
    }
}

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write("usage: camsnap <out.jpg>\n".data(using: .utf8)!)
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
let grabber = Grabber(URL(fileURLWithPath: CommandLine.arguments[1]))
output.setSampleBufferDelegate(grabber, queue: DispatchQueue(label: "camsnap"))
guard session.canAddInput(input), session.canAddOutput(output) else { exit(2) }
session.addInput(input)
session.addOutput(output)
session.startRunning()
DispatchQueue.main.asyncAfter(deadline: .now() + 5) { exit(4) }
dispatchMain()
