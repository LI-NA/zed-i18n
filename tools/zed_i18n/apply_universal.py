from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from .extract import _title_case_identifier
from .rust_ast import make_rust_parser, node_text, walk_nodes
from .rust_strings import parse_rust_string_literal, rust_string_literal


_SCHEMA_METADATA_KINDS = {"rust_doc_comment"}
_ACTION_METADATA_KINDS = {"action_description"}
_SETTINGS_ENUM_KINDS = {
    "settings_enum_discriminant_label",
    "settings_enum_variant_label",
}
_RUST_UNICODE_ESCAPE_RE = re.compile(r"\\u\{[0-9A-Fa-f_]{1,6}\}")
_IMPLICIT_FORMAT_MACROS = (
    ("anyhow::anyhow", 0),
    ("anyhow::bail", 0),
    ("anyhow::ensure", 1),
    ("anyhow", 0),
    ("bail", 0),
    ("ensure", 1),
)
_KNOWN_KINDS = {
    "accessibility_label",
    "action_description",
    "agent_thread_title",
    "agent_tool_error",
    "agent_tool_output",
    "agent_tool_title",
    "agent_tool_warning",
    "announcement_bullet",
    "announcement_description",
    "announcement_heading",
    "announcement_primary_action",
    "announcement_secondary_action",
    "archive_bucket_label",
    "branch_filter_label",
    "branch_picker_subtitle",
    "bundled_file_title",
    "button",
    "button_label",
    "button_link",
    "call_diagnostic_label",
    "call_quality_label",
    "callout_description",
    "callout_title",
    "child_text",
    "chip",
    "commit_message_prefix",
    "completion_group_label",
    "completion_kind_tooltip",
    "configuration_error",
    "configured_api_card_label",
    "content_message",
    "context_menu_action",
    "context_menu_entry",
    "context_menu_header",
    "context_menu_submenu",
    "context_server_error",
    "context_server_modal_description",
    "context_server_modal_error",
    "debugger_memory_width",
    "debugger_mode_label",
    "debugger_view_label",
    "default_title",
    "description",
    "dock_position_label",
    "documentation_aside",
    "dropdown_label",
    "edit_prediction_popover",
    "elicitation_validation_error",
    "empty_state",
    "error_detail",
    "error_prompt",
    "fast_mode_confirmation_message",
    "fast_mode_confirmation_title",
    "feature_upsell",
    "file_dialog_title",
    "filter_label",
    "git_changed_files_count",
    "git_changed_files_count_fragment",
    "git_commit_fallback",
    "git_diff_path",
    "git_diff_title",
    "git_picker_tab",
    "git_remote_link",
    "git_remote_toast",
    "git_section_title",
    "git_timestamp_fallback",
    "git_worktree_picker_disabled_reason",
    "git_worktree_picker_label",
    "git_worktree_picker_section",
    "headline",
    "icon_label",
    "inlay_hint_label",
    "inline_description",
    "inline_prompt_tooltip",
    "inline_title",
    "input_error",
    "input_warning",
    "kernel_selector_label",
    "keybinding_hint_suffix",
    "keystroke_label",
    "label",
    "language_model_effort_label",
    "language_selector_label",
    "link",
    "list_bullet_item",
    "llm_provider_validation_error",
    "loading_label",
    "markdown_section_heading",
    "menu",
    "menu_item",
    "metric_description",
    "metric_title",
    "modal_header",
    "notification",
    "notification_action",
    "notification_error",
    "notification_message",
    "notification_more_info",
    "notification_title",
    "outline_external_file_label",
    "panel_tooltip",
    "path_prompt",
    "permission_option",
    "picker_action",
    "picker_option",
    "picker_prompt",
    "picker_section_header",
    "picker_separator",
    "placeholder",
    "platform_action_label",
    "prediction_status_label",
    "prediction_trigger_label",
    "profile_name_fallback",
    "project_empty_state_label",
    "project_name_fallback",
    "project_panel_undo_error",
    "project_panel_validation",
    "project_picker_header",
    "prompt_answer",
    "prompt_detail",
    "prompt_fragment",
    "prompt_local_command_description",
    "prompt_local_command_label",
    "prompt_message",
    "provider_credential_error",
    "provider_model_error",
    "relative_time",
    "remote_server_action",
    "retry_status_error",
    "rust_doc_comment",
    "sandbox_error_message",
    "sandbox_permission_path_caption",
    "sandbox_status_group",
    "sandbox_status_message",
    "sandbox_status_section",
    "search_option_label",
    "section_header",
    "setting_checkbox_label",
    "setting_description",
    "setting_placeholder",
    "setting_title",
    "settings_action_button",
    "settings_action_description",
    "settings_action_title",
    "settings_enum_discriminant_label",
    "settings_enum_variant_label",
    "settings_file_label",
    "settings_form_validation",
    "settings_list_section_title",
    "settings_page_description",
    "settings_page_title",
    "settings_section_header",
    "settings_subpage_breadcrumb",
    "settings_subpage_description",
    "settings_subpage_title",
    "settings_warning_banner",
    "settings_warning_detail",
    "shared_string",
    "skill_creator_error",
    "skill_illustration_source",
    "skill_load_error",
    "skill_share_link_error",
    "status_label",
    "status_message",
    "status_toast",
    "switch_description",
    "switch_label",
    "tab_title",
    "tab_tooltip",
    "table_header",
    "task_template_label",
    "thread_error_message",
    "thread_import_status",
    "toast",
    "toast_action",
    "toggle_button",
    "tool_permission_mode_label",
    "tool_permission_regex_explanation",
    "tool_permission_rule_section_description",
    "tool_permission_rule_section_title",
    "tool_permission_rule_type_label",
    "tool_permission_tool_description",
    "tool_permission_tool_name",
    "tool_permissions_note",
    "tool_permissions_security_note",
    "tool_permissions_summary",
    "tool_permissions_validation",
    "tooltip",
    "tooltip_meta",
    "unicode_confusable_description",
    "welcome_section_title",
    "window_title",
    "workspace_error_action",
    "workspace_error_message",
    "workspace_security_error",
}


@dataclass(frozen=True)
class HandlingEntry:
    source: str
    file: str
    line: int
    kind: str
    handling_class: str
    start_byte: int
    end_byte: int


@dataclass(frozen=True)
class HandlingMapReport:
    accepted_occurrences: int
    overlay_occurrences: int
    kind_count: int
    class_counts: dict[str, int]
    duplicates: tuple[str, ...]
    unclassified: tuple[str, ...]
    entries: tuple[HandlingEntry, ...]


@dataclass(frozen=True)
class UniversalApplyReport:
    ok: bool
    already_applied: bool
    applied_occurrences: int
    dependency_crates: tuple[str, ...]
    manifest_sha256: str


@dataclass(frozen=True)
class RuntimePatchReport:
    changed_files: int
    files: tuple[str, ...]


@dataclass(frozen=True)
class _Placeholder:
    key: str
    format_spec: str


@dataclass(frozen=True)
class _Replacement:
    start: int
    end: int
    text: str


def build_handling_map(
    zed_root: Path,
    manifest: Mapping[str, object],
) -> HandlingMapReport:
    accepted_by_file: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
    overlay_count = 0
    seen_spans: dict[tuple[str, int, int], str] = {}
    duplicates: list[str] = []

    for source, raw_entry in manifest.items():
        if not isinstance(source, str) or not isinstance(raw_entry, dict):
            continue
        if raw_entry.get("status") != "accepted":
            continue
        occurrences = raw_entry.get("occurrences", [])
        if not isinstance(occurrences, list):
            raise ValueError(f"manifest occurrences must be a list: {source!r}")
        for raw_occurrence in occurrences:
            if not isinstance(raw_occurrence, dict):
                raise ValueError(f"manifest occurrence must be an object: {source!r}")
            relative = raw_occurrence.get("file")
            start = raw_occurrence.get("start_byte")
            end = raw_occurrence.get("end_byte")
            if not isinstance(relative, str) or not isinstance(start, int) or not isinstance(end, int):
                raise ValueError(f"accepted occurrence is missing file or byte span: {source!r}")
            if relative.startswith("runtime-overlay/"):
                overlay_count += 1
                continue
            span = (relative, start, end)
            if span in seen_spans:
                duplicates.append(f"{relative}:{start}-{end}")
            else:
                seen_spans[span] = source
            accepted_by_file[relative].append((source, raw_occurrence))

    if duplicates:
        raise ValueError(f"duplicate accepted occurrence: {duplicates[0]}")

    parser = make_rust_parser()
    entries: list[HandlingEntry] = []
    kinds: set[str] = set()
    for relative, occurrences in sorted(accepted_by_file.items()):
        path = zed_root / relative
        if not path.exists():
            raise ValueError(f"accepted occurrence file does not exist: {relative}")
        text = path.read_text(encoding="utf-8")
        source_bytes = text.encode("utf-8")
        tree = parser.parse(source_bytes)
        nodes = {(node.start_byte, node.end_byte): node for node in walk_nodes(tree.root_node)}
        for source, occurrence in occurrences:
            start = int(occurrence["start_byte"])
            end = int(occurrence["end_byte"])
            line = occurrence.get("line")
            kind = occurrence.get("kind")
            if not isinstance(line, int) or not isinstance(kind, str):
                raise ValueError(f"accepted occurrence is missing line or kind: {relative}:{start}")
            if kind not in _KNOWN_KINDS:
                raise ValueError(f"unrecognized occurrence kind: {kind}")
            kinds.add(kind)
            if start < 0 or end <= start or end > len(source_bytes):
                raise ValueError(f"stale occurrence span: {relative}:{line}")
            raw = source_bytes[start:end].decode("utf-8")
            node = nodes.get((start, end))
            if (
                node is None
                and kind not in _SCHEMA_METADATA_KINDS
                and kind not in _ACTION_METADATA_KINDS
                and kind not in _SETTINGS_ENUM_KINDS
            ):
                raise ValueError(f"stale occurrence span: {relative}:{line}")
            handling_class = _classify_occurrence(kind, node, source_bytes)
            if handling_class in {
                "rewrite_static",
                "rewrite_format",
                "rewrite_const_context",
                "rewrite_thiserror",
            }:
                if node is None or node.type != "string_literal":
                    raise ValueError(f"stale occurrence span: {relative}:{line}")
                decoded_sources = {
                    parse_rust_string_literal(raw),
                    parse_rust_string_literal(re.sub(r"\\\r?\n[ \t]*", "", raw)),
                }
                if source not in decoded_sources and not isinstance(
                    occurrence.get("composite_rule_id"), str
                ):
                    raise ValueError(
                        f"stale occurrence source: {relative}:{line}: expected {source!r}, "
                        f"got {sorted(decoded_sources)!r}"
                    )
            else:
                normalized_raw = raw.strip().removeprefix("///").strip()
                metadata_sources = {raw, normalized_raw}
                if normalized_raw.startswith('"'):
                    metadata_sources.add(parse_rust_string_literal(normalized_raw))
                if kind in _SETTINGS_ENUM_KINDS:
                    if not normalized_raw.startswith('"'):
                        metadata_sources.add(_title_case_identifier(normalized_raw))
                if source not in metadata_sources:
                    raise ValueError(
                        f"stale occurrence source: {relative}:{line}: expected {source!r}"
                    )
            entries.append(
                HandlingEntry(
                    source=source,
                    file=relative,
                    line=line,
                    kind=kind,
                    handling_class=handling_class,
                    start_byte=start,
                    end_byte=end,
                )
            )

    entries.sort(key=lambda item: (item.file, item.start_byte, item.end_byte, item.source))
    overlaps = _overlapping_entries(entries)
    if overlaps:
        raise ValueError(f"overlapping accepted occurrences: {overlaps[0]}")
    class_counts = dict(sorted(Counter(entry.handling_class for entry in entries).items()))
    return HandlingMapReport(
        accepted_occurrences=len(entries),
        overlay_occurrences=overlay_count,
        kind_count=len(kinds),
        class_counts=class_counts,
        duplicates=(),
        unclassified=(),
        entries=tuple(entries),
    )


