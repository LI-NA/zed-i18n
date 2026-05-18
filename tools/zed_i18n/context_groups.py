from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Iterable


SETTING_ROLES = {
    "setting_title": "title",
    "setting_description": "description",
    "setting_placeholder": "placeholder",
    "settings_action_title": "title",
    "settings_action_description": "description",
    "settings_action_button": "button",
    "settings_subpage_title": "title",
    "settings_subpage_description": "description",
    "switch_label": "title",
    "switch_description": "description",
}

SETTING_BLOCK_PATTERNS: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    ("setting", re.compile(r"\bSettingItem\s*\{"), "{", "}"),
    ("settings_action", re.compile(r"\bActionLink\s*\{"), "{", "}"),
    ("settings_subpage", re.compile(r"\bSubPageLink\s*\{"), "{", "}"),
    ("switch_field", re.compile(r"\bSwitchField::new\s*\("), "(", ")"),
)

DOC_COMMENT_CALLS = {"action_doc_comment", "rust_doc_comment"}


@dataclass
class ContextGroups:
    settings: list[dict[str, Any]] = field(default_factory=list)
    connected_lines: list[dict[str, Any]] = field(default_factory=list)

    def all_groups(self) -> list[dict[str, Any]]:
        return [*self.settings, *self.connected_lines]


def build_context_groups(
    zed_root: Path,
    manifest: dict[str, dict[str, Any]],
    translations: dict[str, str] | None = None,
) -> ContextGroups:
    translations = translations or {}
    occurrences = _accepted_occurrences(manifest, translations)
    return ContextGroups(
        settings=_build_setting_groups(zed_root, occurrences),
        connected_lines=_build_connected_line_groups(occurrences),
    )


def source_batches_for_context_groups(
    sources: list[str],
    manifest: dict[str, dict[str, Any]],
    groups: ContextGroups,
    batch_size: int,
) -> list[list[str]]:
    target_sources = set(sources)
    consumed: set[str] = set()
    items: list[tuple[tuple[str, int, str], list[str]]] = []

    for group in _sorted_groups(groups.all_groups()):
        group_sources = [
            entry["source"]
            for entry in group.get("entries", [])
            if entry.get("source") in target_sources
        ]
        if not group_sources:
            continue
        items.append((_group_sort_key(group), group_sources))
        consumed.update(group_sources)

    for source in sources:
        if source in consumed:
            continue
        items.append((_source_sort_key(source, manifest), [source]))

    batches: list[list[str]] = []
    current: list[str] = []
    for _, item_sources in sorted(items, key=lambda item: item[0]):
        if current and len(current) + len(item_sources) > batch_size:
            batches.append(current)
            current = []
        current.extend(item_sources)
        if len(item_sources) >= batch_size:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    return batches


def context_groups_by_source(
    groups: ContextGroups,
    target_sources: Iterable[str],
) -> dict[str, dict[str, Any]]:
    target_set = set(target_sources)
    contexts: dict[str, dict[str, Any]] = {}
    for group in groups.all_groups():
        payload = _context_payload(group, target_set)
        for entry in group.get("entries", []):
            source = entry.get("source")
            if isinstance(source, str):
                contexts.setdefault(source, payload)
    return contexts


def preferred_occurrence_from_context(
    context_group: dict[str, Any] | None,
    source: str,
) -> dict[str, Any] | None:
    if not context_group:
        return None
    file = context_group.get("file")
    for entry in context_group.get("entries", []):
        if entry.get("source") != source:
            continue
        line = entry.get("line")
        if isinstance(file, str) and isinstance(line, int):
            return {
                "file": file,
                "line": line,
                "kind": entry.get("kind", ""),
                "call": entry.get("call", ""),
                "start_byte": entry.get("start_byte", 0),
                "end_byte": entry.get("end_byte", 0),
            }
    return None


