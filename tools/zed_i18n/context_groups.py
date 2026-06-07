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

SETTING_ENUM_LABEL_KINDS = {
    "settings_enum_variant_label",
    "settings_enum_discriminant_label",
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
    prompt_components: list[dict[str, Any]] = field(default_factory=list)

    def all_groups(self) -> list[dict[str, Any]]:
        return [*self.settings, *self.connected_lines, *self.prompt_components]


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
        prompt_components=_build_prompt_component_groups(occurrences),
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
        group_sources = []
        seen_in_group: set[str] = set()
        for entry in group.get("entries", []):
            source = entry.get("source")
            if (
                isinstance(source, str)
                and source in target_sources
                and source not in consumed
                and source not in seen_in_group
            ):
                group_sources.append(source)
                seen_in_group.add(source)
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
    contexts: dict[str, list[dict[str, Any]]] = {}
    for group in groups.all_groups():
        payload = _context_payload(group, target_set)
        for entry in group.get("entries", []):
            source = entry.get("source")
            if isinstance(source, str) and source in target_set:
                contexts.setdefault(source, []).append(payload)
    return {
        source: payloads[0] if len(payloads) == 1 else _combined_context_payload(source, payloads)
        for source, payloads in contexts.items()
    }


def preferred_occurrence_from_context(
    context_group: dict[str, Any] | None,
    source: str,
) -> dict[str, Any] | None:
    if not context_group:
        return None
    child_groups = context_group.get("groups")
    if isinstance(child_groups, list):
        for child_group in child_groups:
            if not isinstance(child_group, dict):
                continue
            occurrence = preferred_occurrence_from_context(child_group, source)
            if occurrence is not None:
                return occurrence
    file = context_group.get("file")
    for entry in context_group.get("entries", []):
        if entry.get("source") != source:
            continue
        line = entry.get("line")
        entry_file = entry.get("file") or file
        if isinstance(entry_file, str) and isinstance(line, int):
            return {
                "file": entry_file,
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
    if group_type in {"all", "prompt", "prompt-components"}:
        _write_json(output_dir / "prompt-components.json", groups.prompt_components)
        (output_dir / "prompt-components.md").write_text(
            _prompt_components_markdown(groups.prompt_components),
            encoding="utf-8",
        )
    summary = {
        "settings": len(groups.settings),
        "connected_lines": len(groups.connected_lines),
        "prompt_components": len(groups.prompt_components),
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

    enum_groups = _build_setting_enum_groups(zed_root, occurrences)
    enum_groups_by_name = {
        group["context_key"]: group
        for group in enum_groups
        if isinstance(group.get("context_key"), str)
    }
    field_enum_types = _settings_field_enum_types(zed_root, set(enum_groups_by_name))
    path_enum_types = _settings_path_enum_types(zed_root, set(enum_groups_by_name))
    dynamic_discriminant_context_keys = {
        context_key.removesuffix("$")
        for group in groups.values()
        if isinstance((context_key := group.get("context_key")), str)
        and context_key.endswith("$")
    }
    linked_enum_names: set[str] = set()
    result: list[dict[str, Any]] = []
    for group in groups.values():
        roles = {entry["role"] for entry in group["entries"]}
        if "title" not in roles:
            continue
        source_path = zed_root / group["file"]
        enum_names: list[str] = []
        if source_path.exists():
            lines = source_path.read_text(encoding="utf-8").splitlines()
            enum_names = _enum_names_for_setting_block(
                lines,
                group["start_line"],
                group["end_line"],
                group.get("context_key"),
                field_enum_types,
                path_enum_types,
                set(enum_groups_by_name),
                skip_context_lookup=group.get("context_key") in dynamic_discriminant_context_keys,
            )
        if "description" not in roles and not enum_names:
            continue
        for enum_name in enum_names:
            enum_group = enum_groups_by_name.get(enum_name)
            if enum_group is None:
                continue
            group["entries"].extend(enum_group["entries"])
            linked_enum_names.add(enum_name)
        if enum_names:
            group["subtype"] = "setting_with_options"
            group["option_context_keys"] = enum_names
        group["entries"] = _dedupe_and_sort_entries(group["entries"])
        group["joined_source"] = _join_text(entry["source"] for entry in group["entries"])
        group["joined_current_translation"] = _join_text(
            entry.get("current_translation") for entry in group["entries"]
        )
        result.append(group)
    result.extend(
        group
        for group in enum_groups
        if group.get("context_key") not in linked_enum_names
    )
    return _sorted_groups(result)


def _build_setting_enum_groups(
    zed_root: Path,
    occurrences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        if occurrence["kind"] in SETTING_ENUM_LABEL_KINDS:
            by_file.setdefault(occurrence["file"], []).append(occurrence)

    groups: dict[str, dict[str, Any]] = {}
    for file, file_occurrences in by_file.items():
        source_path = zed_root / file
        if not source_path.exists():
            continue
        lines = source_path.read_text(encoding="utf-8").splitlines()
        for occurrence in file_occurrences:
            block = _setting_enum_block_for_line(lines, occurrence["line"])
            if block is None:
                continue
            enum_name, start_line, end_line = block
            group_id = f"settings_enum:{file}:{start_line}"
            group = groups.setdefault(
                group_id,
                {
                    "id": group_id,
                    "type": "setting",
                    "subtype": "settings_enum",
                    "file": file,
                    "start_line": start_line,
                    "end_line": end_line,
                    "context_key": enum_name,
                    "entries": [],
                },
            )
            group["entries"].append(_group_entry(occurrence, "option"))

    result: list[dict[str, Any]] = []
    for group in groups.values():
        group["entries"] = _dedupe_and_sort_entries(group["entries"])
        if len(group["entries"]) < 2:
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


def _build_prompt_component_groups(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        subtype = _prompt_component_subtype(occurrence)
        if subtype is None:
            continue
        grouped.setdefault((occurrence["file"], subtype), []).append(occurrence)

    groups: list[dict[str, Any]] = []
    for (file, subtype), group_occurrences in grouped.items():
        if len(group_occurrences) < 2:
            continue
        entries = [
            _group_entry(occurrence, _prompt_component_role(occurrence))
            for occurrence in sorted(
                group_occurrences,
                key=lambda item: (item["line"], item.get("start_byte", 0), item["source"]),
            )
        ]
        start_line = entries[0]["line"]
        end_line = entries[-1]["line"]
        groups.append(
            {
                "id": f"prompt_components:{subtype}:{file}:{start_line}",
                "type": "prompt_components",
                "subtype": subtype,
                "file": file,
                "start_line": start_line,
                "end_line": end_line,
                "joined_source": _join_text(entry["source"] for entry in entries),
                "joined_current_translation": _join_text(
                    entry.get("current_translation") for entry in entries
                ),
                "entries": entries,
            }
        )
    return _sorted_groups(groups)


def _prompt_component_subtype(occurrence: dict[str, Any]) -> str | None:
    file = occurrence["file"]
    call = occurrence["call"]
    if file == "crates/project_panel/src/project_panel.rs":
        if call.startswith("delete_prompt_"):
            return "project_panel_delete_prompt"
        if call == "replace_prompt_message" or occurrence["source"] == "A file or folder with name {} ":
            return "project_panel_replace_prompt"
    if file == "crates/workspace/src/pane.rs" and call == "save_conflict_prompt":
        return "workspace_save_conflict_prompt"
    if file == "crates/agent/src/tools/tool_permissions.rs" and call == "authorize_dirty_buffer":
        return "agent_dirty_buffer_prompt"
    return None


def _prompt_component_role(occurrence: dict[str, Any]) -> str:
    call = occurrence["call"]
    if call.startswith("delete_prompt_"):
        return call.removeprefix("delete_prompt_")
    if call.endswith("_prompt_message"):
        return "message"
    if call.endswith("_prompt"):
        return "message"
    return call


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


def _setting_enum_block_for_line(
    lines: list[str],
    line_number: int,
) -> tuple[str, int, int] | None:
    line_index = line_number - 1
    for start_index in range(line_index, max(-1, line_index - 120), -1):
        line = _without_string_literals(lines[start_index])
        match = re.search(r"\bpub(?:\([^)]*\))?\s+enum\s+([A-Za-z0-9_]+)\s*\{", line)
        if match is None:
            continue
        end_line = _delimited_block_end(lines, start_index, "{", "}")
        if end_line is not None and start_index + 1 <= line_number <= end_line:
            return match.group(1), start_index + 1, end_line
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


def _settings_field_enum_types(zed_root: Path, enum_names: set[str]) -> dict[str, str]:
    settings_content_root = zed_root / "crates" / "settings_content" / "src"
    if not settings_content_root.exists():
        return {}

    candidates: dict[str, set[str]] = {}
    for path in settings_content_root.rglob("*.rs"):
        text = path.read_text(encoding="utf-8")
        for match in _settings_field_pattern().finditer(text):
            field_name = match.group(1)
            enum_name = _normalize_settings_enum_name(match.group(2), enum_names)
            if enum_name is None:
                continue
            candidates.setdefault(field_name, set()).add(enum_name)

    return {
        field_name: next(iter(types))
        for field_name, types in candidates.items()
        if len(types) == 1
    }


def _settings_path_enum_types(zed_root: Path, enum_names: set[str]) -> dict[str, str]:
    struct_fields = _settings_struct_fields(zed_root)
    enum_variant_fields = _settings_enum_variant_fields(zed_root)
    candidates: dict[str, set[str]] = {}

    def add_candidate(path_parts: list[str], type_name: str) -> None:
        enum_name = _normalize_settings_enum_name(type_name, enum_names)
        if enum_name is None:
            return
        candidates.setdefault(".".join(path_parts), set()).add(enum_name)

    def walk(struct_name: str, prefix: list[str], seen: set[str]) -> None:
        for field_name, type_name in struct_fields.get(struct_name, []):
            path_parts = [*prefix, field_name]
            add_candidate(path_parts, type_name)
            if type_name in struct_fields and type_name not in seen:
                walk(type_name, path_parts, {*seen, type_name})
            for variant_field_name, variant_type_name in enum_variant_fields.get(type_name, []):
                add_candidate([*path_parts, variant_field_name], variant_type_name)

    for struct_name in struct_fields:
        walk(struct_name, [], {struct_name})

    return {
        path: next(iter(types))
        for path, types in candidates.items()
        if len(types) == 1
    }


def _settings_struct_fields(zed_root: Path) -> dict[str, list[tuple[str, str]]]:
    settings_content_root = zed_root / "crates" / "settings_content" / "src"
    if not settings_content_root.exists():
        return {}

    structs: dict[str, list[tuple[str, str]]] = {}
    struct_pattern = re.compile(r"\bpub\s+struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
    field_pattern = _settings_field_pattern()
    for path in settings_content_root.rglob("*.rs"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for start_index, line in enumerate(lines):
            match = struct_pattern.search(line)
            if match is None:
                continue
            end_line = _delimited_block_end(lines, start_index, "{", "}")
            if end_line is None:
                continue
            block = "\n".join(lines[start_index:end_line])
            structs[match.group(1)] = [
                (field_match.group(1), field_match.group(2))
                for field_match in field_pattern.finditer(block)
            ]
    return structs


def _settings_enum_variant_fields(zed_root: Path) -> dict[str, list[tuple[str, str]]]:
    settings_content_root = zed_root / "crates" / "settings_content" / "src"
    if not settings_content_root.exists():
        return {}

    enums: dict[str, list[tuple[str, str]]] = {}
    enum_pattern = re.compile(r"\bpub\s+enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
    variant_field_pattern = re.compile(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
        r"(?:[A-Za-z_][A-Za-z0-9_]*::)*([A-Za-z_][A-Za-z0-9_]*)\s*,"
    )
    for path in settings_content_root.rglob("*.rs"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for start_index, line in enumerate(lines):
            match = enum_pattern.search(line)
            if match is None:
                continue
            end_line = _delimited_block_end(lines, start_index, "{", "}")
            if end_line is None:
                continue
            block = "\n".join(lines[start_index:end_line])
            fields = [
                (field_match.group(1), field_match.group(2))
                for field_match in variant_field_pattern.finditer(block)
            ]
            if fields:
                enums[match.group(1)] = fields
    return enums


def _settings_field_pattern() -> re.Pattern[str]:
    return re.compile(
        r"\bpub\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
        r"(?:Option\s*<\s*)?"
        r"(?:Vec\s*<\s*)?"
        r"(?:[A-Za-z_][A-Za-z0-9_]*::)*([A-Za-z_][A-Za-z0-9_]*)"
    )


def _enum_names_for_setting_block(
    lines: list[str],
    start_line: int,
    end_line: int,
    context_key: object,
    field_enum_types: dict[str, str],
    path_enum_types: dict[str, str],
    enum_names: set[str],
    *,
    skip_context_lookup: bool = False,
) -> list[str]:
    text = "\n".join(lines[start_line - 1 : end_line])
    dynamic_variant_child = re.search(r"=>\s*vec!\s*\[\s*SettingItem\s*\{", text) is not None
    names: list[str] = []

    if not dynamic_variant_child:
        for match in re.finditer(r"dynamic_variants::<settings::([A-Za-z_][A-Za-z0-9_]*)>", text):
            enum_name = _normalize_settings_enum_name(match.group(1), enum_names)
            if enum_name is not None and enum_name not in names:
                names.append(enum_name)

        for match in re.finditer(r"\bsettings::([A-Za-z_][A-Za-z0-9_]*Discriminants)\b", text):
            enum_name = _normalize_settings_enum_name(match.group(1), enum_names)
            if enum_name is not None and enum_name not in names:
                names.append(enum_name)

    path_key = _path_from_context_key(context_key)
    pick_path = _pick_path_from_setting_block(text)
    pick_field_name = _field_name_from_context_key(pick_path)
    context_conflicts_with_pick = (
        not dynamic_variant_child
        and path_key is not None
        and pick_field_name is not None
        and _field_name_from_context_key(path_key) != pick_field_name
    )
    if pick_path is not None and not dynamic_variant_child:
        enum_name = path_enum_types.get(pick_path)
        if enum_name is None and pick_field_name is not None:
            enum_name = field_enum_types.get(pick_field_name)
        if enum_name is not None and enum_name not in names:
            names.append(enum_name)

    matched_path = False
    if path_key is not None and not skip_context_lookup and not context_conflicts_with_pick:
        enum_name = path_enum_types.get(path_key)
        if enum_name is not None and enum_name not in names:
            names.append(enum_name)
            matched_path = True

    field_name = _field_name_from_context_key(context_key)
    if (
        field_name is not None
        and not skip_context_lookup
        and not matched_path
        and not context_conflicts_with_pick
    ):
        enum_name = field_enum_types.get(field_name)
        if enum_name is not None and enum_name not in names:
            names.append(enum_name)

    return names


def _pick_path_from_setting_block(text: str) -> str | None:
    pick_index = text.find("pick:")
    if pick_index < 0:
        return None
    write_index = text.find("write:", pick_index)
    pick_text = text[pick_index : write_index if write_index >= 0 else len(text)]
    paths = [
        path
        for match in re.finditer(
            r"settings_content((?:\s*\.as_ref\(\)\?|\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)",
            pick_text,
        )
        if (path := _settings_content_path_from_chain(match.group(1))) is not None
    ]
    if not paths:
        return None
    return max(paths, key=lambda path: path.count("."))


def _settings_content_path_from_chain(chain: str) -> str | None:
    fields = [
        field
        for field in re.findall(r"\.\s*([A-Za-z_][A-Za-z0-9_]*)", chain)
        if field != "as_ref"
    ]
    if not fields:
        return None
    return ".".join(fields)


def _path_from_context_key(context_key: object) -> str | None:
    if not isinstance(context_key, str) or not context_key:
        return None
    key = context_key.rstrip("$")
    return key or None


def _field_name_from_context_key(context_key: object) -> str | None:
    key = _path_from_context_key(context_key)
    if key is None:
        return None
    return key.rsplit(".", 1)[-1]


def _normalize_settings_enum_name(name: str, enum_names: set[str]) -> str | None:
    if name in enum_names:
        return name
    if name.endswith("Discriminants"):
        base_name = name.removesuffix("Discriminants")
        if base_name in enum_names:
            return base_name
    return None


def _group_entry(occurrence: dict[str, Any], role: str) -> dict[str, Any]:
    entry = {
        "role": role,
        "source": occurrence["source"],
        "file": occurrence["file"],
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
    deduped: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for entry in entries:
        deduped[(entry.get("file", ""), entry["source"], entry["role"], entry["line"])] = entry
    role_order = {
        "title": 0,
        "description": 1,
        "placeholder": 2,
        "button": 3,
        "option": 4,
    }
    return sorted(
        deduped.values(),
        key=lambda entry: (
            role_order.get(entry["role"], 99),
            entry.get("file", ""),
            entry["line"],
            entry["start_byte"],
            entry["source"],
        ),
    )


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


def _combined_context_payload(source: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen_entries: set[tuple[str, str, str, int]] = set()
    for payload in payloads:
        for entry in payload.get("entries", []):
            if not isinstance(entry, dict):
                continue
            key = (
                str(entry.get("file", "")),
                str(entry.get("source", "")),
                str(entry.get("role", "")),
                int(entry.get("line", 0) or 0),
            )
            if key in seen_entries:
                continue
            seen_entries.add(key)
            entries.append(entry)
    return {
        "type": "related_context_groups",
        "context_key": source,
        "groups": payloads,
        "entries": entries,
        "joined_source": " | ".join(
            payload.get("joined_source", "")
            for payload in payloads
            if isinstance(payload.get("joined_source"), str)
        ),
        "joined_current_translation": " | ".join(
            payload.get("joined_current_translation", "")
            for payload in payloads
            if isinstance(payload.get("joined_current_translation"), str)
            and payload.get("joined_current_translation")
        ),
    }


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
    return _line_group_markdown("Connected Line Groups", groups)


def _prompt_components_markdown(groups: list[dict[str, Any]]) -> str:
    return _line_group_markdown("Prompt Component Groups", groups)


def _line_group_markdown(title: str, groups: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", f"Total groups: {len(groups)}", ""]
    for group in groups:
        group_title = f"{group['file']}:{group['start_line']}-{group['end_line']}"
        if group.get("subtype"):
            group_title += f" `{group['subtype']}`"
        lines.extend(
            [
                f"## {group_title}",
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
