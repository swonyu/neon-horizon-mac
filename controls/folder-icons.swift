import AppKit
let folders = [("Work", "briefcase.fill"),
               ("Code", "chevron.left.forwardslash.chevron.right"),
               ("Screenshots", "camera.viewfinder"),
               ("Wallpapers", "photo.on.rectangle.angled")]
let output = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "generated-icons")
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
for (name, symbolName) in folders {
    guard let glyph = NSImage(systemSymbolName: symbolName, accessibilityDescription: name)?.withSymbolConfiguration(.init(pointSize: 470, weight: .semibold)),
          let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1024, pixelsHigh: 1024, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
          let context = NSGraphicsContext(bitmapImageRep: bitmap) else { fatalError("Cannot prepare \(name)") }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    NSColor.clear.setFill(); NSRect(x: 0, y: 0, width: 1024, height: 1024).fill()
    NSColor(srgbRed: 0.50, green: 0.10, blue: 0.34, alpha: 1).setFill()
    NSBezierPath(roundedRect: NSRect(x: 104, y: 626, width: 390, height: 166), xRadius: 52, yRadius: 52).fill()
    let body = NSBezierPath(roundedRect: NSRect(x: 104, y: 178, width: 816, height: 542), xRadius: 78, yRadius: 78)
    NSGradient(starting: NSColor(srgbRed: 0.61, green: 0.12, blue: 0.51, alpha: 1), ending: NSColor(srgbRed: 0.98, green: 0.25, blue: 0.56, alpha: 1))!.draw(in: body, angle: 90)
    NSColor.white.withAlphaComponent(0.22).setStroke(); body.lineWidth = 3; body.stroke()
    let symbol = glyph.withSymbolConfiguration(.init(paletteColors: [.white]))!
    let scale = min(490 / symbol.size.width, 346 / symbol.size.height)
    let w = symbol.size.width * scale, h = symbol.size.height * scale
    symbol.draw(in: NSRect(x: (1024-w)/2, y: 449-h/2, width: w, height: h), from: .zero, operation: .sourceOver, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    guard let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("PNG failed") }
    try png.write(to: output.appendingPathComponent(name + ".png"))
    assert(bitmap.pixelsWide == 1024 && bitmap.pixelsHigh == 1024)
}
print("Prepared four 1024-pixel icons. No folder icons changed. See docs/SETUP.md to apply them.")