def write_context_group_reports(
    output_dir: Path,
    groups: ContextGroups,
    group_type: str = "all",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if group_type in {"all", "settings"}:
        _write_json(output_dir / "settings-groups.json", groups.settings)
        (output_dir / "settings-groups.md").write_text(
            _settings_markdown(groups.settings),
            encoding="utf-8",
        )
    if group_type in {"all", "connected"}:
        _write_json(output_dir / "connected-lines.json", groups.connected_lines)
        (output_dir / "connected-lines.md").write_text(
            _connected_lines_markdown(groups.connected_lines),
            encoding="utf-8",
        )
    summary = {
        "settings": len(groups.settings),
        "connected_lines": len(groups.connected_lines),
    }
    _write_json(output_dir / "summary.json", summary)


def _accepted_occurrences(
    manifest: dict[str, dict[str, Any]],
    translations: dict[str, str],
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for source, entry in manifest.items():
        if entry.get("status") != "accepted":
            continue
        for occurrence in entry.get("occurrences", []):
            if not isinstance(occurrence, dict):
                continue
            file = occurrence.get("file")
            line = occurrence.get("line")
            kind = occurrence.get("kind")
            call = occurrence.get("call")
            if not isinstance(file, str) or not isinstance(line, int):
                continue
            if not isinstance(kind, str) or not isinstance(call, str):
                continue
            occurrences.append(
                {
                    "source": source,
                    "file": file,
                    "line": line,
                    "kind": kind,
                    "call": call,
                    "start_byte": occurrence.get("start_byte", 0),
                    "end_byte": occurrence.get("end_byte", 0),
                    "current_translation": translations.get(source),
                }
            )
    return occurrences


def _build_setting_groups(
    zed_root: Path,
    occurrences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        if occurrence["kind"] in SETTING_ROLES:
            by_file.setdefault(occurrence["file"], []).append(occurrence)

    groups: dict[str, dict[str, Any]] = {}
    for file, file_occurrences in by_file.items():
        source_path = zed_root / file
        if not source_path.exists():
            continue
        lines = source_path.read_text(encoding="utf-8").splitlines()
        for occurrence in file_occurrences:
            block = _setting_block_for_line(lines, occurrence["line"])
            if block is None:
                continue
            group_type, start_line, end_line = block
            group_id = f"{group_type}:{file}:{start_line}"
            group = groups.setdefault(
                group_id,
                {
                    "id": group_id,
                    "type": "setting",
                    "subtype": group_type,
                    "file": file,
                    "start_line": start_line,
                    "end_line": end_line,
                    "context_key": _json_path_from_block(lines, start_line, end_line),
                    "entries": [],
                },
            )
            group["entries"].append(_group_entry(occurrence, SETTING_ROLES[occurrence["kind"]]))

    result: list[dict[str, Any]] = []
    for group in groups.values():
        group["entries"] = _dedupe_and_sort_entries(group["entries"])
        roles = {entry["role"] for entry in group["entries"]}
        if "title" not in roles or "description" not in roles:
            continue
        group["joined_source"] = _join_text(entry["source"] for entry in group["entries"])
        group["joined_current_translation"] = _join_text(
            entry.get("current_translation") for entry in group["entries"]
        )
        result.append(group)
    return _sorted_groups(result)


def _build_connected_line_groups(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        occurrence
        for occurrence in occurrences
        if occurrence["call"] in DOC_COMMENT_CALLS
        or occurrence["kind"] in {"rust_doc_comment", "action_description"}
        and occurrence["call"] in DOC_COMMENT_CALLS
    ]
    by_file: dict[str, list[dict[str, Any]]] = {}
    for occurrence in candidates:
        by_file.setdefault(occurrence["file"], []).append(occurrence)

    groups: list[dict[str, Any]] = []
    for file, file_occurrences in by_file.items():
        current: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for occurrence in sorted(file_occurrences, key=lambda item: (item["line"], item["start_byte"])):
            adjacent = previous is not None and occurrence["line"] == previous["line"] + 1
            same_call = previous is not None and occurrence["call"] == previous["call"]
            if adjacent and same_call:
                current.append(occurrence)
            else:
                _append_connected_group(groups, file, current)
                current = [occurrence]
            previous = occurrence
        _append_connected_group(groups, file, current)
    return _sorted_groups(groups)


def _append_connected_group(
    groups: list[dict[str, Any]],
    occurrences: str,
    current: list[dict[str, Any]],
) -> None:
    if len(current) < 2:
        return
    file = occurrences
    entries = [_group_entry(occurrence, "line") for occurrence in current]
    start_line = entries[0]["line"]
    end_line = entries[-1]["line"]
    group = {
        "id": f"connected_lines:{file}:{start_line}",
        "type": "connected_lines",
        "file": file,
        "start_line": start_line,
        "end_line": end_line,
        "joined_source": _join_text(entry["source"] for entry in entries),
        "joined_current_translation": _join_text(
            entry.get("current_translation") for entry in entries
        ),
        "entries": entries,
    }
    groups.append(group)


def _setting_block_for_line(
    lines: list[str],
    line_number: int,
) -> tuple[str, int, int] | None:
    line_index = line_number - 1
    for start_index in range(line_index, max(-1, line_index - 80), -1):
        line = _without_string_literals(lines[start_index])
        for group_type, pattern, open_char, close_char in SETTING_BLOCK_PATTERNS:
            if not pattern.search(line):
                continue
            end_line = _delimited_block_end(lines, start_index, open_char, close_char)
            if end_line is not None and start_index + 1 <= line_number <= end_line:
                return group_type, start_index + 1, end_line
    return None


def _delimited_block_end(
    lines: list[str],
    start_index: int,
    open_char: str,
    close_char: str,
) -> int | None:
    depth = 0
    seen = False
    for index in range(start_index, len(lines)):
        line = _without_string_literals(lines[index])
        open_count = line.count(open_char)
        close_count = line.count(close_char)
        if open_count:
            seen = True
        depth += open_count - close_count
        if seen and depth <= 0:
            return index + 1
    return None


def _without_string_literals(line: str) -> str:
    result = []
    in_string = False
    escaped = False
    for char in line:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
                result.append(char)
            else:
                result.append(" ")
        else:
            if char == '"':
                in_string = True
            result.append(char)
    return "".join(result)


def _json_path_from_block(lines: list[str], start_line: int, end_line: int) -> str | None:
    text = "\n".join(lines[start_line - 1 : end_line])
    match = re.search(r'json_path:\s*Some\(\s*"((?:\\.|[^"\\])*)"', text)
    if match is None:
        return None
    return match.group(1)


def _group_entry(occurrence: dict[str, Any], role: str) -> dict[str, Any]:
    entry = {
        "role": role,
        "source": occurrence["source"],
        "kind": occurrence["kind"],
        "call": occurrence["call"],
        "line": occurrence["line"],
        "start_byte": occurrence.get("start_byte", 0),
        "end_byte": occurrence.get("end_byte", 0),
    }
    if occurrence.get("current_translation") is not None:
        entry["current_translation"] = occurrence["current_translation"]
    return entry


def _dedupe_and_sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, int], dict[str, Any]] = {}
    for entry in entries:
        deduped[(entry["source"], entry["role"], entry["line"])] = entry
    return sorted(deduped.values(), key=lambda entry: (entry["line"], entry["start_byte"], entry["role"]))


def _context_payload(group: dict[str, Any], target_sources: set[str]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in group.items()
        if key not in {"entries"} and value is not None
    }
    payload["entries"] = [
        {
            **entry,
            "target": entry.get("source") in target_sources,
        }
        for entry in group.get("entries", [])
    ]
    return payload


def _sorted_groups(groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(groups, key=_group_sort_key)


def _group_sort_key(group: dict[str, Any]) -> tuple[str, int, str]:
    file = group.get("file", "")
    line = group.get("start_line", 0)
    return (
        file if isinstance(file, str) else "",
        line if isinstance(line, int) else 0,
        str(group.get("id", "")),
    )


def _source_sort_key(
    source: str,
    manifest: dict[str, dict[str, Any]],
) -> tuple[str, int, str]:
    occurrences = manifest.get(source, {}).get("occurrences", [])
    first = occurrences[0] if occurrences and isinstance(occurrences[0], dict) else {}
    file = first.get("file", "")
    line = first.get("line", 0)
    return (
        file if isinstance(file, str) else "",
        line if isinstance(line, int) else 0,
        source,
    )


def _join_text(values: Iterable[str | None]) -> str:
    return " ".join(value.strip() for value in values if isinstance(value, str) and value.strip())


def _settings_markdown(groups: list[dict[str, Any]]) -> str:
    lines = ["# Setting Context Groups", "", f"Total groups: {len(groups)}", ""]
    for group in groups:
        title = f"{group['file']}:{group['start_line']}-{group['end_line']}"
        if group.get("context_key"):
            title += f" `{group['context_key']}`"
        lines.extend(
            [
                f"## {title}",
                "",
                "| Role | Source | Current Translation |",
                "|---|---|---|",
            ]
        )
        for entry in group.get("entries", []):
            lines.append(
                "| {role} | {source} | {translation} |".format(
                    role=_markdown_cell(entry.get("role", "")),
                    source=_markdown_cell(entry.get("source", "")),
                    translation=_markdown_cell(entry.get("current_translation", "")),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _connected_lines_markdown(groups: list[dict[str, Any]]) -> str:
    lines = ["# Connected Line Groups", "", f"Total groups: {len(groups)}", ""]
    for group in groups:
        lines.extend(
            [
                f"## {group['file']}:{group['start_line']}-{group['end_line']}",
                "",
                f"Source: {_markdown_text(group.get('joined_source', ''))}",
                "",
            ]
        )
        if group.get("joined_current_translation"):
            lines.extend(
                [
                    f"Current: {_markdown_text(group['joined_current_translation'])}",
                    "",
                ]
            )
        lines.extend(["| Line | Source | Current Translation |", "|---|---|---|"])
        for entry in group.get("entries", []):
            lines.append(
                "| {line} | {source} | {translation} |".format(
                    line=entry.get("line", ""),
                    source=_markdown_cell(entry.get("source", "")),
                    translation=_markdown_cell(entry.get("current_translation", "")),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _markdown_text(value: object) -> str:
    return str(value).replace("\n", " ")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