def apply_zed_runtime_patches(root: Path, zed_root: Path) -> RuntimePatchReport:
    planned: dict[Path, str] = {}
    _plan_zed_runtime_patches(root, zed_root, planned)
    changed = _write_planned_files(zed_root, planned)
    return RuntimePatchReport(changed_files=len(changed), files=tuple(changed))


def _write_planned_files(zed_root: Path, planned: Mapping[Path, str]) -> list[str]:
    changed: list[str] = []
    for path, text in sorted(planned.items(), key=lambda item: item[0].as_posix()):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        changed.append(path.relative_to(zed_root).as_posix())
    return changed


def _plan_zed_runtime_patches(
    root: Path,
    zed_root: Path,
    planned: dict[Path, str],
) -> None:
    """Validate and stage every structural patch into `planned` without
    touching the checkout, so anchor failures abort before the first write."""
    overlay_root = root / "tools" / "zed_i18n" / "runtime_overlay"

    for relative in (
        "crates/localization/Cargo.toml",
        "crates/localization/src/localization.rs",
        "crates/zed/src/zed/ui_locale.rs",
        "crates/settings_ui/src/components/locale_picker.rs",
        "crates/language_selector/src/localized_language_name.rs",
    ):
        source = overlay_root / relative
        if not source.exists():
            raise ValueError(f"runtime overlay file does not exist: {source}")
        destination = zed_root / relative
        overlay_text = source.read_text(encoding="utf-8")
        if not destination.exists() or destination.read_text(encoding="utf-8") != overlay_text:
            planned[destination] = overlay_text

    def patch(relative: str, old: str, new: str) -> None:
        path = zed_root / relative
        text = planned.get(path)
        if text is None:
            if not path.exists():
                raise ValueError(f"structural patch target does not exist: {relative}")
            text = path.read_text(encoding="utf-8")
        if new in text:
            return
        count = text.count(old)
        if count != 1:
            raise ValueError(
                f"structural patch anchor count for {relative} is {count}, expected 1"
            )
        planned[path] = text.replace(old, new, 1)

    def dependency(relative: str, after: str, name: str) -> None:
        path = zed_root / relative
        text = planned.get(path)
        if text is None:
            if not path.exists():
                raise ValueError(f"structural patch target does not exist: {relative}")
            text = path.read_text(encoding="utf-8")
        if re.search(rf"(?m)^{re.escape(name)}\.workspace\s*=\s*true\s*$", text):
            return
        patch(
            relative,
            f"{after}.workspace = true\n",
            f"{after}.workspace = true\n{name}.workspace = true\n",
        )

    patch(
        "Cargo.toml",
        '    "crates/language",\n',
        '    "crates/language",\n    "crates/localization",\n',
    )
    patch(
        "Cargo.toml",
        'language = { path = "crates/language" }\n',
        'language = { path = "crates/language" }\nlocalization = { path = "crates/localization" }\n',
    )

    ui_locale_model = '''#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, MergeFrom)]
#[serde(transparent)]
pub struct UiLocale(pub String);

impl Default for UiLocale {
    fn default() -> Self {
        Self("system".into())
    }
}

impl JsonSchema for UiLocale {
    fn schema_name() -> std::borrow::Cow<'static, str> {
        "UiLocale".into()
    }

    fn json_schema(_: &mut schemars::SchemaGenerator) -> schemars::Schema {
        schemars::json_schema!({ "type": "string" })
    }
}

'''
    patch(
        "crates/settings_content/src/settings_content.rs",
        "#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize, MergeFrom)]\n#[serde(transparent)]\npub struct FeatureFlagsMap(pub HashMap<String, String>);",
        ui_locale_model
        + "#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize, MergeFrom)]\n#[serde(transparent)]\npub struct FeatureFlagsMap(pub HashMap<String, String>);",
    )
    patch(
        "crates/settings_content/src/settings_content.rs",
        "    /// Local overrides for feature flags, keyed by flag name.\n    pub feature_flags: Option<FeatureFlagsMap>,",
        '''    /// The locale used by the Zed UI. `system` follows the operating system language.
    /// Changes apply after restarting Zed.
    ///
    /// Default: system
    pub ui_locale: Option<UiLocale>,

    /// Local overrides for feature flags, keyed by flag name.
    pub feature_flags: Option<FeatureFlagsMap>,''',
    )
    patch(
        "assets/settings/default.json",
        '  "$schema": "zed://schemas/settings",\n',
        '  "$schema": "zed://schemas/settings",\n  "ui_locale": "system",\n',
    )
    patch(
        "crates/settings/src/vscode_import.rs",
        "            modeline_lines: None,\n            feature_flags: None,",
        "            modeline_lines: None,\n            ui_locale: None,\n            feature_flags: None,",
    )

    zed_module_path = zed_root / "crates/zed/src/zed.rs"
    zed_module_text = planned.get(zed_module_path)
    if zed_module_text is None:
        zed_module_text = zed_module_path.read_text(encoding="utf-8")
    legacy_module = (
        "mod app_menus;\nmod localization;\n"
        "pub use localization::initialize_localization;\n"
    )
    current_module = (
        "mod app_menus;\nmod ui_locale;\n"
        "pub use ui_locale::initialize_localization;\n"
    )
    if legacy_module in zed_module_text and current_module not in zed_module_text:
        planned[zed_module_path] = zed_module_text.replace(
            legacy_module, current_module, 1
        )
    else:
        patch("crates/zed/src/zed.rs", "mod app_menus;\n", current_module)
    patch(
        "crates/zed/src/main.rs",
        "        zed::watch_settings_files(fs.clone(), cx);\n        handle_keymap_file_changes",
        "        zed::watch_settings_files(fs.clone(), cx);\n        zed::initialize_localization(fs.clone(), cx);\n        handle_keymap_file_changes",
    )
    dependency("crates/zed/Cargo.toml", "language_model", "localization")

    patch(
        "crates/settings_ui/src/components.rs",
        "mod input_field;\n",
        "mod input_field;\nmod locale_picker;\n",
    )
    patch(
        "crates/settings_ui/src/components.rs",
        "pub use input_field::*;\n",
        "pub use input_field::*;\npub(crate) use locale_picker::*;\n",
    )
    patch(
        "crates/settings_ui/src/page_data.rs",
        "fn general_page(cx: &App) -> SettingsPage {\n    fn general_settings_section(_cx: &App) -> Vec<SettingsPageItem> {\n        vec![\n",
        "fn general_page(cx: &App) -> SettingsPage {\n    fn general_settings_section(_cx: &App) -> Vec<SettingsPageItem> {\n        vec![\n            crate::components::locale_setting_item(),\n",
    )
    patch(
        "crates/settings_ui/src/settings_ui.rs",
        "        .add_basic_renderer::<settings::SaturatingBool>(render_toggle_button)\n",
        "        .add_basic_renderer::<settings::SaturatingBool>(render_toggle_button)\n        .add_basic_renderer::<settings::UiLocale>(crate::components::render_locale_picker)\n",
    )
    dependency("crates/settings_ui/Cargo.toml", "language", "localization")

    # Display-level "Plain Text" localization (VS Code convention: only the
    # synthetic plain-text language is localized, real language names stay
    # verbatim) in the language picker rows and the status bar button.
    patch(
        "crates/language_selector/src/language_selector.rs",
        "mod active_buffer_language;\n",
        "mod active_buffer_language;\nmod localized_language_name;\n",
    )
    patch(
        "crates/language_selector/src/language_selector.rs",
        "        let mut label = mat.string.clone();\n",
        "        let mut label ="
        " crate::localized_language_name::localized_language_name(&mat.string);\n",
    )
    # The fuzzy match positions are byte offsets into the English match string;
    # recompute them against the displayed label so a localized "Plain Text"
    # never feeds stale offsets into HighlightedLabel.
    patch(
        "crates/language_selector/src/language_selector.rs",
        "        let (label, language_icon) = self.language_data_for_match(mat, cx);\n",
        "        let (label, language_icon) = self.language_data_for_match(mat, cx);\n"
        "        let positions ="
        " crate::localized_language_name::localized_match_positions(&label, mat);\n",
    )
    patch(
        "crates/language_selector/src/language_selector.rs",
        ".child(HighlightedLabel::new(label, mat.positions.clone())),",
        ".child(HighlightedLabel::new(label, positions)),",
    )
    patch(
        "crates/language_selector/src/active_buffer_language.rs",
        '''            let active_language_text = if let Some(active_language_text) = active_language {
                active_language_text.to_string()
''',
        '''            let active_language_text = if let Some(active_language_text) = active_language {
                crate::localized_language_name::localized_language_name(
                    active_language_text.as_ref(),
                )
''',
    )
    dependency("crates/language_selector/Cargo.toml", "language", "localization")

    patch(
        "crates/json_schema_store/src/json_schema_store.rs",
        "    let schema = match schema_name {\n",
        "    let mut schema = match schema_name {\n",
    )
    patch(
        "crates/json_schema_store/src/json_schema_store.rs",
        "    };\n    Ok(schema)\n}\n\nconst JSONC_LANGUAGE_NAME",
        '''    };
    if matches!(schema_name, "settings" | "project_settings" | "keymap" | "action") {
        inject_ui_locale_schema(&mut schema);
        localize_schema_metadata(&mut schema);
    }
    Ok(schema)
}

const JSONC_LANGUAGE_NAME''',
    )
    schema_helpers = '''fn inject_ui_locale_schema(schema: &mut serde_json::Value) {
    use schemars::JsonSchema as _;

    let Some(defs) = schema.get_mut("$defs").and_then(|defs| defs.as_object_mut()) else {
        return;
    };
    let mut variants = vec![serde_json::Value::String("system".into())];
    variants.extend(
        localization::available_locales()
            .iter()
            .map(|locale| serde_json::Value::String(locale.id.clone())),
    );
    defs.insert(
        settings::UiLocale::schema_name().into_owned(),
        serde_json::json!({ "type": "string", "enum": variants }),
    );
}

fn localize_schema_metadata(value: &mut serde_json::Value) {
    match value {
        serde_json::Value::Object(object) => {
            for (key, value) in object {
                if matches!(
                    key.as_str(),
                    "title" | "description" | "markdownDescription" | "deprecationMessage"
                ) && let Some(source) = value.as_str()
                    && let Some(translation) = localization::lookup(source)
                {
                    *value = serde_json::Value::String(translation.to_owned());
                } else {
                    localize_schema_metadata(value);
                }
            }
        }
        serde_json::Value::Array(values) => {
            for value in values {
                localize_schema_metadata(value);
            }
        }
        _ => {}
    }
}

'''
    patch(
        "crates/json_schema_store/src/json_schema_store.rs",
        "/// Swaps the placeholder [`settings::FeatureFlagsMap`] subschema produced by\n",
        schema_helpers
        + "/// Swaps the placeholder [`settings::FeatureFlagsMap`] subschema produced by\n",
    )
    dependency("crates/json_schema_store/Cargo.toml", "language", "localization")

    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        "            documentation: action_documentation.get(action_name).copied(),",
        "            documentation: action_documentation\n                .get(action_name)\n                .copied()\n                .map(localization::translate_static),",
    )
    dependency("crates/keymap_editor/Cargo.toml", "language", "localization")

    patch(
        "crates/settings_ui/src/components/dropdown.rs",
        '''        let current_value_label = self.labels[self
            .variants
            .iter()
            .position(|v| *v == self.current_value)
            .unwrap()];

        let context_menu = window.use_keyed_state(current_value_label, cx, |window, cx| {''',
        '''        let current_value_index = self
            .variants
            .iter()
            .position(|value| *value == self.current_value)
            .unwrap();
        let current_value_label = self.labels[current_value_index];

        let context_menu = window.use_keyed_state(current_value_index, cx, |window, cx| {''',
    )
    patch(
        "crates/settings_ui/src/components/dropdown.rs",
        '''                        if self.should_do_title_case {
                            label.to_title_case()
                        } else {
                            label.to_string()
                        },''',
        '''                        translated_enum_label(label, self.should_do_title_case),''',
    )
    patch(
        "crates/settings_ui/src/components/dropdown.rs",
        '''            if self.should_do_title_case {
                current_value_label.to_title_case()
            } else {
                current_value_label.to_string()
            },''',
        '''            translated_enum_label(current_value_label, self.should_do_title_case),''',
    )
    patch(
        "crates/settings_ui/src/components/dropdown.rs",
        "#[derive(IntoElement)]\npub struct EnumVariantDropdown<T>",
        '''fn translated_enum_label(label: &str, title_case: bool) -> String {
    let display_source = if title_case {
        label.to_title_case()
    } else {
        label.to_owned()
    };
    // Labels with an explicit `#[strum(serialize = "...")]` value are
    // cataloged verbatim, so fall back to the untitle-cased label before
    // giving up (`"Prefer LF"` title-cases to `"Prefer Lf"` and would
    // otherwise never match its catalog key).
    localization::lookup(&display_source)
        .or_else(|| localization::lookup(label))
        .unwrap_or(&display_source)
        .to_owned()
}

#[derive(IntoElement)]
pub struct EnumVariantDropdown<T>''',
    )

    patch(
        "crates/ui/src/components/context_menu.rs",
        '.debug_selector(|| format!("MENU_ITEM-{}", label))',
        '''.debug_selector(|| {
                                action
                                    .as_ref()
                                    .map(|action| format!("MENU_ITEM-ACTION-{}", action.name()))
                                    .unwrap_or_else(|| format!("MENU_ITEM-INDEX-{ix}"))
                            })''',
    )
    dependency("crates/ui/Cargo.toml", "itertools", "localization")
    # The stable menu identities above change the debug selectors, so retarget
    # the upstream tests that still look menu items up by their English labels.
    patch(
        "crates/editor/src/mouse_context_menu.rs",
        '        assert!(cx.debug_bounds("MENU_ITEM-Copy").is_some());\n',
        '        assert!(cx.debug_bounds("MENU_ITEM-ACTION-editor::Copy").is_some());\n',
    )
    patch(
        "crates/collab/tests/integration/integration_tests.rs",
        '    assert!(cx.debug_bounds("MENU_ITEM-Close").is_none());\n',
        '    assert!(cx.debug_bounds("MENU_ITEM-ACTION-pane::CloseActiveItem").is_none());\n',
    )
    patch(
        "crates/collab/tests/integration/integration_tests.rs",
        '    assert!(cx.debug_bounds("MENU_ITEM-Close").is_some());\n',
        '    assert!(cx.debug_bounds("MENU_ITEM-ACTION-pane::CloseActiveItem").is_some());\n',
    )
    patch(
        "crates/agent_ui/src/agent_panel.rs",
        '            cx.debug_bounds("MENU_ITEM-Skills").is_some(),\n',
        '            cx.debug_bounds("MENU_ITEM-ACTION-agent::ManageSkills").is_some(),\n',
    )

    observer = '''#[cfg(debug_assertions)]
static TEXT_OBSERVER: std::sync::OnceLock<fn(&str)> = std::sync::OnceLock::new();

/// Installs a debug-only observer for text entering GPUI layout.
pub fn set_text_observer(observer: fn(&str)) {
    #[cfg(debug_assertions)]
    let _ = TEXT_OBSERVER.set(observer);
    #[cfg(not(debug_assertions))]
    let _ = observer;
}

#[inline]
fn observe_text(text: &str) {
    #[cfg(debug_assertions)]
    if let Some(observer) = TEXT_OBSERVER.get() {
        observer(text);
    }
}

'''
    gpui_text_path = zed_root / "crates/gpui/src/elements/text.rs"
    gpui_text = planned.get(gpui_text_path, gpui_text_path.read_text(encoding="utf-8"))
    if "pub fn set_text_observer" in gpui_text:
        if "/// Installs a debug-only observer for text entering GPUI layout." not in gpui_text:
            patch(
                "crates/gpui/src/elements/text.rs",
                "pub fn set_text_observer(observer: fn(&str)) {",
                "/// Installs a debug-only observer for text entering GPUI layout.\npub fn set_text_observer(observer: fn(&str)) {",
            )
    else:
        patch(
            "crates/gpui/src/elements/text.rs",
            "/// An [`Element`] that renders text.\n",
            observer + "/// An [`Element`] that renders text.\n",
        )
    patch(
        "crates/gpui/src/elements/text.rs",
        '''    ) -> (LayoutId, Self::RequestLayoutState) {
        let mut state = TextLayout::default();
        let layout_id = state.layout(SharedString::from(*self), None, window, cx);''',
        '''    ) -> (LayoutId, Self::RequestLayoutState) {
        observe_text(*self);
        let mut state = TextLayout::default();
        let layout_id = state.layout(SharedString::from(*self), None, window, cx);''',
    )
    patch(
        "crates/gpui/src/elements/text.rs",
        '''    ) -> (LayoutId, Self::RequestLayoutState) {
        let mut state = TextLayout::default();
        let layout_id = state.layout(self.clone(), None, window, cx);''',
        '''    ) -> (LayoutId, Self::RequestLayoutState) {
        observe_text(self.as_ref());
        let mut state = TextLayout::default();
        let layout_id = state.layout(self.clone(), None, window, cx);''',
    )

    _register_const_context_patches(patch, dependency)
    _register_thiserror_patches(patch, dependency)

    dependency("crates/auto_update_helper/Cargo.toml", "anyhow", "localization")
    dependency("crates/auto_update_helper/Cargo.toml", "localization", "serde")
    dependency("crates/auto_update_helper/Cargo.toml", "serde", "serde_json_lenient")
    patch(
        "crates/auto_update_helper/src/auto_update_helper.rs",
        '''        let app_dir = helper_dir
            .parent()
            .context("No parent directory")?
            .to_path_buf();

        log::info!''',
        '''        let app_dir = helper_dir
            .parent()
            .context("No parent directory")?
            .to_path_buf();
        initialize_localization(&app_dir);

        log::info!''',
    )
    helper_init = '''    #[derive(Default, serde::Deserialize)]
    struct LocaleSettings {
        ui_locale: Option<String>,
    }

    // Mirrors `paths::config_dir` for Windows (%APPDATA%/Zed) without pulling
    // the heavy paths/settings_json dependency trees into this small helper.
    fn zed_settings_path() -> Option<std::path::PathBuf> {
        let appdata = std::env::var_os("APPDATA")?;
        Some(
            std::path::Path::new(&appdata)
                .join("Zed")
                .join("settings.json"),
        )
    }

    fn initialize_localization(app_dir: &Path) {
        let user_preference = zed_settings_path()
            .and_then(|path| std::fs::read_to_string(path).ok())
            .and_then(|source| {
                serde_json_lenient::from_str::<LocaleSettings>(&source)
                    .ok()
                    .and_then(|settings| settings.ui_locale)
            });
        let legacy_locale = std::fs::read_to_string(
            app_dir.join("locales").join("legacy-locale"),
        )
        .ok()
        .map(|locale| locale.trim().to_owned())
        .filter(|locale| !locale.is_empty());
        localization::initialize(localization::InitRequest {
            user_preference: user_preference.as_deref(),
            legacy_locale: legacy_locale.as_deref(),
        });
    }

'''
    patch(
        "crates/auto_update_helper/src/auto_update_helper.rs",
        "    fn parse_args(input: impl IntoIterator<Item = String>) -> Args {\n",
        helper_init + "    fn parse_args(input: impl IntoIterator<Item = String>) -> Args {\n",
    )
    patch(
        "crates/auto_update_helper/src/auto_update_helper.rs",
        '''        let _ = unsafe {
            MessageBoxW(
                None,
                &HSTRING::from(content),
                windows::core::w!("Error: Zed update failed."),''',
        '''        let caption = HSTRING::from(localization::localized_str!(
            "Error: Zed update failed."
        ));
        let _ = unsafe {
            MessageBoxW(
                None,
                &HSTRING::from(content),
                &caption,''',
    )


