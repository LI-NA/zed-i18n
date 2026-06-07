from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re

from .rust_strings import (
    parse_rust_string_literal,
    rust_format_placeholders_compatible,
    rust_string_literal,
)


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
    applied_settings_enum_labels = False
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

        if not rust_format_placeholders_compatible(source, translation):
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
                if _is_settings_enum_label_occurrence(occurrence):
                    applied_settings_enum_labels = True
            else:
                stale_sources.add(source)

    if applied_settings_enum_labels:
        _disable_settings_dropdown_title_case(zed_root)

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
        if _is_settings_enum_label_occurrence(occurrence):
            return _insert_strum_serialize_attribute(
                file_path,
                lines,
                index,
                source,
                translation_literal,
                discriminant=occurrence.get("kind") == "settings_enum_discriminant_label",
            )
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


def _insert_strum_serialize_attribute(
    file_path: Path,
    lines: list[str],
    index: int,
    source: str,
    translation_literal: str,
    *,
    discriminant: bool,
) -> bool:
    if index < 0 or index >= len(lines):
        return False

    variant_index = _find_settings_enum_variant_index(lines, index, source)
    if variant_index is None:
        return False

    existing_attribute_index = _existing_strum_serialize_attribute_index(
        lines,
        variant_index,
        discriminant=discriminant,
    )
    if existing_attribute_index is not None:
        updated = _replace_serialize_literal(
            lines[existing_attribute_index],
            translation_literal,
        )
        if updated is None:
            return False
        if updated != lines[existing_attribute_index]:
            lines[existing_attribute_index] = updated
            file_path.write_text("".join(lines), encoding="utf-8")
        return True

    indent = lines[variant_index][: len(lines[variant_index]) - len(lines[variant_index].lstrip())]
    if discriminant:
        attribute = f"{indent}#[strum_discriminants(strum(serialize = {translation_literal}))]\n"
    else:
        attribute = f"{indent}#[strum(serialize = {translation_literal})]\n"

    lines.insert(variant_index, attribute)
    file_path.write_text("".join(lines), encoding="utf-8")
    return True


def _find_settings_enum_variant_index(
    lines: list[str],
    index: int,
    source: str,
) -> int | None:
    expected_identifier = _generated_variant_identifier(source)
    search_start = max(0, index - 120)
    search_end = min(len(lines), index + 121)
    candidates: list[int] = []
    for candidate_index in range(search_start, search_end):
        identifier = _enum_variant_identifier(lines[candidate_index])
        if identifier == expected_identifier:
            candidates.append(candidate_index)

    if candidates:
        return min(candidates, key=lambda candidate: (abs(candidate - index), candidate < index))

    if _enum_variant_identifier(lines[index]) is not None:
        return index
    return None


def _generated_variant_identifier(source: str) -> str:
    return "".join(part for part in source.split(" ") if part)


def _enum_variant_identifier(line: str) -> str | None:
    stripped = line.lstrip()
    if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("pub "):
        return None
    match = _ENUM_VARIANT_RE.match(line)
    if match is None:
        return None
    return match.group(1)


def _existing_strum_serialize_attribute_index(
    lines: list[str],
    variant_index: int,
    *,
    discriminant: bool,
) -> int | None:
    for index in range(variant_index - 1, -1, -1):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if stripped.startswith("///") or stripped.startswith("#["):
            if _is_matching_strum_serialize_attribute(stripped, discriminant=discriminant):
                return index
            continue
        break
    return None


def _is_matching_strum_serialize_attribute(line: str, *, discriminant: bool) -> bool:
    if "serialize" not in line:
        return False
    if discriminant:
        return line.startswith("#[strum_discriminants(")
    return line.startswith("#[strum(")


def _replace_serialize_literal(line: str, translation_literal: str) -> str | None:
    match = _STRUM_SERIALIZE_RE.search(line)
    if match is None:
        return None
    return line[: match.start(1)] + translation_literal + line[match.end(1) :]


def _disable_settings_dropdown_title_case(zed_root: Path) -> None:
    path = zed_root / "crates" / "settings_ui" / "src" / "settings_ui.rs"
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    start, end = _render_dropdown_function_span(text, path)
    block = text[start:end]
    patched_block = block
    patched_block = _replace_once_or_verify(
        patched_block,
        "    metadata: Option<&SettingsFieldMetadata>,\n",
        "    _metadata: Option<&SettingsFieldMetadata>,\n",
        "    _metadata: Option<&SettingsFieldMetadata>,\n",
        path,
    )
    patched_block = _replace_once_or_verify(
        patched_block,
        "    let should_do_titlecase = metadata\n"
        "        .and_then(|metadata| metadata.should_do_titlecase)\n"
        "        .unwrap_or(true);\n",
        "    let should_do_titlecase = false;\n",
        "    let should_do_titlecase = false;\n",
        path,
    )
    patched = text[:start] + patched_block + text[end:]
    if patched != text:
        path.write_text(patched, encoding="utf-8")


def _render_dropdown_function_span(text: str, path: Path) -> tuple[int, int]:
    start = text.find("fn render_dropdown<T>(")
    if start < 0:
        raise ValueError(f"expected render_dropdown function not found in {path}")

    open_index = text.find("{", start)
    if open_index < 0:
        raise ValueError(f"expected render_dropdown function body not found in {path}")

    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise ValueError(f"expected render_dropdown function end not found in {path}")


def _replace_once_or_verify(
    text: str,
    old: str,
    new: str,
    already_patched: str,
    path: Path,
) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if already_patched in text:
        return text
    raise ValueError(f"expected patch target not found in {path}: {old[:80]!r}")


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
        if source in _literal_sources(text[quote_index:end_index]):
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


def _literal_sources(literal: str) -> tuple[str, ...]:
    sources = [
        parse_rust_string_literal(_collapse_rust_string_line_continuations(literal)),
        parse_rust_string_literal(literal),
    ]
    return tuple(dict.fromkeys(sources))


def _collapse_rust_string_line_continuations(literal: str) -> str:
    return re.sub(r"\\\r?\n[ \t]*", "", literal)


def _is_doc_comment_occurrence(occurrence: dict[str, object]) -> bool:
    return occurrence.get("kind") == "rust_doc_comment" or occurrence.get("call") in {
        "rust_doc_comment",
        "action_doc_comment",
    }


def _is_settings_enum_label_occurrence(occurrence: dict[str, object]) -> bool:
    return occurrence.get("kind") in {
        "settings_enum_variant_label",
        "settings_enum_discriminant_label",
    }


_ENUM_VARIANT_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9_]*)\b(?=\s*(?:[,({=]|$))")
_STRUM_SERIALIZE_RE = re.compile(r'serialize\s*=\s*("(?:\\.|[^"\\])*")')
