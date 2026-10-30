import AppKit
import SwiftUI

/// Uses the native Liquid Glass surface on current macOS, with an AppKit fallback
/// that remains available on Ventura and earlier supported macOS releases.
struct GlassEffectView: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        #if compiler(>=6.2)
            if #available(macOS 26.0, *) {
                return NSGlassEffectView()
            }
        #endif

        let view = NSVisualEffectView()
        view.material = .hudWindow
        view.blendingMode = .behindWindow
        view.state = .active
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}