def _register_const_context_patches(patch, dependency) -> None:
    patch(
        "crates/agent_ui/src/agent_configuration/configure_context_server_modal.rs",
        '''        const MODAL_DESCRIPTION: &str =
            "Check the server docs for required arguments and environment variables.";''',
        '''        let modal_description = localization::localized_str!(
            "Check the server docs for required arguments and environment variables."
        );''',
    )
    patch(
        "crates/agent_ui/src/agent_configuration/configure_context_server_modal.rs",
        "Label::new(MODAL_DESCRIPTION)",
        "Label::new(modal_description)",
    )
    dependency("crates/agent_ui/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/copilot_ui/src/sign_in.rs",
        '''const ERROR_LABEL: &str = "Copilot Edit Predictions had issues starting. You can try reinstalling it and signing in again.";''',
        '''fn error_label() -> &'static str {
    localization::localized_str!("Copilot Edit Predictions had issues starting. You can try reinstalling it and signing in again.")
}''',
    )
    patch(
        "crates/copilot_ui/src/sign_in.rs",
        "Label::new(ERROR_LABEL)",
        "Label::new(error_label())",
    )
    patch(
        "crates/copilot_ui/src/sign_in.rs",
        "ERROR_LABEL.into(),",
        "error_label().into(),",
    )
    dependency("crates/copilot_ui/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/debugger_tools/src/dap_log.rs",
        '''const ADAPTER_LOGS: &str = "Adapter Logs";
const RPC_MESSAGES: &str = "RPC Messages";
const INITIALIZATION_SEQUENCE: &str = "Initialization Sequence";''',
        '''fn adapter_logs_label() -> &'static str {
    localization::localized_str!("Adapter Logs")
}

fn rpc_messages_label() -> &'static str {
    localization::localized_str!("RPC Messages")
}

fn initialization_sequence_label() -> &'static str {
    localization::localized_str!("Initialization Sequence")
}''',
    )
    for old, new in (
        ("View::AdapterLogs => ADAPTER_LOGS", "View::AdapterLogs => adapter_logs_label()"),
        ("View::RpcMessages => RPC_MESSAGES", "View::RpcMessages => rpc_messages_label()"),
        (
            "View::InitializationSequence => INITIALIZATION_SEQUENCE",
            "View::InitializationSequence => initialization_sequence_label()",
        ),
        ("Label::new(ADAPTER_LOGS)", "Label::new(adapter_logs_label())"),
        ("Label::new(RPC_MESSAGES)", "Label::new(rpc_messages_label())"),
        (
            "Label::new(INITIALIZATION_SEQUENCE)",
            "Label::new(initialization_sequence_label())",
        ),
    ):
        patch("crates/debugger_tools/src/dap_log.rs", old, new)
    dependency("crates/debugger_tools/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/debugger_ui/src/new_process_modal.rs",
        '''static SELECT_DEBUGGER_LABEL: SharedString = SharedString::new_static("Select Debugger");''',
        '''fn select_debugger_label() -> SharedString {
    localization::localized_str!("Select Debugger").into()
}''',
    )
    patch(
        "crates/debugger_ui/src/new_process_modal.rs",
        "unwrap_or_else(|| SELECT_DEBUGGER_LABEL.clone())",
        "unwrap_or_else(select_debugger_label)",
    )
    patch(
        "crates/debugger_ui/src/session/running/memory_view.rs",
        '''static WIDTHS: [ViewWidth; 7] = [
    ViewWidth::new(1, "1 byte"),
    ViewWidth::new(2, "2 bytes"),
    ViewWidth::new(4, "4 bytes"),
    ViewWidth::new(8, "8 bytes"),
    ViewWidth::new(16, "16 bytes"),
    ViewWidth::new(32, "32 bytes"),
    ViewWidth::new(64, "64 bytes"),
];''',
        '''fn widths() -> &'static [ViewWidth; 7] {
    static WIDTHS: std::sync::OnceLock<[ViewWidth; 7]> = std::sync::OnceLock::new();
    WIDTHS.get_or_init(|| [
        ViewWidth::new(1, localization::localized_str!("1 byte")),
        ViewWidth::new(2, localization::localized_str!("2 bytes")),
        ViewWidth::new(4, localization::localized_str!("4 bytes")),
        ViewWidth::new(8, localization::localized_str!("8 bytes")),
        ViewWidth::new(16, localization::localized_str!("16 bytes")),
        ViewWidth::new(32, localization::localized_str!("32 bytes")),
        ViewWidth::new(64, localization::localized_str!("64 bytes")),
    ])
}''',
    )
    for old, new in (
        ("WIDTHS[4].clone()", "widths()[4].clone()"),
        ("for width in &WIDTHS", "for width in widths()"),
        ("WIDTHS\n                    .iter()", "widths()\n                    .iter()"),
    ):
        patch("crates/debugger_ui/src/session/running/memory_view.rs", old, new)
    dependency("crates/debugger_ui/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/editor/src/code_lens.rs",
        '''static EMPTY_LENS_FALLBACK_TITLE: SharedString = SharedString::new_static("0 references");''',
        '''fn empty_lens_fallback_title() -> &'static SharedString {
    static TITLE: std::sync::OnceLock<SharedString> = std::sync::OnceLock::new();
    TITLE.get_or_init(|| localization::localized_str!("0 references").into())
}''',
    )
    patch(
        "crates/editor/src/code_lens.rs",
        ".or_else(|| item.action.resolved.then_some(&EMPTY_LENS_FALLBACK_TITLE))",
        ".or_else(|| item.action.resolved.then_some(empty_lens_fallback_title()))",
    )
    patch(
        "crates/editor/src/editor.rs",
        '''        const RIGHT_CLICK_HINT: &str = "right-click for more options";''',
        '''        #[allow(non_snake_case)]
        let RIGHT_CLICK_HINT = localization::localized_str!("right-click for more options");''',
    )
    dependency("crates/editor/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/git_ui/src/remote_output.rs",
        "pending_label = Some(label);",
        "pending_label = Some(localization::translate_static(label));",
    )
    dependency("crates/git_ui/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        '''const NO_ACTION_ARGUMENTS_TEXT: SharedString = SharedString::new_static("<no arguments>");''',
        '''fn no_action_arguments_text() -> SharedString {
    localization::localized_str!("<no arguments>").into()
}''',
    )
    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        '''    const GLOBAL: SharedString = SharedString::new_static("<global>");''',
        '''    fn global_label() -> SharedString {
        localization::localized_str!("<global>").into()
    }''',
    )
    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        "muted_styled_text(KeybindContextString::GLOBAL, cx)",
        "muted_styled_text(KeybindContextString::global_label(), cx)",
    )
    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        '''                                                const NULL: SharedString =
                                                    SharedString::new_static("<null>");
                                                muted_styled_text(NULL, cx)''',
        '''                                                let null: SharedString =
                                                    localization::localized_str!("<null>").into();
                                                muted_styled_text(null, cx)''',
    )
    patch(
        "crates/keymap_editor/src/keymap_editor.rs",
        "muted_styled_text(NO_ACTION_ARGUMENTS_TEXT, cx)",
        "muted_styled_text(no_action_arguments_text(), cx)",
    )

    patch(
        "crates/language_models/src/provider/openai_subscribed.rs",
        '''const SUBSCRIPTION_DESCRIPTION: &str =
    "Sign in with your ChatGPT Plus or Pro subscription to use OpenAI models in Zed's agent.";''',
        '''fn subscription_description() -> &'static str {
    localization::localized_str!(
        "Sign in with your ChatGPT Plus or Pro subscription to use OpenAI models in Zed's agent."
    )
}''',
    )
    patch(
        "crates/language_models/src/provider/openai_subscribed.rs",
        "SUBSCRIPTION_DESCRIPTION.into()",
        "subscription_description().into()",
    )
    patch(
        "crates/language_models/src/provider/openai_subscribed.rs",
        "Label::new(SUBSCRIPTION_DESCRIPTION)",
        "Label::new(subscription_description())",
    )
    dependency("crates/language_models/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/multi_buffer/src/multi_buffer.rs",
        "        Self::DEFAULT_TITLE.into()",
        "        localization::localized_str!(\"untitled\").into()",
    )
    dependency("crates/multi_buffer/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/onboarding/src/basics_page.rs",
        '''                        const MODE_NAMES: [SharedString; 3] = [
                            SharedString::new_static("Light"),
                            SharedString::new_static("Dark"),
                            SharedString::new_static("System"),
                        ];''',
        '''                        let mode_names: [SharedString; 3] = [
                            localization::localized_str!("Light").into(),
                            localization::localized_str!("Dark").into(),
                            localization::localized_str!("System").into(),
                        ];''',
    )
    patch(
        "crates/onboarding/src/basics_page.rs",
        "MODE_NAMES[mode as usize].clone()",
        "mode_names[mode as usize].clone()",
    )
    dependency("crates/onboarding/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/search/src/search.rs",
        '''const REPLACE_PLACEHOLDER: &str = "Replace in project…";
const INCLUDE_PLACEHOLDER: &str = "Include: e.g. src/**/*.rs";
const EXCLUDE_PLACEHOLDER: &str = "Exclude: e.g. vendor/*, *.lock";''',
        '''fn replace_placeholder() -> &'static str {
    localization::localized_str!("Replace in project…")
}

fn include_placeholder() -> &'static str {
    localization::localized_str!("Include: e.g. src/**/*.rs")
}

fn exclude_placeholder() -> &'static str {
    localization::localized_str!("Exclude: e.g. vendor/*, *.lock")
}''',
    )
    patch(
        "crates/search/src/project_search.rs",
        '''    BufferSearchBar, EXCLUDE_PLACEHOLDER, FocusSearch, HighlightKey, INCLUDE_PLACEHOLDER,
    NextHistoryQuery, PreviousHistoryQuery, REPLACE_PLACEHOLDER, ReplaceAll, ReplaceNext,''',
        '''    BufferSearchBar, FocusSearch, HighlightKey, NextHistoryQuery, PreviousHistoryQuery,
    ReplaceAll, ReplaceNext, exclude_placeholder, include_placeholder, replace_placeholder,''',
    )
    for old, new in (
        (
            "editor.set_placeholder_text(REPLACE_PLACEHOLDER, window, cx);",
            "editor.set_placeholder_text(replace_placeholder(), window, cx);",
        ),
        (
            "editor.set_placeholder_text(INCLUDE_PLACEHOLDER, window, cx);",
            "editor.set_placeholder_text(include_placeholder(), window, cx);",
        ),
        (
            "editor.set_placeholder_text(EXCLUDE_PLACEHOLDER, window, cx);",
            "editor.set_placeholder_text(exclude_placeholder(), window, cx);",
        ),
    ):
        patch("crates/search/src/project_search.rs", old, new)
    dependency("crates/search/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/settings/src/base_keymap_setting.rs",
        '''        Self::OPTIONS.iter().map(|(name, _)| *name)''',
        '''        Self::OPTIONS
            .iter()
            .map(|(name, _)| localization::translate_static(name))''',
    )
    patch(
        "crates/settings/src/base_keymap_setting.rs",
        '''            .find_map(|(name, value)| (name == option).then_some(value))''',
        '''            .find_map(|(name, value)| {
                (name == option || localization::translate_static(name) == option).then_some(value)
            })''',
    )
    dependency("crates/settings/Cargo.toml", "anyhow", "localization")

    patch(
        "crates/settings_ui/src/pages/sandbox_settings.rs",
        '''const DOMAINS_DESCRIPTION: &str = "Each entry is an exact domain (github.com) or a leading-*. subdomain wildcard (*.npmjs.org). IP addresses and local domains are not allowed.";

const WRITE_PATHS_DESCRIPTION: &str = "Each entry must be an absolute path and grants write access to the whole subtree, except protected Git metadata.";
''',
        "// Sandbox descriptions are localized at their runtime use sites.\n",
    )
    patch(
        "crates/settings_ui/src/pages/sandbox_settings.rs",
        "                    DOMAINS_DESCRIPTION,",
        '''                    localization::localized_str!("Each entry is an exact domain (github.com) or a leading-*. subdomain wildcard (*.npmjs.org). IP addresses and local domains are not allowed."),''',
    )
    patch(
        "crates/settings_ui/src/pages/sandbox_settings.rs",
        "                    WRITE_PATHS_DESCRIPTION,",
        '''                    localization::localized_str!("Each entry must be an absolute path and grants write access to the whole subtree, except protected Git metadata."),''',
    )
    tool_path = "crates/settings_ui/src/pages/tool_permissions_setup.rs"
    patch(
        tool_path,
        '''const HARDCODED_RULES_DESCRIPTION: &str =
    "`rm -rf` commands are always blocked when run on `$HOME`, `~`, `.`, `..`, or `/`";
const SETTINGS_DISCLAIMER: &str = "Note: custom tool permissions only apply to the Zed native agent and don’t extend to external agents connected through the Agent Client Protocol (ACP).";
''',
        "// Tool permission descriptions are localized at their runtime use sites.\n",
    )
    patch(
        tool_path,
        "Label::new(SETTINGS_DISCLAIMER)",
        "Label::new(localization::localized_str!(\"Note: custom tool permissions only apply to the Zed native agent and don’t extend to external agents connected through the Agent Client Protocol (ACP).\"))",
    )
    patch(
        tool_path,
        "Label::new(tool.name)",
        "Label::new(localization::translate_static(tool.name))",
    )
    patch(
        tool_path,
        "Label::new(tool.description)",
        "Label::new(localization::translate_static(tool.description))",
    )
    patch(
        tool_path,
        "let tool_name = tool.name;",
        "let tool_name = localization::translate_static(tool.name);",
    )
    patch(
        tool_path,
        "Label::new(tool.regex_explanation)",
        "Label::new(localization::translate_static(tool.regex_explanation))",
    )
    patch(
        tool_path,
        ".child(render_inline_code_markdown(HARDCODED_RULES_DESCRIPTION, cx))",
        '''.child(render_inline_code_markdown(
            localization::localized_str!("`rm -rf` commands are always blocked when run on `$HOME`, `~`, `.`, `..`, or `/`"),
            cx,
        ))''',
    )

    patch(
        "crates/workspace/src/pane.rs",
        '''        const CONFLICT_MESSAGE: &str = "This file has changed on disk since you started editing it. Do you want to overwrite it?";

        const DELETED_MESSAGE: &str = "This file has been deleted on disk since you started editing it. Do you want to recreate it?";''',
        '''        let conflict_message = localization::localized_str!("This file has changed on disk since you started editing it. Do you want to overwrite it?");

        let deleted_message = localization::localized_str!("This file has been deleted on disk since you started editing it. Do you want to recreate it?");''',
    )
    patch(
        "crates/workspace/src/pane.rs",
        "                        DELETED_MESSAGE,",
        "                        deleted_message,",
    )
    patch(
        "crates/workspace/src/pane.rs",
        "                        CONFLICT_MESSAGE,",
        "                        conflict_message,",
    )
    patch(
        "crates/workspace/src/welcome.rs",
        "                self.title,",
        "                localization::translate_static(self.title),",
    )
    patch(
        "crates/workspace/src/welcome.rs",
        ".child(SectionHeader::new(self.title))",
        ".child(SectionHeader::new(localization::translate_static(self.title)))",
    )
    dependency("crates/workspace/Cargo.toml", "anyhow", "localization")


