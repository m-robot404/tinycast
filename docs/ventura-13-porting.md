# macOS Ventura 13 port — engineering audit

**Status: in progress; not yet verified compatible.** This branch is an isolated porting track. It lowers the deployment target to 13.0 to expose source/API incompatibilities, but the build and Ventura runtime checks must pass before the branch is considered usable.

## Confirmed blockers in the current source

1. The upstream baseline declared macOS 26.0 and Swift 6.0. This branch now lowers both `project.yml` and the checked-in Xcode project to macOS 13.0 while retaining Swift 6 language mode.
2. `docs/development.md` requires macOS 26 and Xcode 27, explicitly citing Liquid Glass and the SwiftUI macro plugin.
3. `Tinycast/DesignSystem/GlassEffectView.swift` originally instantiated `NSGlassEffectView` unconditionally. This branch now guards the newer symbol and provides an `NSVisualEffectView` fallback; the compatibility build must still confirm it compiles against an older SDK.
4. Clipboard OCR originally used the macOS 15 Swift Vision request API. This branch now uses the older `VNRecognizeTextRequest` API supported on Ventura.
5. The architecture document records 39 `@Observable` model types, and `AppCore.swift` is one concrete example. SwiftUI's native Observation integration begins at macOS 14, so Ventura needs a deliberate compatibility implementation (for example, a tested Observation backport plus corresponding SwiftUI view/environment changes) or a larger migration to `ObservableObject` / `@Published`.
6. The project embeds several helper applications and has extensive use of AppKit, SwiftUI, system services, and modern APIs. Each helper target and every API newer than macOS 13 must be audited independently; compiling only the main app target is insufficient.

## Porting sequence

### Phase 1 — establish a Ventura-compatible toolchain and baseline
- Use the dedicated Xcode 27 Apple Silicon CI runner with `MACOSX_DEPLOYMENT_TARGET=13.0` for compiler diagnostics. A later validation gate must still build and launch on an actual Ventura 13 Mac.
- Keep this branch separate from `main`.
- Run a full build of the app scheme, including embedded helper targets, with code signing disabled for CI diagnostics.

### Phase 2 — platform compatibility layer
- [x] Replace the direct `NSGlassEffectView` dependency with a platform abstraction. The branch now uses native glass only with a sufficiently new compiler on macOS 26+, and falls back to `NSVisualEffectView` on Ventura.
- [x] Replace the macOS 15-only Swift Vision `RecognizeTextRequest` calls in clipboard OCR with Ventura-compatible `VNRecognizeTextRequest` and `VNImageRequestHandler`.
- Remove or replace APIs with no safe Ventura equivalent; do not silently no-op essential launcher behavior.

### Phase 3 — observation and UI migration
- [x] Add the pinned `ObservationPolyfill` package for the native `@Observable`, `@ObservationIgnored`, `@Bindable`, and typed `@Environment` APIs on macOS 13.
- [x] Add an idempotent preparation script that imports the backport where required and wraps SwiftUI `View.body` implementations in `WithObservationTracking`.
- Review escaping SwiftUI closures (`sheet`, `popover`, `GeometryReader`, lazy containers, navigation destinations) for model reads that need their own tracking wrapper; validate with runtime diagnostics on Ventura.
- Review every use of newer SwiftUI view modifiers, controls, menu-bar behavior, and AppKit window APIs.
- Preserve state propagation and keyboard focus behavior in tests.

### Phase 4 — helpers, permissions, and integrations
- Build and test ClipboardTextHelper, FileIndexHelper, DictationHelper, and every embedded executable at the same deployment target. Qwen's stateful Core ML path requires macOS 15; this branch gates Qwen to macOS 15+ and keeps Parakeet as the Ventura dictation engine.
- Audit Vision, PDFKit, Core ML, Accessibility, Input Monitoring, login-item, Calendar/EventKit, Shortcuts, and Spaces integrations for Ventura availability and permission behavior.
- Verify the app bundle's nested code, entitlements, signing, and update path.

### Phase 5 — verification and release
- Run the complete test harness and localization/lint checks.
- Build and launch on a real macOS 13.3+ Apple Silicon machine. CI compilation alone cannot verify TCC prompts, menu-bar lifecycle, hotkeys, clipboard paste, Spaces, or helper startup.
- Produce and inspect an arm64 DMG and ZIP; verify nested signatures and install/update/uninstall behavior.
- Only after all gates pass, update the user-facing minimum-version badge, install instructions, release workflow, and Homebrew metadata.

## Current evidence

- `project.yml` and `Tinycast.xcodeproj/project.pbxproj` on this branch: macOS 13.0 deployment target; Swift language mode remains 6.0.
- `docs/development.md`: macOS 26 / Xcode 27 toolchain requirement.
- `Tinycast/DesignSystem/GlassEffectView.swift`: guarded native glass view with AppKit fallback.
- `Tinycast/Features/Clipboard/Service/ClipboardTextExtractor.swift`: Ventura-compatible Vision OCR path.
- `Tinycast/App/AppCore.swift`: Observation macros and `withObservationTracking`, now prepared through the pinned `ObservationPolyfill` dependency.
- `Scripts/prepare-ventura13.py`: imports the backport and wraps SwiftUI view bodies before compilation.
- `project.yml`: pins `moreswift/swift-observation-polyfill` to revision `d8843fa6dbf970aab42faaf101c9ce1cfd16fb94`.
- Apple documents SwiftUI Observation support from macOS 14: https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro

## Important

This audit is not a compatibility claim and does not ship an app. The CI workflow regenerates the Xcode project from `project.yml`, prepares the Observation backport, and attempts a full arm64 compile with a macOS 13 deployment target. A successful compile is not enough: escaping closure tracking and all runtime integrations still require a real Ventura test.
