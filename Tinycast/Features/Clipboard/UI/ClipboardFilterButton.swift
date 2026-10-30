import SwiftUI
import ObservationPolyfill

struct ClipboardFilterButton: View {
    let filter: ClipboardFilter
    let isOpen: Bool
    let action: () -> Void

    var body: some View {
        WithObservationTracking {
            HeaderMenuButton(
                        title: filter.title,
                        systemImage: filter.systemImage,
                        isOpen: isOpen,
                        help: String(localized: "Filter by type  ⌘P"),
                        action: action)
        }
    }
}