def _register_thiserror_patches(patch, dependency) -> None:
    path = "crates/language_model/src/registry.rs"
    patch(
        path,
        '#[error("Configure at least one LLM provider to start using the panel.")]',
        '#[error("{}", localization::localized_str!("Configure at least one LLM provider to start using the panel."))]',
    )
    patch(
        path,
        '#[error("LLM provider is not configured or does not support the configured model.")]',
        '#[error("{}", localization::localized_str!("LLM provider is not configured or does not support the configured model."))]',
    )
    patch(
        path,
        '#[error("{} LLM provider is not configured.", .0.name().0)]',
        '''#[error(
        "{}",
        localization::format_message(
            "{} LLM provider is not configured.",
            &[("0", format!("{}", .0.name().0))],
        )
    )]''',
    )
    dependency("crates/language_model/Cargo.toml", "anyhow", "localization")


# Every accepted occurrence classified as rewrite_const_context or
# rewrite_thiserror must be handled by a hand-written patch in
# _register_const_context_patches or _register_thiserror_patches. This
# allowlist makes that pairing explicit so a version bump that introduces a
# new const/static or #[error] string fails the apply loudly instead of
# silently shipping English at runtime. Update it together with the patches.
_EXPECTED_MANUAL_SITES: frozenset[tuple[str, str]] = frozenset({
    ("crates/agent_ui/src/agent_configuration/configure_context_server_modal.rs", "Check the server docs for required arguments and environment variables."),
    ("crates/copilot_ui/src/sign_in.rs", "Copilot Edit Predictions had issues starting. You can try reinstalling it and signing in again."),
    ("crates/debugger_tools/src/dap_log.rs", "Adapter Logs"),
    ("crates/debugger_tools/src/dap_log.rs", "Initialization Sequence"),
    ("crates/debugger_tools/src/dap_log.rs", "RPC Messages"),
    ("crates/debugger_ui/src/new_process_modal.rs", "Select Debugger"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "1 byte"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "16 bytes"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "2 bytes"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "32 bytes"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "4 bytes"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "64 bytes"),
    ("crates/debugger_ui/src/session/running/memory_view.rs", "8 bytes"),
    ("crates/editor/src/code_lens.rs", "0 references"),
    ("crates/editor/src/editor.rs", "right-click for more options"),
    ("crates/git_ui/src/remote_output.rs", "Create Merge Request"),
    ("crates/git_ui/src/remote_output.rs", "Create Pull Request"),
    ("crates/git_ui/src/remote_output.rs", "View Merge Request"),
    ("crates/keymap_editor/src/keymap_editor.rs", "<global>"),
    ("crates/keymap_editor/src/keymap_editor.rs", "<no arguments>"),
    ("crates/keymap_editor/src/keymap_editor.rs", "<null>"),
    ("crates/language_model/src/registry.rs", "Configure at least one LLM provider to start using the panel."),
    ("crates/language_model/src/registry.rs", "LLM provider is not configured or does not support the configured model."),
    ("crates/language_model/src/registry.rs", "{} LLM provider is not configured."),
    ("crates/language_models/src/provider/openai_subscribed.rs", "Sign in with your ChatGPT Plus or Pro subscription to use OpenAI models in Zed's agent."),
    ("crates/multi_buffer/src/multi_buffer.rs", "untitled"),
    ("crates/onboarding/src/basics_page.rs", "Dark"),
    ("crates/onboarding/src/basics_page.rs", "Light"),
    ("crates/onboarding/src/basics_page.rs", "System"),
    ("crates/search/src/search.rs", "Exclude: e.g. vendor/*, *.lock"),
    ("crates/search/src/search.rs", "Include: e.g. src/**/*.rs"),
    ("crates/search/src/search.rs", "Replace in project…"),
    ("crates/settings/src/base_keymap_setting.rs", "Zed (Default)"),
    ("crates/settings_ui/src/pages/sandbox_settings.rs", "Each entry is an exact domain (github.com) or a leading-*. subdomain wildcard (*.npmjs.org). IP addresses and local domains are not allowed."),
    ("crates/settings_ui/src/pages/sandbox_settings.rs", "Each entry must be an absolute path and grants write access to the whole subtree, except protected Git metadata."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Commands executed in the terminal"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Copy Path"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Create Directory"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Delete Path"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Directory creation"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Edit File"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Fetch"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "File and directory copying"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "File and directory deletion"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "File and directory moves/renames"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "File creation and overwrite operations"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "File editing operations"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "HTTP requests to URLs"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Loading agent skill instructions"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Move Path"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Note: custom tool permissions only apply to the Zed native agent and don’t extend to external agents connected through the Agent Client Protocol (ACP)."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against each command in the input. Commands chained with &&, ||, ;, or pipes are split and checked individually."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the URL being fetched."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the absolute path to the skill's SKILL.md file."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the directory path being created."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the file path being edited."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the file path being written."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the path being deleted."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched against the search query."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Patterns are matched independently against the source path and the destination path. Enter either path below to test."),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Skill"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Terminal"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Web Search"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Web search queries"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "Write File"),
    ("crates/settings_ui/src/pages/tool_permissions_setup.rs", "`rm -rf` commands are always blocked when run on `$HOME`, `~`, `.`, `..`, or `/`"),
    ("crates/workspace/src/pane.rs", "This file has been deleted on disk since you started editing it. Do you want to recreate it?"),
    ("crates/workspace/src/pane.rs", "This file has changed on disk since you started editing it. Do you want to overwrite it?"),
    ("crates/workspace/src/welcome.rs", "Clone Repository"),
    ("crates/workspace/src/welcome.rs", "Configure"),
    ("crates/workspace/src/welcome.rs", "Customize Keymaps"),
    ("crates/workspace/src/welcome.rs", "Explore Extensions"),
    ("crates/workspace/src/welcome.rs", "Get Started"),
    ("crates/workspace/src/welcome.rs", "New File"),
    ("crates/workspace/src/welcome.rs", "Open Command Palette"),
    ("crates/workspace/src/welcome.rs", "Open Project"),
    ("crates/workspace/src/welcome.rs", "Open Settings"),
})


# Pairs above with more than one manifest occurrence; every unlisted pair is
# expected exactly once. A second occurrence of an already-patched string would
# otherwise ship untranslated without tripping the pair-level check.
_EXPECTED_MANUAL_SITE_COUNTS: Mapping[tuple[str, str], int] = {
    ("crates/git_ui/src/remote_output.rs", "Create Pull Request"): 2,
    ("crates/settings/src/base_keymap_setting.rs", "Zed (Default)"): 2,
    (
        "crates/settings_ui/src/pages/tool_permissions_setup.rs",
        "Patterns are matched independently against the source path and the destination path. Enter either path below to test.",
    ): 2,
}


def _verify_manual_rewrite_sites(handling: HandlingMapReport) -> None:
    actual = Counter(
        (entry.file, entry.source)
        for entry in handling.entries
        if entry.handling_class in {"rewrite_const_context", "rewrite_thiserror"}
    )
    expected = {
        site: _EXPECTED_MANUAL_SITE_COUNTS.get(site, 1)
        for site in _EXPECTED_MANUAL_SITES
    }
    problems: list[str] = []
    grown = sorted(
        site for site, count in actual.items() if count > expected.get(site, 0)
    )
    if grown:
        details = [
            (site, f"{actual[site]} occurrences, {expected.get(site, 0)} patched")
            for site in grown[:3]
        ]
        problems.append(f"unpatched manual rewrite sites: {details!r}")
    shrunk = sorted(
        site for site, count in expected.items() if actual.get(site, 0) < count
    )
    if shrunk:
        details = [
            (site, f"{actual.get(site, 0)} occurrences, {expected[site]} patched")
            for site in shrunk[:3]
        ]
        problems.append(f"expected manual rewrite sites disappeared: {details!r}")
    if problems:
        raise ValueError(
            "const/static and thiserror occurrences no longer match the "
            "hand-written runtime patches; update _register_const_context_patches, "
            "_register_thiserror_patches, _EXPECTED_MANUAL_SITES, and "
            "_EXPECTED_MANUAL_SITE_COUNTS together: " + "; ".join(problems)
        )


def _apply_post_rewrite_adapters(zed_root: Path) -> None:
    planned: dict[Path, str] = {}
    _plan_post_rewrite_adapters(zed_root, planned)
    _write_planned_files(zed_root, planned)


def _plan_post_rewrite_adapters(zed_root: Path, planned: dict[Path, str]) -> None:
    path = zed_root / "crates/settings_ui/src/pages/tool_permissions_setup.rs"
    text = planned.get(path)
    if text is None:
        if not path.exists():
            raise ValueError(f"post-rewrite adapter target does not exist: {path}")
        text = path.read_text(encoding="utf-8")
    translated = (
        'let __zed_i18n_arg_0 = format!("{}", '
        "localization::translate_static(tool.name));"
    )
    if translated not in text:
        originals = (
            'let __zed_i18n_arg_0 = format!("{}", tool.name);',
            "let __zed_i18n_arg_0 = &(tool.name);",
        )
        matches = [original for original in originals if original in text]
        if len(matches) == 1 and text.count(matches[0]) == 1:
            planned[path] = text.replace(matches[0], translated, 1)
        elif matches or 'let page_title = format!("{} Tool", tool.name);' not in text:
            raise ValueError(
                "post-rewrite adapter anchor count for tool permission page title "
                f"is {len(matches)}, expected 1"
            )

    rust_paths = set((zed_root / "crates").glob("*/src/**/*.rs"))
    rust_paths.update(
        planned_path
        for planned_path in planned
        if planned_path.suffix == ".rs"
        and _is_crate_source_path(zed_root, planned_path)
    )
    for rust_path in sorted(rust_paths):
        source = planned.get(rust_path)
        if source is None:
            source = rust_path.read_text(encoding="utf-8")
        rewritten = _rewrite_nested_format_literals(source)
        rewritten = _rewrite_nested_indoc_literals(rewritten)
        rewritten = _rewrite_implicit_format_macros(rewritten)
        if rewritten != source:
            planned[rust_path] = rewritten


def _is_crate_source_path(zed_root: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(zed_root).parts
    except ValueError:
        return False
    return len(parts) > 3 and parts[0] == "crates" and parts[2] == "src"


def _rewrite_nested_format_literals(source: str) -> str:
    replacements: list[tuple[int, int, str]] = []
    pattern = re.compile(
        r'^format!\(\s*localization::localized_str!\(("(?:\\.|[^"\\])*")\)',
        re.S,
    )
    parser = make_rust_parser()
    for start, end in _rust_macro_call_spans(source, "format"):
        call = source[start:end]
        match = pattern.match(call)
        if match is None:
            continue
        literal = match.group(1)
        wrapper_start, wrapper_end = match.span(0)
        localized_start = call.index("localization::localized_str!", wrapper_start)
        localized_end = wrapper_end
        clean_call = call[:localized_start] + literal + call[localized_end:]
        fixture = f"fn __zed_i18n_fixture() {{ let _ = {clean_call}; }}"
        fixture_bytes = fixture.encode("utf-8")
        tree = parser.parse(fixture_bytes)
        macro = next(
            (
                node
                for node in walk_nodes(tree.root_node)
                if node.type == "macro_invocation"
                and node_text(fixture_bytes, node).lstrip().startswith("format!")
            ),
            None,
        )
        if macro is None:
            raise ValueError("nested format adapter could not parse generated fixture")
        replacements.append(
            (
                start,
                end,
                _rewrite_format_macro(
                    fixture_bytes,
                    macro,
                    parse_rust_string_literal(
                        re.sub(r"\\\r?\n[ \t]*", "", literal)
                    ),
                ),
            )
        )
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source


def _rewrite_nested_indoc_literals(source: str) -> str:
    replacements: list[tuple[int, int, str]] = []
    pattern = re.compile(
        r'^indoc!\s*[\{\(]\s*localization::localized_str!\(("(?:\\.|[^"\\])*")\)\s*[\}\)]$',
        re.S,
    )
    for start, end in _rust_macro_call_spans(source, "indoc"):
        call = source[start:end]
        match = pattern.match(call)
        if match is None:
            continue
        literal = match.group(1)
        replacements.append(
            (start, end, f"localization::translate_static(indoc!{{{literal}}})")
        )
    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    return source


def _rewrite_implicit_format_macros(source: str) -> str:
    parser = make_rust_parser()
    for macro_name, source_index in _IMPLICIT_FORMAT_MACROS:
        replacements: list[tuple[int, int, str]] = []
        for start, end in _rust_macro_call_spans(source, macro_name):
            call = source[start:end]
            fixture = f"fn __zed_i18n_fixture() {{ let _ = {call}; }}"
            fixture_bytes = fixture.encode("utf-8")
            tree = parser.parse(fixture_bytes)
            macro = next(
                (
                    node
                    for node in walk_nodes(tree.root_node)
                    if node.type == "macro_invocation"
                    and node_text(fixture_bytes, node).lstrip().startswith(
                        f"{macro_name}!"
                    )
                ),
                None,
            )
            if macro is None:
                continue
            token_tree = next(
                (child for child in macro.children if child.type == "token_tree"),
                None,
            )
            if token_tree is None:
                continue
            arguments = _token_tree_arguments(fixture_bytes, token_tree)
            if source_index >= len(arguments):
                continue
            localized = _localized_string_argument(arguments[source_index])
            if localized is None:
                continue
            literal, format_source = localized
            if not _format_placeholders(format_source):
                continue

            format_arguments = arguments[source_index + 1 :]
            clean_format = f"format!({literal}"
            if format_arguments:
                clean_format += ", " + ", ".join(format_arguments)
            clean_format += ")"
            format_fixture = (
                f"fn __zed_i18n_format_fixture() {{ let _ = {clean_format}; }}"
            )
            format_bytes = format_fixture.encode("utf-8")
            format_tree = parser.parse(format_bytes)
            format_macro = next(
                (
                    node
                    for node in walk_nodes(format_tree.root_node)
                    if node.type == "macro_invocation"
                    and node_text(format_bytes, node).lstrip().startswith("format!")
                ),
                None,
            )
            if format_macro is None:
                raise ValueError(
                    f"implicit format adapter could not parse {macro_name}! source"
                )
            message = _rewrite_format_macro(format_bytes, format_macro, format_source)
            retained = arguments[:source_index]
            replacement_arguments = [*retained, '"{}"', message]
            replacements.append(
                (start, end, f"{macro_name}!({', '.join(replacement_arguments)})")
            )
        for start, end, replacement in reversed(replacements):
            source = source[:start] + replacement + source[end:]
    return source


def _localized_string_argument(argument: str) -> tuple[str, str] | None:
    spans = _rust_macro_call_spans(argument, "localization::localized_str")
    if len(spans) != 1:
        return None
    start, end = spans[0]
    if argument[:start].strip() or argument[end:].strip():
        return None
    call = argument[start:end]
    parser = make_rust_parser()
    fixture = f"fn __zed_i18n_fixture() {{ let _ = {call}; }}"
    fixture_bytes = fixture.encode("utf-8")
    tree = parser.parse(fixture_bytes)
    literals = [
        node
        for node in walk_nodes(tree.root_node)
        if node.type in {"string_literal", "raw_string_literal"}
    ]
    if len(literals) != 1:
        return None
    literal = node_text(fixture_bytes, literals[0])
    normalized = re.sub(r"\\\r?\n[ \t]*", "", literal)
    return literal, parse_rust_string_literal(normalized)


def _rust_macro_call_spans(source: str, name: str) -> list[tuple[int, int]]:
    token = f"{name}!"
    spans: list[tuple[int, int]] = []
    cursor = 0
    while True:
        start = source.find(token, cursor)
        if start < 0:
            break
        if start > 0 and (source[start - 1].isalnum() or source[start - 1] in "_:"):
            cursor = start + len(token)
            continue
        open_index = start + len(token)
        while open_index < len(source) and source[open_index].isspace():
            open_index += 1
        if open_index >= len(source) or source[open_index] not in "([{":
            cursor = start + len(token)
            continue
        end = _matching_rust_delimiter(source, open_index)
        if end is None:
            cursor = start + len(token)
            continue
        spans.append((start, end + 1))
        cursor = end + 1
    return spans


def _matching_rust_delimiter(source: str, open_index: int) -> int | None:
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [pairs[source[open_index]]]
    index = open_index + 1
    while index < len(source):
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            depth = 1
            index += 2
            while index < len(source) and depth:
                if source.startswith("/*", index):
                    depth += 1
                    index += 2
                elif source.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            continue
        raw = re.match(r'(?:b)?r(#+)?"', source[index:])
        if raw is not None:
            hashes = raw.group(1) or ""
            close = '"' + hashes
            close_index = source.find(close, index + raw.end())
            if close_index < 0:
                return None
            index = close_index + len(close)
            continue
        if source[index] == '"':
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            continue
        char = source[index]
        if char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
            if not stack:
                return index
        index += 1
    return None


def apply_universal(
    root: Path,
    zed_root: Path,
    manifest: Mapping[str, object],
) -> UniversalApplyReport:
    manifest_sha256 = hashlib.sha256(_canonical_json_bytes(manifest)).hexdigest()
    install_runtime_patches = (
        root / "tools" / "zed_i18n" / "runtime_overlay"
    ).exists()
    if install_runtime_patches and not (
        zed_root / "assets" / "locales" / "index.json"
    ).exists():
        raise ValueError(
            "runtime locale bundles are missing from the checkout; run "
            "`zed-i18n generate-runtime-bundles` before `apply-universal`"
        )
    marker_path = zed_root / ".zed-i18n-universal.json"
    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if marker.get("manifest_sha256") != manifest_sha256:
            raise ValueError("universal localization was applied with a different manifest")
        if install_runtime_patches:
            apply_zed_runtime_patches(root, zed_root)
            _apply_post_rewrite_adapters(zed_root)
        return UniversalApplyReport(
            ok=True,
            already_applied=True,
            applied_occurrences=0,
            dependency_crates=tuple(marker.get("dependency_crates", [])),
            manifest_sha256=manifest_sha256,
        )

    handling = build_handling_map(zed_root, manifest)
    if install_runtime_patches:
        _verify_manual_rewrite_sites(handling)

    entries_by_file: dict[str, list[HandlingEntry]] = defaultdict(list)
    for entry in handling.entries:
        if entry.handling_class in {"rewrite_static", "rewrite_format"}:
            entries_by_file[entry.file].append(entry)

    planned_files: dict[Path, str] = {}
    dependency_crates: set[str] = set()
    applied_occurrences = 0
    parser = make_rust_parser()
    for relative, entries in entries_by_file.items():
        path = zed_root / relative
        text = path.read_text(encoding="utf-8")
        source_bytes = text.encode("utf-8")
        tree = parser.parse(source_bytes)
        nodes = {(node.start_byte, node.end_byte): node for node in walk_nodes(tree.root_node)}
        replacements: list[_Replacement] = []
        format_macros: dict[tuple[int, int], tuple[object, str]] = {}
        for entry in entries:
            node = nodes.get((entry.start_byte, entry.end_byte))
            if node is None:
                raise ValueError(f"stale occurrence span: {entry.file}:{entry.line}")
            if entry.handling_class == "rewrite_static":
                literal = node_text(source_bytes, node)
                replacements.append(
                    _Replacement(
                        start=entry.start_byte,
                        end=entry.end_byte,
                        text=f"localization::localized_str!({literal})",
                    )
                )
            elif entry.handling_class == "rewrite_format":
                macro = _format_macro_ancestor(node, source_bytes)
                if macro is None:
                    raise ValueError(f"format ancestor disappeared: {entry.file}:{entry.line}")
                span = (macro.start_byte, macro.end_byte)
                format_source = _format_macro_source(source_bytes, macro)
                existing = format_macros.get(span)
                if existing is not None and existing[1] != format_source:
                    raise ValueError(
                        f"accepted occurrences disagree on one format macro: {entry.file}:{entry.line}"
                    )
                format_macros[span] = (macro, format_source)
            applied_occurrences += 1

        for macro, format_source in sorted(
            format_macros.values(),
            key=lambda item: item[0].end_byte - item[0].start_byte,
        ):
            contained = [
                replacement
                for replacement in replacements
                if macro.start_byte <= replacement.start
                and replacement.end <= macro.end_byte
            ]
            replacements = [
                replacement for replacement in replacements if replacement not in contained
            ]
            replacements.append(
                _Replacement(
                    start=macro.start_byte,
                    end=macro.end_byte,
                    text=_rewrite_format_macro(
                        source_bytes,
                        macro,
                        format_source,
                        contained,
                    ),
                )
            )

        _validate_replacement_spans(replacements, relative)
        rewritten = source_bytes
        for replacement in sorted(replacements, key=lambda item: item.start, reverse=True):
            rewritten = (
                rewritten[: replacement.start]
                + replacement.text.encode("utf-8")
                + rewritten[replacement.end :]
            )
        planned_files[path] = rewritten.decode("utf-8")
        crate = _owning_crate(relative)
        dependency_crates.add(crate)

    for crate in sorted(dependency_crates):
        cargo_path = zed_root / "crates" / crate / "Cargo.toml"
        if not cargo_path.exists():
            raise ValueError(f"owning crate Cargo.toml does not exist: {crate}")
        cargo_text = cargo_path.read_text(encoding="utf-8")
        planned_files[cargo_path] = _add_localization_dependency(cargo_text, cargo_path)

    # Plan the structural patches and post-rewrite adapters on top of the
    # in-memory rewrites so an anchor failure aborts before the first write
    # instead of stranding a half-modified checkout with stale manifest spans.
    if install_runtime_patches:
        _plan_zed_runtime_patches(root, zed_root, planned_files)
        _plan_post_rewrite_adapters(zed_root, planned_files)

    _write_planned_files(zed_root, planned_files)
    dependency_crates = {
        cargo.parent.name
        for cargo in (zed_root / "crates").glob("*/Cargo.toml")
        if re.search(
            r"(?m)^localization(?:\.[A-Za-z0-9_-]+)?\s*=",
            cargo.read_text(encoding="utf-8"),
        )
    }

    marker = {
        "schema_version": 1,
        "manifest_sha256": manifest_sha256,
        "dependency_crates": sorted(dependency_crates),
        "applied_occurrences": len(handling.entries),
    }
    marker_path.write_bytes(_canonical_json_bytes(marker))
    report = UniversalApplyReport(
        ok=True,
        already_applied=False,
        applied_occurrences=len(handling.entries),
        dependency_crates=tuple(sorted(dependency_crates)),
        manifest_sha256=manifest_sha256,
    )
    report_dir = root / "reports" / "runtime-feasibility"
    _write_json(report_dir / "kind-handling-map.json", _handling_report_json(handling))
    _write_json(
        report_dir / "dependency-map.json",
        {"crate_count": len(dependency_crates), "crates": sorted(dependency_crates)},
    )
    _write_json(report_dir / "rewrite-compile-report.json", asdict(report))
    return report


def _classify_occurrence(kind: str, node, source_bytes: bytes) -> str:
    if kind in _SCHEMA_METADATA_KINDS:
        return "schema_metadata"
    if kind in _ACTION_METADATA_KINDS:
        return "action_metadata"
    if kind in _SETTINGS_ENUM_KINDS:
        return "settings_enum"
    if node is None:
        return "not_runtime_visible"

    parent = node.parent
    while parent is not None:
        if parent.type == "macro_invocation":
            macro_name = node_text(source_bytes, parent).split("!", 1)[0].strip()
            if macro_name in {"format", "format_args", "write"}:
                if _is_format_source_argument(node, parent, macro_name):
                    return "rewrite_format"
                return "rewrite_static"
            if macro_name == "w":
                return "rewrite_const_context"
        if parent.type in {"const_item", "static_item"}:
            return "rewrite_const_context"
        if parent.type == "attribute_item" and node_text(source_bytes, parent).lstrip().startswith(
            "#[error"
        ):
            return "rewrite_thiserror"
        parent = parent.parent
    return "rewrite_static"


def _is_format_source_argument(node, macro, macro_name: str) -> bool:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    if token_tree is None:
        return False
    commas = [child.start_byte for child in token_tree.children if child.type == ","]
    argument_index = 1 if macro_name == "write" else 0
    start = token_tree.start_byte + 1 if argument_index == 0 else commas[argument_index - 1] + 1
    end = commas[argument_index] if len(commas) > argument_index else token_tree.end_byte - 1
    return start <= node.start_byte and node.end_byte <= end


def _format_macro_ancestor(node, source_bytes: bytes):
    parent = node.parent
    while parent is not None:
        if parent.type == "macro_invocation":
            macro_name = node_text(source_bytes, parent).split("!", 1)[0].strip()
            if macro_name in {"format", "format_args", "write"}:
                return parent
        parent = parent.parent
    return None


def _format_macro_source(source_bytes: bytes, macro) -> str:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    if token_tree is None:
        raise ValueError("format macro has no token tree")
    macro_name = node_text(source_bytes, macro).split("!", 1)[0].strip()
    commas = [child.start_byte for child in token_tree.children if child.type == ","]
    argument_index = 1 if macro_name == "write" else 0
    source_start = (
        token_tree.start_byte + 1
        if argument_index == 0
        else commas[argument_index - 1] + 1
    )
    source_end = (
        commas[argument_index]
        if len(commas) > argument_index
        else token_tree.end_byte - 1
    )
    literals = [
        node
        for node in walk_nodes(token_tree)
        if node.type == "string_literal"
        and source_start <= node.start_byte
        and node.end_byte <= source_end
    ]
    if not literals:
        raise ValueError("format source is not a string literal or concat of literals")
    return "".join(
        parse_rust_string_literal(
            re.sub(
                r"\\\r?\n[ \t]*",
                "",
                node_text(source_bytes, literal),
            )
        )
        for literal in literals
    )


def _rewrite_format_macro(
    source_bytes: bytes,
    macro,
    source: str,
    inner_replacements: list[_Replacement] | None = None,
) -> str:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    if token_tree is None:
        raise ValueError(f"format macro has no token tree: {source!r}")
    arguments = _token_tree_arguments(source_bytes, token_tree, inner_replacements or [])
    if not arguments:
        raise ValueError(f"format macro has no source literal: {source!r}")
    macro_name = node_text(source_bytes, macro).split("!", 1)[0].strip()
    destination = arguments.pop(0) if macro_name == "write" else None
    first = arguments[0].strip()
    if not (first.startswith('"') or first.startswith("concat!")):
        raise ValueError(f"format source is not a regular string literal or concat: {source!r}")

    raw_arguments = arguments[1:]
    parsed_arguments: list[tuple[str | None, str]] = []
    positional: list[int] = []
    named: dict[str, int] = {}
    for argument in raw_arguments:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?!=)(.+)$", argument, re.S)
        if match is None:
            positional.append(len(parsed_arguments))
            parsed_arguments.append((None, argument.strip()))
        else:
            name = match.group(1)
            if name in named:
                raise ValueError(f"duplicate named format argument {name!r}: {source!r}")
            named[name] = len(parsed_arguments)
            parsed_arguments.append((name, match.group(2).strip()))

    placeholders = _format_placeholders(source)
    implicit_index = 0
    key_to_argument: dict[str, int | str] = {}
    key_specs: dict[str, str] = {}
    capture_order: list[str] = []
    for placeholder in placeholders:
        key = placeholder.key
        if key == "":
            key = str(implicit_index)
            implicit_index += 1
        if key.isdecimal():
            argument_index = int(key)
            if argument_index >= len(positional):
                raise ValueError(f"format argument {key} is out of range: {source!r}")
            target: int | str = positional[argument_index]
        elif key in named:
            target = named[key]
        else:
            target = key
            if key not in capture_order:
                capture_order.append(key)
        previous_spec = key_specs.get(key)
        if previous_spec is not None and previous_spec != placeholder.format_spec:
            raise ValueError(f"one format argument uses multiple format specs: {source!r}")
        key_specs[key] = placeholder.format_spec
        key_to_argument[key] = target

    binding_names: dict[int | str, str] = {}
    bindings: list[str] = []
    for argument_index, (_, expression) in enumerate(parsed_arguments):
        binding = f"__zed_i18n_arg_{len(bindings)}"
        binding_names[argument_index] = binding
        specs = {
            key_specs[key]
            for key, target in key_to_argument.items()
            if target == argument_index
        }
        if len(specs) != 1:
            raise ValueError(f"format argument has ambiguous formatting: {source!r}")
        format_literal = rust_string_literal("{" + next(iter(specs)) + "}")
        bindings.append(f"let {binding} = format!({format_literal}, {expression});")
    for capture in capture_order:
        binding = f"__zed_i18n_arg_{len(bindings)}"
        binding_names[capture] = binding
        format_literal = rust_string_literal("{" + key_specs[capture] + "}")
        bindings.append(f"let {binding} = format!({format_literal}, {capture});")

    rendered_arguments: list[str] = []
    emitted: set[str] = set()
    implicit_index = 0
    for placeholder in placeholders:
        key = placeholder.key
        if key == "":
            key = str(implicit_index)
            implicit_index += 1
        if key in emitted:
            continue
        emitted.add(key)
        target = key_to_argument[key]
        binding = binding_names[target]
        rendered_arguments.append(
            f"({rust_string_literal(key)}, format!(\"{{}}\", {binding}))"
        )

    binding_block = "\n        ".join(bindings)
    arguments_block = ",\n                ".join(rendered_arguments)
    if bindings:
        binding_block += "\n        "
    expression = (
        "{\n"
        f"        {binding_block}localization::format_message(\n"
        f"            {rust_string_literal(source)},\n"
        "            &[\n"
        f"                {arguments_block}\n"
        "            ],\n"
        "        )\n"
        "    }"
    )
    if destination is not None:
        return f'write!({destination}, "{{}}", {expression})'
    return expression


def _token_tree_arguments(
    source_bytes: bytes,
    token_tree,
    replacements: list[_Replacement] | None = None,
) -> list[str]:
    comma_positions = [
        child.start_byte for child in token_tree.children if child.type == ","
    ]
    start = token_tree.start_byte + 1
    end = token_tree.end_byte - 1
    boundaries = [start, *comma_positions, end]
    arguments: list[str] = []
    for index in range(len(boundaries) - 1):
        item_start = boundaries[index] + (1 if index > 0 else 0)
        item_end = boundaries[index + 1]
        value_bytes = source_bytes[item_start:item_end]
        for replacement in sorted(
            (
                replacement
                for replacement in replacements or []
                if item_start <= replacement.start and replacement.end <= item_end
            ),
            key=lambda item: item.start,
            reverse=True,
        ):
            relative_start = replacement.start - item_start
            relative_end = replacement.end - item_start
            value_bytes = (
                value_bytes[:relative_start]
                + replacement.text.encode("utf-8")
                + value_bytes[relative_end:]
            )
        value = value_bytes.decode("utf-8").strip()
        if value:
            arguments.append(value)
    return arguments


def _format_placeholders(source: str) -> tuple[_Placeholder, ...]:
    placeholders: list[_Placeholder] = []
    index = 0
    while index < len(source):
        unicode_escape = _RUST_UNICODE_ESCAPE_RE.match(source, index)
        if unicode_escape is not None:
            index = unicode_escape.end()
            continue
        if source.startswith("{{", index) or source.startswith("}}", index):
            index += 2
            continue
        if source[index] == "}":
            raise ValueError(f"unmatched closing brace in format string: {source!r}")
        if source[index] != "{":
            index += 1
            continue
        end = source.find("}", index + 1)
        if end < 0 or "{" in source[index + 1 : end]:
            raise ValueError(f"invalid format placeholder: {source!r}")
        inner = source[index + 1 : end]
        key, separator, spec = inner.partition(":")
        format_spec = f":{spec}" if separator else ""
        if "$" in format_spec or ".*" in format_spec:
            raise ValueError(f"dynamic width or precision is unsupported: {source!r}")
        placeholders.append(_Placeholder(key=key, format_spec=format_spec))
        index = end + 1
    return tuple(placeholders)


def _owning_crate(relative: str) -> str:
    parts = Path(relative).parts
    if len(parts) < 3 or parts[0] != "crates":
        raise ValueError(f"runtime localization occurrence is not owned by a crate: {relative}")
    return parts[1]


def _add_localization_dependency(text: str, path: Path) -> str:
    if re.search(r"(?m)^localization(?:\.[A-Za-z0-9_-]+)?\s*=", text):
        return text
    match = re.search(
        r"(?m)^\[(?:dependencies|target\..*\.dependencies)\]\s*$",
        text,
    )
    if match is None:
        raise ValueError(f"crate has no [dependencies] section: {path}")
    insert = match.end()
    return text[:insert] + "\nlocalization.workspace = true" + text[insert:]


def _overlapping_entries(entries: list[HandlingEntry]) -> list[str]:
    overlaps: list[str] = []
    previous: HandlingEntry | None = None
    for entry in entries:
        if previous is not None and previous.file == entry.file and entry.start_byte < previous.end_byte:
            overlaps.append(f"{entry.file}:{entry.start_byte}-{entry.end_byte}")
        if previous is None or previous.file != entry.file or entry.end_byte > previous.end_byte:
            previous = entry
    return overlaps


def _validate_replacement_spans(replacements: list[_Replacement], relative: str) -> None:
    previous: _Replacement | None = None
    for replacement in sorted(replacements, key=lambda item: (item.start, item.end)):
        if previous is not None and replacement.start < previous.end:
            raise ValueError(f"overlapping generated replacements: {relative}:{replacement.start}")
        previous = replacement


def _handling_report_json(report: HandlingMapReport) -> dict[str, object]:
    return {
        "accepted_occurrences": report.accepted_occurrences,
        "overlay_occurrences": report.overlay_occurrences,
        "kind_count": report.kind_count,
        "class_counts": report.class_counts,
        "duplicates": list(report.duplicates),
        "unclassified": list(report.unclassified),
        "entries": [asdict(entry) for entry in report.entries],
    }


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(value))
