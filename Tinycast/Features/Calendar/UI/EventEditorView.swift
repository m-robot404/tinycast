import SwiftUI
import ObservationPolyfill

private struct EventMenuFramePreferenceKey: PreferenceKey {
    static var defaultValue: [EventEditorSession.Field: CGRect] = [:]
    static func reduce(
        value: inout [EventEditorSession.Field: CGRect],
        nextValue: () -> [EventEditorSession.Field: CGRect]
    ) {
        value.merge(nextValue(), uniquingKeysWith: { _, new in new })
    }
}

struct EventEditorView: View {
    @ObservationPolyfill.Bindable var editor: EventEditorSession
    let openMenuCorner: MenuPanelCorner?
    let openInputMenu: (PopoverMenuContent, MenuPanelCorner, Int) -> Void

    @Environment(CalendarCoordinator.self) private var coordinator
    @Environment(PaletteState.self) private var palette
    @Environment(\.metrics) private var metrics
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var focusedField: EventEditorSession.Field?
    @FocusState private var focusedControl: EventEditorSession.Field?
    @State private var menuFrames: [EventEditorSession.Field: CGRect] = [:]

    var body: some View {
        WithObservationTracking {
            ScrollView {
                        VStack(spacing: metrics.spacing.xxl) {
                            FormRow("Title") {
                                FormTextInput(
                                    text: $editor.draft.title, focused: titleFocused,
                                    placeholder: String(localized: "Event title"),
                                    label: String(localized: "Event title"), moveFocus: editor.advanceFocus
                                )
                                .frame(height: metrics.size.dialogButtonHeight)
                                .formFieldChrome(focused: focusedField == .title)
                            }
                            FormRow("Start") {
                                choice(
                                    String(localized: "Start"), field: .start,
                                    selection: $editor.draft.startOffsetMinutes,
                                    values: EventDraft.startOffsets,
                                    label: { EventDraft.label(startOffset: $0, locale: .current) })
                            }
                            FormRow("Duration") {
                                choice(
                                    String(localized: "Duration"), field: .duration,
                                    selection: $editor.draft.durationMinutes,
                                    values: EventDraft.durations,
                                    label: { EventDraft.label(duration: $0, locale: .current) })
                            }
                            FormRow {
                                Text("The event will be added to your default calendar.")
                                    .font(metrics.typography.rowTrailing)
                                    .foregroundStyle(Theme.Colors.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .font(metrics.typography.rowTitle)
                        .foregroundStyle(Theme.Colors.textPrimary)
                        .padding(.horizontal, metrics.spacing.xxxl * 2)
                        .padding(.vertical, metrics.spacing.md)
                    }
                    .edgeDissolve()
                    .onPreferenceChange(EventMenuFramePreferenceKey.self) { menuFrames = $0 }
                    .task(id: palette.focusToken) {
                        palette.noteEditingField(true)
                        await Task.yield()
                        guard !Task.isCancelled else { return }
                        focusedField = editor.focusedField
                    }
                    .onChange(of: editor.focusedField) { field in focusedField = field }
                    .onChange(of: focusedField) { field in
                        if let field { editor.focusedField = field }
                        focusedControl = field == .title ? nil : field
                    }
                    .onChange(of: focusedControl) { field in
                        if let field { focusedField = field }
                    }
                    .onDisappear {
                        coordinator.editorDidClose(editor)
                        palette.noteEditingField(false)
                    }
        }
    }

    private var titleFocused: Binding<Bool> {
        Binding(
            get: { focusedField == .title },
            set: { value in
                if value { focusedField = .title } else if focusedField == .title { focusedField = nil }
            })
    }

    private func choice(
        _ title: String, field: EventEditorSession.Field, selection: Binding<Int>,
        values: [Int], label: @escaping (Int) -> String
    ) -> some View {
        let frame = menuFrames[field] ?? .zero
        let isOpen = openMenuCorner == .belowControl(frame)
        let open = {
            let items = values.map { value in
                PopoverMenuItem(title: label(value), icon: .blank) { selection.wrappedValue = value }
            }
            openInputMenu(
                PopoverMenuContent(items: items), .belowControl(frame),
                values.firstIndex(of: selection.wrappedValue) ?? 0)
        }
        return Button(action: open) {
            HStack {
                Text(label(selection.wrappedValue))
                Spacer()
                Image(systemName: "chevron.down")
                    .font(metrics.typography.disclosure)
                    .foregroundStyle(Theme.Colors.textSecondary)
                    .rotationEffect(.degrees(isOpen ? 180 : 0))
                    .animation(reduceMotion ? nil : Theme.MenuMotion.chevronAnimation, value: isOpen)
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, metrics.spacing.xl)
            .frame(height: metrics.size.dialogButtonHeight)
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .focused($focusedControl, equals: field)
        .background(
            GeometryReader { proxy in
                Color.clear.preference(
                    key: EventMenuFramePreferenceKey.self,
                    value: [field: proxy.frame(in: .global)])
            }
        )
        .formFieldChrome(focused: focusedField == field)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
        .accessibilityValue(label(selection.wrappedValue))
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { open() }
    }
}
