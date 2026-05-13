from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .rust_strings import parse_rust_string_literal, rust_format_placeholders, rust_string_literal


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.stale


def apply_translations(
    zed_root: Path,
    manifest: dict[str, dict[str, object]],
    translations: dict[str, str],
) -> ApplyReport:
    report = ApplyReport()
    accepted_sources: list[str] = []
    changed_sources: set[str] = set()
    stale_sources: set[str] = set()
    occurrences_by_file: dict[str, list[tuple[str, str, object]]] = defaultdict(list)

    for source, entry in manifest.items():
        if entry.get("status") != "accepted":
            report.skipped.append(source)
            continue

        accepted_sources.append(source)
        translation = translations.get(source)
        if translation is None:
            report.missing.append(source)
            continue

        if rust_format_placeholders(source) != rust_format_placeholders(translation):
            raise ValueError(f"placeholder mismatch for {source!r}")

        occurrences = entry.get("occurrences", [])
        for occurrence in occurrences:
            if not isinstance(occurrence, dict) or not isinstance(occurrence.get("file"), str):
                stale_sources.add(source)
                continue
            occurrences_by_file[occurrence["file"]].append((source, translation, occurrence))

    for occurrences in occurrences_by_file.values():
        for source, translation, occurrence in sorted(
            occurrences,
            key=lambda item: _occurrence_line(item[2]),
            reverse=True,
        ):
            if _apply_one(zed_root, source, translation, occurrence):
                changed_sources.add(source)
            else:
                stale_sources.add(source)

    report.applied.extend(
        source
        for source in accepted_sources
        if source in changed_sources and source not in stale_sources
    )
    report.stale.extend(source for source in accepted_sources if source in stale_sources)

    return report


def _occurrence_line(occurrence: object) -> int:
    if not isinstance(occurrence, dict):
        return -1
    line = occurrence.get("line")
    return line if isinstance(line, int) else -1


def _apply_one(
    zed_root: Path,
    source: str,
    translation: str,
    occurrence: object,
) -> bool:
    if not isinstance(occurrence, dict):
        return False
    relative_file = occurrence.get("file")
    line_number = occurrence.get("line")
    if not isinstance(relative_file, str) or not isinstance(line_number, int):
        return False

    file_path = zed_root / relative_file
    if not file_path.exists():
        return False

    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    index = line_number - 1
    if index < 0 or index >= len(lines):
        return False

    if _is_doc_comment_occurrence(occurrence):
        if source not in lines[index]:
            return False
        lines[index] = lines[index].replace(source, translation, 1)
        file_path.write_text("".join(lines), encoding="utf-8")
        return True

    source_literal = rust_string_literal(source)
    translation_literal = rust_string_literal(translation)
    if source_literal not in lines[index]:
        return _apply_raw_string_literal(
            file_path,
            text,
            lines,
            index,
            source,
            translation_literal,
        )

    lines[index] = lines[index].replace(source_literal, translation_literal, 1)
    file_path.write_text("".join(lines), encoding="utf-8")
    return True


def _apply_raw_string_literal(
    file_path: Path,
    text: str,
    lines: list[str],
    index: int,
    source: str,
    translation_literal: str,
) -> bool:
    line_start = sum(len(line) for line in lines[:index])
    line_end = line_start + len(lines[index])
    span = _find_regular_string_literal_span(text, line_start, line_end, source)
    if span is None:
        return False
    start, end = span
    file_path.write_text(text[:start] + translation_literal + text[end:], encoding="utf-8")
    return True


def _find_regular_string_literal_span(
    text: str,
    start_index: int,
    end_search_index: int,
    source: str,
) -> tuple[int, int] | None:
    quote_index = text.find('"', start_index)
    while quote_index != -1 and quote_index < end_search_index:
        end_index = _regular_string_literal_end(text, quote_index)
        if end_index is None:
            return None
        if _literal_source(text[quote_index:end_index]) == source:
            return quote_index, end_index
        quote_index = text.find('"', end_index)
    return None


def _regular_string_literal_end(text: str, quote_index: int) -> int | None:
    escaped = False
    index = quote_index + 1
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return index + 1
        index += 1
    return None


def _literal_source(literal: str) -> str:
    return parse_rust_string_literal(literal)


def _is_doc_comment_occurrence(occurrence: dict[str, object]) -> bool:
    return occurrence.get("kind") == "rust_doc_comment" or occurrence.get("call") in {
        "rust_doc_comment",
        "action_doc_comment",
    }
