import SwiftUI
import ObservationPolyfill

struct CameraButton: View {
    /// Secondary also reads as "off": the mirror toggle dims rather than growing a second style.
    enum Emphasis {
        case primary
        case secondary
    }

    let title: String
    var keyCaps: [String] = []
    var emphasis: Emphasis = .primary
    let onActivate: () -> Void

    var body: some View {
        WithObservationTracking {
            Button(title, action: onActivate)
                        .buttonStyle(.modalAction(role, fillsWidth: false))
                        .tooltip(keyCaps: keyCaps)
        }
    }

    private var role: ModalActionButtonStyle.Role {
        emphasis == .primary ? .primary : .cancel
    }
}
