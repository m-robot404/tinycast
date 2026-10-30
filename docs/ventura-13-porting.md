# macOS Ventura 13 port — engineering audit

**Status: not yet compatible.** This branch is an isolated porting track. It deliberately does not lower the production deployment target until the source has been migrated and a real Ventura build passes.

## Confirmed blockers in the current source

1. `project.yml` declares macOS 26.0 and Swift 6.0. The checked-in Xcode project is generated from this file.
2. `docs/development.md` requires macOS 26 and Xcode 27, explicitly citing Liquid Glass and the SwiftUI macro plugin.
3. `Tinycast/DesignSystem/GlassEffectView.swift` directly instantiates `NSGlassEffectView`. That type is not available in the macOS 13 SDK. A deployment-target change cannot make an SDK symbol exist.
4. The architecture document records 39 `@Observable` model types, and `AppCore.swift` is one concrete example. SwiftUI's native Observation integration begins at macOS 14, so Ventura needs a deliberate compatibility implementation (for example, a tested Observation backport plus corresponding SwiftUI view/environment changes) or a larger migration to `ObservableObject` / `@Published`.
5. The project embeds several helper applications and has extensive use of AppKit, SwiftUI, system services, and modern APIs. Each helper target and every API newer than macOS 13 must be audited independently; compiling only the main app target is insufficient.

## Porting sequence

### Phase 1 — establish a Ventura-compatible toolchain and baseline
- Use Xcode 15.1/15.2-era SDKs on a supported host, or a newer compiler with a macOS 13 deployment target while ensuring no unavailable SDK symbols leak into the source.
- Keep this branch separate from `main`.
- Run a full build of the app scheme, including embedded helper targets, with code signing disabled for CI diagnostics.

### Phase 2 — platform compatibility layer
- Replace the direct `NSGlassEffectView` dependency with a platform abstraction. Use the native glass view only when compiling with an SDK that declares it and use an AppKit visual-effect fallback on Ventura.
- Inventory all macOS 14–26 API references and add compile-time/runtime fallbacks where a Ventura equivalent exists.
- Remove or replace APIs with no safe Ventura equivalent; do not silently no-op essential launcher behavior.

### Phase 3 — observation and UI migration
- Choose one observation strategy for macOS 13. A backport requires updating imports, observable annotations, and SwiftUI tracking/environment call sites consistently. A partial macro substitution is not sufficient.
- Review every use of newer SwiftUI view modifiers, controls, menu-bar behavior, and AppKit window APIs.
- Preserve state propagation and keyboard focus behavior in tests.

### Phase 4 — helpers, permissions, and integrations
- Build and test ClipboardTextHelper, FileIndexHelper, DictationHelper, and every embedded executable at the same deployment target.
- Audit Vision, PDFKit, Core ML, Accessibility, Input Monitoring, login-item, Calendar/EventKit, Shortcuts, and Spaces integrations for Ventura availability and permission behavior.
- Verify the app bundle's nested code, entitlements, signing, and update path.

### Phase 5 — verification and release
- Run the complete test harness and localization/lint checks.
- Build and launch on a real macOS 13.3+ Apple Silicon machine. CI compilation alone cannot verify TCC prompts, menu-bar lifecycle, hotkeys, clipboard paste, Spaces, or helper startup.
- Produce and inspect an arm64 DMG and ZIP; verify nested signatures and install/update/uninstall behavior.
- Only after all gates pass, update the user-facing minimum-version badge, install instructions, release workflow, and Homebrew metadata.

## Current evidence

- `project.yml`: `deploymentTarget.macOS = 26.0`, `SWIFT_VERSION = 6.0`.
- `docs/development.md`: macOS 26 / Xcode 27 toolchain requirement.
- `Tinycast/DesignSystem/GlassEffectView.swift`: direct `NSGlassEffectView` use.
- `Tinycast/App/AppCore.swift`: native `@Observable` usage.
- Apple documents SwiftUI Observation support from macOS 14: https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro

## Important

This audit is not a compatibility claim and does not ship an app. The CI workflow on this branch is a diagnostic compile attempt against a macOS 13 deployment target; its first failures must be fixed in source before a Ventura build can be claimed.
