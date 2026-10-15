// camsnap <out.jpg>: take one photo with the default camera and save it as a JPEG.
// Exit codes: 0 saved, 2 no camera, 3 camera access denied, 4 timed out, 5 couldn't write.
import AVFoundation
import AppKit

final class Grabber: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let out: URL
    let start = Date()
    var done = false
    init(_ out: URL) { self.out = out }

    func captureOutput(_ output: AVCaptureOutput, didOutput buffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        // the first frames are dark while the camera adjusts its exposure
        if done || Date().timeIntervalSince(start) < 0.6 { return }
        guard let pixels = CMSampleBufferGetImageBuffer(buffer) else { return }
        done = true
        let rep = NSBitmapImageRep(ciImage: CIImage(cvPixelBuffer: pixels))
        let jpeg = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.85])
        exit((try? jpeg?.write(to: out)) != nil ? 0 : 5)
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
let grabber = Grabber(URL(fileURLWithPath: CommandLine.arguments[1]))
output.setSampleBufferDelegate(grabber, queue: DispatchQueue(label: "camsnap"))
guard session.canAddInput(input), session.canAddOutput(output) else { exit(2) }
session.addInput(input)
session.addOutput(output)
session.startRunning()
DispatchQueue.main.asyncAfter(deadline: .now() + 5) { exit(4) }
dispatchMain()
