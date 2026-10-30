#!/usr/bin/env python3
"""Prepare Tinycast's SwiftUI Observation code for the macOS 13 backport.

The project uses Apple's Observation API on macOS 14+. ObservationPolyfill supplies
the same model macros on macOS 13. SwiftUI view bodies must be wrapped in
WithObservationTracking when running on the older OS. This script makes those
source-level adaptations idempotently before the target is compiled.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "Tinycast"

NEEDS_POLYFILL = re.compile(
    r"@(?:Observable|ObservationIgnored|Bindable)\b"
    r"|@Environment\s*\("
    r"|\.environment\s*\("
    r"|\bvar\s+body\s*:\s*some\s+View\b"
    r"|\bwithObservationTracking\b"
)
VIEW_BODY = re.compile(r"\bvar\s+body\s*:\s*some\s+View\s*\{")

EXCLUDED_PARTS = {
    ("Features", "Dictation", "Helper"),
    ("Features", "FileSearch", "Helper"),
}
EXCLUDED_FILES = {
    "ClipboardTextExtractor.swift",
    "ClipboardTextHelper.swift",
}


def skip_string(source: str, start: int) -> int | None:
    """Return the first offset after a Swift string literal beginning at start."""
    i = start
    while i < len(source) and source[i] == "#":
        i += 1
    hashes = i - start
    if i >= len(source) or source[i] != '"':
        return None

    quote_count = 3 if source.startswith('"""', i) else 1
    terminator = ('"' * quote_count) + ("#" * hashes)
    i += quote_count

    while i < len(source):
        if source.startswith(terminator, i):
            return i + len(terminator)
        if source[i] == "\\":
            i += 1
            if hashes:
                while i < len(source) and source[i] == "#":
                    i += 1
            if i < len(source):
                i += 1
        else:
            i += 1
    return len(source)


def matching_brace(source: str, opening: int) -> int:
    """Find a matching Swift brace, ignoring strings and comments."""
    depth = 1
    i = opening + 1
    while i < len(source):
        if source.startswith("//", i):
            newline = source.find("\n", i + 2)
            i = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", i):
            i += 2
            comment_depth = 1
            while i < len(source) and comment_depth:
                if source.startswith("/*", i):
                    comment_depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    comment_depth -= 1
                    i += 2
                else:
                    i += 1
            continue

        string_end = skip_string(source, i)
        if string_end is not None:
            i = string_end
            continue

        char = source[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    raise ValueError(f"Unmatched Swift body brace at offset {opening}")


def code_mask(source: str) -> list[bool]:
    """Mark Swift code while excluding comments and string literal contents."""
    mask = [True] * len(source)
    i = 0
    while i < len(source):
        if source.startswith("//", i):
            end = source.find("\n", i + 2)
            end = len(source) if end < 0 else end
            for offset in range(i, end):
                mask[offset] = False
            i = end
            continue
        if source.startswith("/*", i):
            start = i
            i += 2
            depth = 1
            while i < len(source) and depth:
                if source.startswith("/*", i):
                    depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            for offset in range(start, i):
                mask[offset] = False
            continue
        end = skip_string(source, i)
        if end is not None:
            for offset in range(i, end):
                mask[offset] = False
            i = end
            continue
        i += 1
    return mask


def remove_top_level_return(source: str) -> str:
    """Remove a result-builder body's explicit top-level return, if present."""
    depth = 0
    i = 0
    while i < len(source):
        if source.startswith("//", i):
            newline = source.find("\n", i + 2)
            i = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", i):
            i += 2
            comment_depth = 1
            while i < len(source) and comment_depth:
                if source.startswith("/*", i):
                    comment_depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    comment_depth -= 1
                    i += 2
                else:
                    i += 1
            continue

        string_end = skip_string(source, i)
        if string_end is not None:
            i = string_end
            continue

        if source[i] == "{":
            depth += 1
            i += 1
            continue
        if source[i] == "}":
            depth -= 1
            i += 1
            continue

        if depth == 0 and source.startswith("return", i):
            before_ok = i == 0 or not (source[i - 1].isalnum() or source[i - 1] == "_")
            end = i + len("return")
            after_ok = end == len(source) or not (source[end].isalnum() or source[end] == "_")
            if before_ok and after_ok:
                while end < len(source) and source[end] in " \t":
                    end += 1
                return source[:i] + source[end:]
        i += 1
    return source


def wrap_view_bodies(source: str) -> tuple[str, int]:
    mask = code_mask(source)
    matches = [match for match in VIEW_BODY.finditer(source) if mask[match.start()]]
    wrapped = 0

    for match in reversed(matches):
        opening = match.end() - 1
        closing = matching_brace(source, opening)
        body = source[opening + 1 : closing]

        existing_wrapper = re.match(r"\s*WithObservationTracking\s*\{", body)
        if existing_wrapper:
            wrapper_open = opening + 1 + existing_wrapper.end() - 1
            wrapper_close = matching_brace(source, wrapper_open)
            wrapper_body = source[wrapper_open + 1 : wrapper_close]
            cleaned = remove_top_level_return(wrapper_body)
            if cleaned != wrapper_body:
                source = source[: wrapper_open + 1] + cleaned + source[wrapper_close:]
            continue

        inner = body.strip()
        if not inner:
            continue

        # Result-builder closures accept the expression directly, not an explicit return.
        inner = remove_top_level_return(inner)

        line_start = source.rfind("\n", 0, match.start()) + 1
        outer_indent = re.match(r"[ \t]*", source[line_start : match.start()]).group(0)
        wrapper_indent = outer_indent + "    "
        content_indent = wrapper_indent + "    "
        indented_inner = "\n".join(
            content_indent + line if line else ""
            for line in inner.splitlines()
        )

        replacement = (
            "\n"
            + wrapper_indent
            + "WithObservationTracking {\n"
            + indented_inner
            + "\n"
            + wrapper_indent
            + "}\n"
            + outer_indent
        )
        source = source[: opening + 1] + replacement + source[closing:]
        wrapped += 1

    return source, wrapped


def add_import(source: str) -> tuple[str, bool]:
    if "import ObservationPolyfill" in source:
        return source, False

    import_lines = list(
        re.finditer(r"(?m)^[ \t]*(?:@preconcurrency\s+)?import\s+[^\n]+", source)
    )
    if import_lines:
        position = import_lines[0].end()
        source = source[:position] + "\nimport ObservationPolyfill" + source[position:]
    else:
        source = "import ObservationPolyfill\n" + source
    return source, True


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(SOURCE_ROOT)
    if path.name in EXCLUDED_FILES:
        return True
    parts = relative.parts
    return any(
        len(parts) >= len(prefix) and parts[: len(prefix)] == prefix
        for prefix in EXCLUDED_PARTS
    )


def main() -> None:
    imported = 0
    wrapped = 0
    changed_files = 0

    for path in sorted(SOURCE_ROOT.rglob("*.swift")):
        if is_excluded(path):
            continue

        original = path.read_text(encoding="utf-8")
        if not NEEDS_POLYFILL.search(original):
            continue

        updated, count = wrap_view_bodies(original)
        updated = re.sub(r"(?<![A-Za-z0-9_.])@Bindable\b", "@ObservationPolyfill.Bindable", updated)
        updated, did_import = add_import(updated)
        wrapped += count
        imported += int(did_import)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1

    print(
        "Ventura Observation preparation complete: "
        f"{changed_files} files updated, {imported} polyfill imports added, "
        f"{wrapped} SwiftUI view bodies wrapped."
    )


if __name__ == "__main__":
    main()
