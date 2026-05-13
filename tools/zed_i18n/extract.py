from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from .rust_ast import (
    iter_rust_files as _rust_files,
    make_rust_parser as _rust_parser,
    node_text as _node_text,
    walk_nodes as _walk,
)
from .rust_strings import parse_rust_string_literal


@dataclass(frozen=True)
class StringOccurrence:
    source: str
    file: str
    line: int
    call: str
    kind: str
    start_byte: int
    end_byte: int

    def to_manifest_occurrence(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("source")
        return data


@dataclass(frozen=True)
class LinePattern:
    pattern: re.Pattern[str]
    call: str
    kind: str
    value_group: int
    rust_literal: bool = True


CALL_RULES: dict[str, tuple[int, str, str]] = {
    "MenuItem::action": (0, "menu_item", "MenuItem::action"),
    "MenuItem::os_action": (0, "menu_item", "MenuItem::os_action"),
    "Menu::new": (0, "menu", "Menu::new"),
    "ContextMenuEntry::new": (0, "context_menu_entry", "ContextMenuEntry::new"),
    "ConfiguredApiCard::new": (0, "configured_api_card_label", "ConfiguredApiCard::new"),
    "DropdownMenu::new": (1, "dropdown_label", "DropdownMenu::new"),
    "Label::new": (0, "label", "Label::new"),
    "Headline::new": (0, "headline", "Headline::new"),
    "Button::new": (1, "button", "Button::new"),
    "ButtonLink::new": (0, "button_link", "ButtonLink::new"),
    "CopyButton::new": (1, "button", "CopyButton::new"),
    "InputField::new": (2, "placeholder", "InputField::new"),
    "Tooltip::text": (0, "tooltip", "Tooltip::text"),
    "Tooltip::simple": (0, "tooltip", "Tooltip::simple"),
    "Tooltip::new": (0, "tooltip", "Tooltip::new"),
    "Toast::new": (1, "toast", "Toast::new"),
    "StatusToast::new": (0, "status_toast", "StatusToast::new"),
    "MessageNotification::new": (0, "notification", "MessageNotification::new"),
    "ErrorMessagePrompt::new": (0, "error_prompt", "ErrorMessagePrompt::new"),
    "LoadingLabel::new": (0, "loading_label", "LoadingLabel::new"),
    "input_output_header": (0, "label", "input_output_header"),
    "copilot_toast": (0, "toast", "copilot_toast"),
    "SharedString::from": (0, "shared_string", "SharedString::from"),
    "SharedString::new": (0, "shared_string", "SharedString::new"),
    "SharedString::new_static": (0, "shared_string", "SharedString::new_static"),
    "SectionHeader::new": (0, "section_header", "SectionHeader::new"),
    "SettingsSectionHeader::new": (0, "settings_section_header", "SettingsSectionHeader::new"),
    "SettingsPageItem::SectionHeader": (
        0,
        "settings_section_header",
        "SettingsPageItem::SectionHeader",
    ),
    "ListBulletItem::new": (0, "list_bullet_item", "ListBulletItem::new"),
    "ProfileModalHeader::new": (0, "modal_header", "ProfileModalHeader::new"),
}

STRUCT_FIELD_RULES: dict[tuple[str, str], tuple[str, str]] = {
    ("ActionLink", "title"): ("settings_action_title", "ActionLink.title"),
    ("ActionLink", "description"): ("settings_action_description", "ActionLink.description"),
    ("ActionLink", "button_text"): ("settings_action_button", "ActionLink.button_text"),
    ("SettingsPage", "title"): ("settings_page_title", "SettingsPage.title"),
    ("SubPageLink", "title"): ("settings_subpage_title", "SubPageLink.title"),
    ("SubPageLink", "description"): ("settings_subpage_description", "SubPageLink.description"),
    ("SettingItem", "title"): ("setting_title", "SettingItem.title"),
    ("SettingItem", "description"): ("setting_description", "SettingItem.description"),
    ("SettingsFieldMetadata", "placeholder"): (
        "setting_placeholder",
        "SettingsFieldMetadata.placeholder",
    ),
    ("PathPromptOptions", "prompt"): ("path_prompt", "PathPromptOptions.prompt"),
    ("Content", "message"): ("content_message", "Content.message"),
    ("Content", "tooltip_message"): ("content_tooltip_message", "Content.tooltip_message"),
}

UI_RETURN_METHODS: dict[str, tuple[str, str]] = {
    "icon_tooltip": ("panel_tooltip", "icon_tooltip"),
    "loading_message": ("status_message", "loading_message"),
    "placeholder_text": ("placeholder", "placeholder_text"),
    "no_matches_text": ("empty_state", "no_matches_text"),
    "tab_content_text": ("tab_title", "tab_content_text"),
}

EXCLUDED_PARTS = {
    "tests",
    "fixtures",
    "examples",
}


def should_skip_path(relative_path: str) -> bool:
    normalized = Path(relative_path).as_posix()
    parts = set(normalized.split("/"))
    if parts & EXCLUDED_PARTS:
        return True
    if Path(normalized).name.endswith("_tests.rs"):
        return True
    if normalized.startswith("crates/component_preview/"):
        return True
    if normalized.startswith("crates/ui/src/components/") and "/stories" in normalized:
        return True
    return False


def extract_ui_strings_from_source(source: str, relative_path: str) -> list[StringOccurrence]:
    if should_skip_path(relative_path):
        return []

    source_bytes = source.encode("utf-8")
    parser = _rust_parser()
    tree = parser.parse(source_bytes)
    if tree is None:
        return []

    occurrences: list[StringOccurrence] = []
    for node in _walk(tree.root_node):
        if node.type != "call_expression":
            continue
        function_node = node.child_by_field_name("function")
        arguments_node = node.child_by_field_name("arguments")
        if function_node is None or arguments_node is None:
            continue

        call = _node_text(source_bytes, function_node)
        arguments = list(arguments_node.named_children)
        for argument_index, kind, call_name in _rules_for_call(call):
            if argument_index >= len(arguments):
                continue

            argument_node = arguments[argument_index]
            for literal_node in _visible_literal_nodes(
                source_bytes,
                argument_node,
                allow_unwrap_or=kind == "placeholder",
            ):
                literal = _node_text(source_bytes, literal_node)
                occurrences.append(
                    StringOccurrence(
                        source=parse_rust_string_literal(literal),
                        file=relative_path,
                        line=literal_node.start_point[0] + 1,
                        call=call_name,
                        kind=kind,
                        start_byte=literal_node.start_byte,
                        end_byte=literal_node.end_byte,
                    )
                )

    for node in _walk(tree.root_node):
        if node.type != "field_initializer":
            continue
        occurrence = _extract_struct_field_occurrence(source_bytes, node, relative_path)
        if occurrence is not None:
            occurrences.append(occurrence)

    for node in _walk(tree.root_node):
        if node.type != "function_item":
            continue
        occurrences.extend(_extract_ui_return_method_occurrences(source_bytes, node, relative_path))

    occurrences.extend(_extract_action_doc_comments(source, relative_path))
    occurrences.extend(_extract_line_candidates(source, relative_path))
    return _dedupe_occurrences(occurrences)


def extract_repository(zed_root: Path) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    catalog: dict[str, str] = {}
    manifest: dict[str, dict[str, object]] = {}
    for rust_file in _rust_files(zed_root):
        relative_path = rust_file.relative_to(zed_root).as_posix()
        source = rust_file.read_text(encoding="utf-8")
        for occurrence in extract_ui_strings_from_source(source, relative_path):
            catalog.setdefault(occurrence.source, occurrence.source)
            entry = manifest.setdefault(
                occurrence.source,
                {
                    "status": "needs_review",
                    "occurrences": [],
                },
            )
            entry["occurrences"].append(occurrence.to_manifest_occurrence())
    return catalog, manifest


def _rules_for_call(call: str) -> tuple[tuple[int, str, str], ...]:
    canonical = _canonical_call(call)
    if canonical in CALL_RULES:
        return (CALL_RULES[canonical],)
    if canonical == "Toast::new" or canonical.endswith("::Toast::new"):
        return ((1, "toast", "Toast::new"),)
    if canonical == "Chip::new" or canonical.endswith("::Chip::new"):
        return ((0, "chip", "Chip::new"),)
    if canonical == "ToggleButtonSimple::new" or canonical.endswith("::ToggleButtonSimple::new"):
        return ((0, "toggle_button", "ToggleButtonSimple::new"),)
    if canonical == "ViewWidth::new" or canonical.endswith("::ViewWidth::new"):
        return ((1, "debugger_memory_width", "ViewWidth::new"),)
    if canonical.endswith(".set_placeholder_text") or canonical == "set_placeholder_text":
        return ((0, "placeholder", "set_placeholder_text"),)
    if canonical.endswith(".with_placeholder") or canonical == "with_placeholder":
        return ((0, "placeholder", "with_placeholder"),)
    if canonical.endswith(".tooltip_label") or canonical == "tooltip_label":
        return ((0, "tooltip", "tooltip_label"),)
    if canonical.endswith(".headline") or canonical == "headline":
        return ((0, "headline", "headline"),)
    if canonical.endswith(".header") and _looks_like_context_menu_header_call(canonical):
        return ((0, "context_menu_header", "header"),)
    if canonical.endswith(".button_label") or canonical == "button_label":
        return ((0, "button_label", "button_label"),)
    if canonical.endswith(".with_link_button") or canonical == "with_link_button":
        return ((0, "link_button", "with_link_button"),)
    if canonical.endswith(".primary_message") or canonical == "primary_message":
        return ((0, "notification_message", "primary_message"),)
    if canonical.endswith(".secondary_message") or canonical == "secondary_message":
        return ((0, "notification_message", "secondary_message"),)
    if canonical.endswith(".documentation_aside") or canonical == "documentation_aside":
        return ((1, "documentation_aside", "documentation_aside"),)
    if canonical.endswith(".render_section_title") or canonical == "render_section_title":
        return (
            (0, "section_title", "render_section_title"),
            (1, "section_description", "render_section_title"),
        )
    if canonical.endswith(".render_error_callout") or canonical == "render_error_callout":
        return (
            (0, "callout_title", "render_error_callout"),
            (1, "callout_description", "render_error_callout"),
        )
    if canonical.endswith(".render_metric_row") or canonical == "render_metric_row":
        return (
            (0, "metric_title", "render_metric_row"),
            (1, "metric_description", "render_metric_row"),
        )
    if canonical.endswith(".render_loading") or canonical == "render_loading":
        return ((0, "loading_label", "render_loading"),)
    if canonical.endswith(".render_feature_upsell_banner") or canonical == "render_feature_upsell_banner":
        return ((0, "feature_upsell", "render_feature_upsell_banner"),)
    if canonical.endswith("render_action_button"):
        return ((3, "tooltip", "render_action_button"),)
    if (
        canonical == "show_deferred_toast"
        or canonical.endswith(".show_deferred_toast")
        or canonical.endswith("::show_deferred_toast")
    ):
        return ((1, "toast", "show_deferred_toast"),)
    if canonical == "show_etw_notification":
        return ((1, "notification", "show_etw_notification"),)
    if canonical == "show_etw_notification_with_action":
        return (
            (1, "notification", "show_etw_notification_with_action"),
            (2, "notification_action", "show_etw_notification_with_action"),
        )
    if canonical.endswith(".link") or canonical == "link":
        return ((0, "link", "link"),)
    if canonical.endswith(".link_with_handler") or canonical == "link_with_handler":
        return ((0, "link", "link_with_handler"),)
    if canonical.endswith("Tooltip::with_meta") or canonical.endswith("Tooltip::with_meta_in"):
        return (
            (0, "tooltip", "Tooltip::with_meta"),
            (2, "tooltip_meta", "Tooltip::with_meta"),
        )
    if canonical.endswith("Tooltip::for_action_title") or canonical.endswith(
        "Tooltip::for_action_title_in"
    ):
        return ((0, "tooltip", "Tooltip::for_action_title"),)
    if canonical.endswith("Tooltip::for_action") or canonical.endswith("Tooltip::for_action_in"):
        return ((0, "tooltip", "Tooltip::for_action"),)
    if canonical == "SwitchField::new":
        return (
            (1, "switch_label", "SwitchField::new"),
            (2, "switch_description", "SwitchField::new"),
        )
    if canonical == "KeybindingHint::with_suffix" or canonical.endswith("::KeybindingHint::with_suffix"):
        return ((1, "keybinding_hint_suffix", "KeybindingHint::with_suffix"),)
    if canonical.endswith(".suffix") and "KeybindingHint::" in canonical:
        return ((0, "keybinding_hint_suffix", "KeybindingHint.suffix"),)
    if canonical in {"panel_button", "panel_filled_button"}:
        return ((0, "button", canonical),)
    if canonical == "split_button":
        return ((1, "button", "split_button"),)
    if canonical == "git_action_tooltip":
        return ((0, "tooltip", "git_action_tooltip"),)
    if canonical.endswith(".prompt") or canonical == "prompt":
        return (
            (1, "prompt_message", "prompt"),
            (2, "prompt_detail", "prompt"),
            (3, "prompt_answer", "prompt"),
        )
    if canonical.endswith(".title") and "Callout::new" in canonical:
        return ((0, "callout_title", "title"),)
    if canonical.endswith(".description") and (
        "Callout::new" in canonical or "ModalHeader::new" in canonical
    ):
        return ((0, "description", "description"),)
    if canonical.endswith(".label") or canonical == "label":
        return ((0, "label", "label"),)
    if canonical.endswith(".child") or canonical == "child":
        return ((0, "child_text", "child"),)
    if canonical.endswith(".entry"):
        return ((0, "context_menu_entry", "entry"),)
    if canonical.endswith(".toggleable_entry"):
        return ((0, "context_menu_entry", "toggleable_entry"),)
    if canonical.endswith(".submenu") or canonical.endswith(".submenu_with_icon"):
        return ((0, "context_menu_submenu", "submenu"),)
    if canonical.endswith(".action"):
        return ((0, "context_menu_action", "action"),)
    if canonical.endswith(".action_disabled_when"):
        return ((1, "context_menu_action", "action_disabled_when"),)
    if canonical.endswith(".heading") or canonical == "heading":
        return ((0, "announcement_heading", "heading"),)
    return ()


def _canonical_call(call: str) -> str:
    return call.strip()


def _looks_like_context_menu_header_call(call: str) -> bool:
    normalized = re.sub(r"\s+", "", call)
    return normalized.startswith("menu.") or ".menu." in normalized


def _extract_struct_field_occurrence(source_bytes: bytes, node, relative_path: str) -> StringOccurrence | None:
    struct_name = _nearest_struct_name(source_bytes, node)
    field_name = _field_name(source_bytes, node)
    if struct_name is None or field_name is None:
        return None
    if struct_name == "Content" and not _is_activity_indicator_path(relative_path):
        return None

    rule = STRUCT_FIELD_RULES.get((struct_name, field_name))
    if rule is None:
        return None

    value_node = node.child_by_field_name("value")
    if value_node is None:
        return None

    literal_node = _first_string_literal(value_node)
    if literal_node is None:
        return None

    literal = _node_text(source_bytes, literal_node)
    kind, call_name = rule
    return StringOccurrence(
        source=parse_rust_string_literal(literal),
        file=relative_path,
        line=literal_node.start_point[0] + 1,
        call=call_name,
        kind=kind,
        start_byte=literal_node.start_byte,
        end_byte=literal_node.end_byte,
    )


def _extract_ui_return_method_occurrences(source_bytes: bytes, node, relative_path: str) -> list[StringOccurrence]:
    name_node = node.child_by_field_name("name")
    body_node = node.child_by_field_name("body")
    if name_node is None or body_node is None:
        return []

    method_name = _node_text(source_bytes, name_node)
    rule = UI_RETURN_METHODS.get(method_name)
    if rule is None and relative_path == "crates/workspace/src/dock.rs" and method_name == "label":
        rule = ("dock_position_label", "DockPosition.label")
    if rule is None and _is_agent_tool_path(relative_path) and method_name == "initial_title":
        rule = ("agent_tool_title", "initial_title")
    if rule is None and _is_git_panel_path(relative_path):
        if method_name == "title":
            rule = ("git_section_title", "GitHeaderEntry.title")
        elif method_name == "commit_button_title":
            rule = ("button", "commit_button_title")
        elif method_name == "configure_commit_button":
            rule = ("tooltip", "configure_commit_button")
    if rule is None and _is_git_multi_diff_view_path(relative_path) and method_name == "title":
        rule = ("git_diff_title", "MultiDiffView.title")
    if rule is None and _is_inline_prompt_editor_path(relative_path) and method_name in {
        "tooltip_interrupt",
        "tooltip_restart",
        "tooltip_accept",
    }:
        rule = ("inline_prompt_tooltip", f"GenerationMode.{method_name}")
    if rule is None and _is_keymap_editor_path(relative_path) and method_name == "render_no_matches_hint":
        rule = ("empty_state", "render_no_matches_hint")
    if (
        rule is None
        and _is_git_worktree_picker_path(relative_path)
        and method_name == "creation_blocked_reason"
    ):
        rule = ("git_worktree_picker_disabled_reason", "creation_blocked_reason")
    if rule is None:
        return []

    kind, call_name = rule
    occurrences: list[StringOccurrence] = []
    literal_nodes = _string_literal_nodes(body_node)
    if call_name == "initial_title":
        literal_nodes = [
            literal_node
            for literal_node in literal_nodes
            if not _is_json_lookup_key(source_bytes, literal_node)
        ]
    for literal_node in literal_nodes:
        literal = _node_text(source_bytes, literal_node)
        source = parse_rust_string_literal(literal)
        if source == "":
            continue
        occurrences.append(
            StringOccurrence(
                source=source,
                file=relative_path,
                line=literal_node.start_point[0] + 1,
                call=call_name,
                kind=kind,
                start_byte=literal_node.start_byte,
                end_byte=literal_node.end_byte,
            )
        )
    return occurrences


def _string_literal_nodes(node) -> list:
    literals = []
    if node.type == "string_literal":
        literals.append(node)
    for child in node.named_children:
        literals.extend(_string_literal_nodes(child))
    return literals


def _is_json_lookup_key(source_bytes: bytes, node) -> bool:
    current = node.parent
    while current is not None:
        if current.type == "function_item":
            return False
        if current.type == "call_expression":
            function_node = current.child_by_field_name("function")
            arguments_node = current.child_by_field_name("arguments")
            call = _node_text(source_bytes, function_node) if function_node is not None else ""
            if arguments_node is not None and _node_contains(arguments_node, node) and (
                call.endswith(".get") or call.endswith(".pointer")
            ):
                return True
        current = current.parent
    return False


def _node_contains(parent, child) -> bool:
    return parent.start_byte <= child.start_byte and child.end_byte <= parent.end_byte


def _visible_literal_nodes(source_bytes: bytes, node, *, allow_unwrap_or: bool = False) -> list:
    if node.type == "string_literal":
        return [node]
    if node.type == "identifier":
        return _visible_literal_nodes_for_local_binding(
            source_bytes,
            node,
            allow_unwrap_or=allow_unwrap_or,
        )
    if node.type == "macro_invocation":
        macro_node = node.child_by_field_name("macro")
        macro_name = _node_text(source_bytes, macro_node) if macro_node is not None else ""
        if macro_name in {"format", "indoc"}:
            first = _first_string_literal(node)
            return [first] if first is not None else []
        return []
    if node.type in {
        "if_expression",
        "match_expression",
        "block",
        "else_clause",
        "closure_expression",
        "let_declaration",
        "match_block",
        "match_arm",
        "parenthesized_expression",
        "reference_expression",
        "array_expression",
        "arguments",
        "tuple_expression",
        "field_expression",
    }:
        return [
            literal
            for child in node.children
            for literal in _visible_literal_nodes(
                source_bytes,
                child,
                allow_unwrap_or=allow_unwrap_or,
            )
        ]
    if node.type == "call_expression":
        function_node = node.child_by_field_name("function")
        call = _node_text(source_bytes, function_node) if function_node is not None else ""
        if call in {
            "SharedString::from",
            "SharedString::new",
            "SharedString::new_static",
            "Some",
        } or call.endswith(".into") or call.endswith(".clone") or call.endswith(".to_string") or (
            allow_unwrap_or and call.endswith(".unwrap_or")
        ):
            return [
                literal
                for child in node.children
                for literal in _visible_literal_nodes(
                    source_bytes,
                    child,
                    allow_unwrap_or=allow_unwrap_or,
                )
            ]
    return []


def _visible_literal_nodes_for_local_binding(
    source_bytes: bytes,
    node,
    *,
    allow_unwrap_or: bool = False,
) -> list:
    name = _node_text(source_bytes, node)
    current = node.parent
    while current is not None:
        if current.type == "block":
            literals = _literal_nodes_from_prior_let_binding(
                source_bytes,
                current,
                name,
                node.start_byte,
                allow_unwrap_or=allow_unwrap_or,
            )
            if literals:
                return literals
        current = current.parent
    return []


def _literal_nodes_from_prior_let_binding(
    source_bytes: bytes,
    block_node,
    name: str,
    before_byte: int,
    *,
    allow_unwrap_or: bool = False,
) -> list:
    matched_literals: list = []
    for child in block_node.named_children:
        if child.end_byte >= before_byte:
            break
        if child.type != "let_declaration":
            continue

        pattern_node = child.child_by_field_name("pattern")
        value_node = child.child_by_field_name("value")
        if pattern_node is None or value_node is None:
            continue
        binds_name = _pattern_binds_name(source_bytes, pattern_node, name)
        if not binds_name:
            continue

        matched_literals = _visible_literal_nodes_for_pattern_binding(
            source_bytes,
            pattern_node,
            value_node,
            name,
            allow_unwrap_or=allow_unwrap_or,
        )
    return matched_literals


def _pattern_binds_name(source_bytes: bytes, pattern_node, name: str) -> bool:
    if _node_text(source_bytes, pattern_node) == name:
        return True
    if pattern_node.type not in {"tuple_pattern", "tuple_struct_pattern"}:
        return False
    return any(_node_text(source_bytes, child) == name for child in pattern_node.named_children)


def _visible_literal_nodes_for_pattern_binding(
    source_bytes: bytes,
    pattern_node,
    value_node,
    name: str,
    *,
    allow_unwrap_or: bool = False,
) -> list:
    if _node_text(source_bytes, pattern_node) == name:
        return _visible_literal_nodes(
            source_bytes,
            value_node,
            allow_unwrap_or=allow_unwrap_or,
        )
    if pattern_node.type not in {"tuple_pattern", "tuple_struct_pattern"}:
        return []

    index = _tuple_pattern_index_for_name(source_bytes, pattern_node, name)
    if index is None:
        return []

    return _visible_literal_nodes_for_tuple_index(
        source_bytes,
        value_node,
        index,
        allow_unwrap_or=allow_unwrap_or,
    )


def _tuple_pattern_index_for_name(source_bytes: bytes, pattern_node, name: str) -> int | None:
    for index, child in enumerate(pattern_node.named_children):
        if _node_text(source_bytes, child) == name:
            return index
    return None


def _visible_literal_nodes_for_tuple_index(
    source_bytes: bytes,
    node,
    index: int,
    *,
    allow_unwrap_or: bool = False,
) -> list:
    if node.type == "tuple_expression":
        values = node.named_children
        if index >= len(values):
            return []
        return _visible_literal_nodes(
            source_bytes,
            values[index],
            allow_unwrap_or=allow_unwrap_or,
        )
    if node.type == "if_expression":
        return [
            literal
            for child in node.named_children
            for literal in _visible_literal_nodes_for_tuple_index(
                source_bytes,
                child,
                index,
                allow_unwrap_or=allow_unwrap_or,
            )
        ]
    if node.type in {"block", "else_clause"}:
        return [
            literal
            for child in node.named_children
            for literal in _visible_literal_nodes_for_tuple_index(
                source_bytes,
                child,
                index,
                allow_unwrap_or=allow_unwrap_or,
            )
        ]
    return []


def _nearest_struct_name(source_bytes: bytes, node) -> str | None:
    current = node.parent
    while current is not None:
        if current.type == "struct_expression":
            name_node = current.child_by_field_name("name")
            if name_node is not None:
                return _node_text(source_bytes, name_node)
            return None
        current = current.parent
    return None


def _field_name(source_bytes: bytes, node) -> str | None:
    for child in node.named_children:
        if child.type == "field_identifier":
            return _node_text(source_bytes, child)
    return None


def _first_string_literal(node):
    if node.type == "string_literal":
        return node
    for child in node.named_children:
        found = _first_string_literal(child)
        if found is not None:
            return found
    return None


def _extract_line_candidates(source: str, relative_path: str) -> list[StringOccurrence]:
    candidates: list[StringOccurrence] = []
    byte_offset = 0
    in_announcement_bullets = False
    pending_multiline_pattern: LinePattern | None = None
    for line_index, line in enumerate(source.splitlines(keepends=True), start=1):
        if _is_non_doc_comment_line(line, relative_path):
            byte_offset += len(line.encode("utf-8"))
            continue

        if pending_multiline_pattern is not None:
            matches = _occurrences_for_line_pattern(
                pending_multiline_pattern,
                line,
                byte_offset,
                line_index,
                relative_path,
            )
            candidates.extend(matches)
            if matches:
                pending_multiline_pattern = None

        for pattern in _line_patterns_for_path(relative_path, line, in_announcement_bullets):
            candidates.extend(
                _occurrences_for_line_pattern(
                    pattern,
                    line,
                    byte_offset,
                    line_index,
                    relative_path,
                )
            )
        if _is_announcement_path(relative_path):
            if "bullet_items:" in line and "vec![" in line:
                in_announcement_bullets = True
            if in_announcement_bullets and "]," in line:
                in_announcement_bullets = False
        pending_multiline_pattern = (
            _pending_multiline_pattern_for_line(line, relative_path) or pending_multiline_pattern
        )
        byte_offset += len(line.encode("utf-8"))
    return candidates


def _extract_action_doc_comments(source: str, relative_path: str) -> list[StringOccurrence]:
    candidates: list[StringOccurrence] = []
    byte_offset = 0
    in_actions_macro = False
    actions_macro_depth = 0
    pending_docs: list[StringOccurrence] = []
    pending_has_action_derive = False
    pending_no_register = False

    def clear_pending_action_item() -> None:
        nonlocal pending_docs, pending_has_action_derive, pending_no_register
        pending_docs = []
        pending_has_action_derive = False
        pending_no_register = False

    for line_index, line in enumerate(source.splitlines(keepends=True), start=1):
        stripped = line.lstrip()
        doc_occurrence = _action_doc_comment_for_line(
            line,
            byte_offset,
            line_index,
            relative_path,
        )

        if in_actions_macro and doc_occurrence is not None:
            candidates.append(doc_occurrence)

        if doc_occurrence is not None:
            pending_docs.append(doc_occurrence)
        elif stripped.startswith("#["):
            if DERIVE_ACTION_PATTERN.search(line):
                pending_has_action_derive = True
            if ACTION_NO_REGISTER_PATTERN.search(line):
                pending_no_register = True
        else:
            if ACTION_ITEM_PATTERN.match(line):
                if pending_has_action_derive and not pending_no_register:
                    candidates.extend(pending_docs)
                clear_pending_action_item()
            elif not stripped:
                clear_pending_action_item()
            else:
                clear_pending_action_item()

        if not stripped.startswith("//"):
            if not in_actions_macro and ACTIONS_MACRO_START_PATTERN.search(line):
                in_actions_macro = True
                actions_macro_depth = _paren_delta(line)
            elif in_actions_macro:
                actions_macro_depth += _paren_delta(line)

            if in_actions_macro and actions_macro_depth <= 0:
                in_actions_macro = False

        byte_offset += len(line.encode("utf-8"))

    return candidates


def _action_doc_comment_for_line(
    line: str,
    byte_offset: int,
    line_index: int,
    relative_path: str,
) -> StringOccurrence | None:
    match = ACTION_DOC_COMMENT_PATTERN.match(line)
    if match is None:
        return None
    raw_value = match.group(1).strip()
    start_byte = byte_offset + len(line[: match.start(1)].encode("utf-8"))
    end_byte = byte_offset + len(line[: match.end(1)].encode("utf-8"))
    return StringOccurrence(
        source=raw_value,
        file=relative_path,
        line=line_index,
        call="action_doc_comment",
        kind="action_description",
        start_byte=start_byte,
        end_byte=end_byte,
    )


def _paren_delta(line: str) -> int:
    return line.count("(") - line.count(")")


def _is_non_doc_comment_line(line: str, relative_path: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("//"):
        return False
    return not _is_settings_content_path(relative_path)


def _occurrences_for_line_pattern(
    pattern: LinePattern,
    line: str,
    byte_offset: int,
    line_index: int,
    relative_path: str,
) -> list[StringOccurrence]:
    occurrences: list[StringOccurrence] = []
    for match in pattern.pattern.finditer(line):
        raw_value = match.group(pattern.value_group)
        start_byte = byte_offset + len(line[: match.start(pattern.value_group)].encode("utf-8"))
        end_byte = byte_offset + len(line[: match.end(pattern.value_group)].encode("utf-8"))
        source = parse_rust_string_literal(raw_value) if pattern.rust_literal else raw_value.strip()
        occurrences.append(
            StringOccurrence(
                source=source,
                file=relative_path,
                line=line_index,
                call=pattern.call,
                kind=pattern.kind,
                start_byte=start_byte,
                end_byte=end_byte,
            )
        )
    return occurrences


def _line_patterns_for_path(
    relative_path: str,
    line: str,
    in_announcement_bullets: bool,
) -> tuple[LinePattern, ...]:
    patterns: list[LinePattern] = list(LINE_PATTERNS)
    if _is_settings_ui_path(relative_path):
        patterns.extend(SETTINGS_UI_LINE_PATTERNS)
    if _is_settings_ui_root_path(relative_path):
        patterns.extend(SETTINGS_UI_ROOT_LINE_PATTERNS)
    if _is_settings_content_path(relative_path):
        patterns.extend(SETTINGS_CONTENT_LINE_PATTERNS)
    if _is_announcement_path(relative_path):
        patterns.extend(ANNOUNCEMENT_LINE_PATTERNS)
        if in_announcement_bullets:
            patterns.extend(ANNOUNCEMENT_BULLET_LINE_PATTERNS)
    if _is_title_bar_path(relative_path):
        patterns.extend(TITLE_BAR_LINE_PATTERNS)
    if _is_copilot_sign_in_path(relative_path):
        patterns.extend(COPILOT_SIGN_IN_LINE_PATTERNS)
    if _is_workspace_welcome_path(relative_path):
        patterns.extend(WORKSPACE_WELCOME_LINE_PATTERNS)
    if _is_app_menus_path(relative_path):
        patterns.extend(APP_MENU_LINE_PATTERNS)
    if _is_git_panel_path(relative_path):
        patterns.extend(GIT_PANEL_LINE_PATTERNS)
    if _is_git_blame_or_commit_tooltip_path(relative_path):
        patterns.extend(GIT_COMMIT_TOOLTIP_LINE_PATTERNS)
    if _is_git_branch_picker_path(relative_path):
        patterns.extend(GIT_BRANCH_PICKER_LINE_PATTERNS)
    if _is_git_picker_path(relative_path):
        patterns.extend(GIT_PICKER_LINE_PATTERNS)
    if _is_git_remote_output_path(relative_path):
        patterns.extend(GIT_REMOTE_OUTPUT_LINE_PATTERNS)
    if _is_git_text_diff_view_path(relative_path):
        patterns.extend(GIT_TEXT_DIFF_VIEW_LINE_PATTERNS)
    if _is_git_worktree_picker_path(relative_path):
        patterns.extend(GIT_WORKTREE_PICKER_LINE_PATTERNS)
    if _is_activity_indicator_path(relative_path):
        patterns.extend(ACTIVITY_INDICATOR_LINE_PATTERNS)
    if _is_language_selector_path(relative_path):
        patterns.extend(LANGUAGE_SELECTOR_LINE_PATTERNS)
    if _is_inline_prompt_editor_path(relative_path):
        patterns.extend(INLINE_PROMPT_EDITOR_LINE_PATTERNS)
    if _is_keymap_editor_path(relative_path):
        patterns.extend(KEYMAP_EDITOR_LINE_PATTERNS)
    if _is_rust_language_path(relative_path):
        patterns.extend(RUST_LANGUAGE_LINE_PATTERNS)
    if _is_workspace_pane_path(relative_path):
        patterns.extend(WORKSPACE_PANE_LINE_PATTERNS)
    if _is_agent_entry_view_state_path(relative_path):
        patterns.extend(AGENT_ENTRY_VIEW_STATE_LINE_PATTERNS)
    if _is_debugger_dap_log_path(relative_path):
        patterns.extend(DEBUGGER_DAP_LOG_LINE_PATTERNS)
    if _is_debugger_new_process_modal_path(relative_path):
        patterns.extend(DEBUGGER_NEW_PROCESS_MODE_LINE_PATTERNS)
    if "Self::new" in line and "IconName::" in line:
        patterns.extend(ICON_LABEL_LINE_PATTERNS)
    return tuple(patterns)


def _pending_multiline_pattern_for_line(line: str, relative_path: str) -> LinePattern | None:
    starts = list(MULTILINE_CALL_STARTS)
    if _is_copilot_sign_in_path(relative_path):
        starts.extend(COPILOT_SIGN_IN_MULTILINE_STARTS)
    if _is_rust_language_path(relative_path):
        starts.extend(RUST_LANGUAGE_MULTILINE_STARTS)
    if _is_git_panel_path(relative_path):
        starts.extend(GIT_PANEL_MULTILINE_STARTS)
    if _is_keymap_editor_path(relative_path):
        starts.extend(KEYMAP_EDITOR_MULTILINE_STARTS)
    for start_pattern, call, kind in starts:
        if start_pattern.search(line):
            return LinePattern(
                re.compile(r'^\s*("(?:\\.|[^"\\])*")'),
                call,
                kind,
                1,
            )
    return None


def _is_settings_ui_path(relative_path: str) -> bool:
    return relative_path.startswith("crates/settings_ui/src/")


def _is_settings_ui_root_path(relative_path: str) -> bool:
    return relative_path == "crates/settings_ui/src/settings_ui.rs"


def _is_settings_content_path(relative_path: str) -> bool:
    return relative_path.startswith("crates/settings_content/src/")


def _is_announcement_path(relative_path: str) -> bool:
    return relative_path in {
        "crates/auto_update_ui/src/auto_update_ui.rs",
        "crates/ui/src/components/notification/announcement_toast.rs",
    }


def _is_title_bar_path(relative_path: str) -> bool:
    return relative_path == "crates/title_bar/src/title_bar.rs"


def _is_activity_indicator_path(relative_path: str) -> bool:
    return relative_path == "crates/activity_indicator/src/activity_indicator.rs"


def _is_copilot_sign_in_path(relative_path: str) -> bool:
    return relative_path == "crates/copilot_ui/src/sign_in.rs"


def _is_workspace_welcome_path(relative_path: str) -> bool:
    return relative_path == "crates/workspace/src/welcome.rs"


def _is_app_menus_path(relative_path: str) -> bool:
    return relative_path == "crates/zed/src/zed/app_menus.rs"


def _is_workspace_pane_path(relative_path: str) -> bool:
    return relative_path == "crates/workspace/src/pane.rs"


def _is_agent_entry_view_state_path(relative_path: str) -> bool:
    return relative_path == "crates/agent_ui/src/entry_view_state.rs"


def _is_agent_tool_path(relative_path: str) -> bool:
    return relative_path.startswith("crates/agent/src/tools/")


def _is_debugger_dap_log_path(relative_path: str) -> bool:
    return relative_path == "crates/debugger_tools/src/dap_log.rs"


def _is_debugger_new_process_modal_path(relative_path: str) -> bool:
    return relative_path == "crates/debugger_ui/src/new_process_modal.rs"


def _is_git_panel_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/git_panel.rs"


def _is_git_blame_or_commit_tooltip_path(relative_path: str) -> bool:
    return relative_path in {
        "crates/git_ui/src/blame_ui.rs",
        "crates/git_ui/src/commit_tooltip.rs",
    }


def _is_git_branch_picker_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/branch_picker.rs"


def _is_git_picker_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/git_picker.rs"


def _is_git_remote_output_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/remote_output.rs"


def _is_git_worktree_picker_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/worktree_picker.rs"


def _is_git_multi_diff_view_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/multi_diff_view.rs"


def _is_git_text_diff_view_path(relative_path: str) -> bool:
    return relative_path == "crates/git_ui/src/text_diff_view.rs"


def _is_language_selector_path(relative_path: str) -> bool:
    return relative_path == "crates/language_selector/src/language_selector.rs"


def _is_inline_prompt_editor_path(relative_path: str) -> bool:
    return relative_path == "crates/agent_ui/src/inline_prompt_editor.rs"


def _is_keymap_editor_path(relative_path: str) -> bool:
    return relative_path == "crates/keymap_editor/src/keymap_editor.rs"


def _is_rust_language_path(relative_path: str) -> bool:
    return relative_path == "crates/languages/src/rust.rs"


ACTION_DOC_COMMENT_PATTERN = re.compile(r"^\s*///\s+(.+\S)\s*$")
ACTIONS_MACRO_START_PATTERN = re.compile(r"\bactions!\s*\(")
DERIVE_ACTION_PATTERN = re.compile(r"\bderive\s*\([^)]*\bAction\b")
ACTION_NO_REGISTER_PATTERN = re.compile(r"\bno_register\b")
ACTION_ITEM_PATTERN = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum)\s+\w+\b")

LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bMenuItem::action\s*\(\s*("(?:\\.|[^"\\])*")'),
        "MenuItem::action",
        "menu_item",
        1,
    ),
    LinePattern(
        re.compile(r'\bMenuItem::os_action\s*\(\s*("(?:\\.|[^"\\])*")'),
        "MenuItem::os_action",
        "menu_item",
        1,
    ),
    LinePattern(
        re.compile(r'\bMenu::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Menu::new",
        "menu",
        1,
    ),
    LinePattern(
        re.compile(r'\bContextMenuEntry::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ContextMenuEntry::new",
        "context_menu_entry",
        1,
    ),
    LinePattern(
        re.compile(r'\bConfiguredApiCard::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ConfiguredApiCard::new",
        "configured_api_card_label",
        1,
    ),
    LinePattern(
        re.compile(r'\bDropdownMenu::new\s*\(\s*[^,\n]+,\s*("(?:\\.|[^"\\])*")'),
        "DropdownMenu::new",
        "dropdown_label",
        1,
    ),
    LinePattern(
        re.compile(r'\bLabel::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Label::new",
        "label",
        1,
    ),
    LinePattern(
        re.compile(r'\bButton::new\s*\(\s*[^,\n]+,\s*("(?:\\.|[^"\\])*")'),
        "Button::new",
        "button",
        1,
    ),
    LinePattern(
        re.compile(r'\bCopyButton::new\s*\(\s*[^,\n]+,\s*("(?:\\.|[^"\\])*")'),
        "CopyButton::new",
        "button",
        1,
    ),
    LinePattern(
        re.compile(r'\bButtonLink::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ButtonLink::new",
        "button_link",
        1,
    ),
    LinePattern(
        re.compile(r'\bHeadline::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Headline::new",
        "headline",
        1,
    ),
    LinePattern(
        re.compile(r'\bTooltip::text\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Tooltip::text",
        "tooltip",
        1,
    ),
    LinePattern(
        re.compile(r'\bTooltip::simple\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Tooltip::simple",
        "tooltip",
        1,
    ),
    LinePattern(
        re.compile(r'\bTooltip::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Tooltip::new",
        "tooltip",
        1,
    ),
    LinePattern(
        re.compile(r'\bTooltip::for_action(?:_in)?\s*\(\s*("(?:\\.|[^"\\])*")'),
        "Tooltip::for_action",
        "tooltip",
        1,
    ),
    LinePattern(
        re.compile(r'\bToast::new\s*\(\s*[^,\n]+,\s*("(?:\\.|[^"\\])*")'),
        "Toast::new",
        "toast",
        1,
    ),
    LinePattern(
        re.compile(r'\bStatusToast::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "StatusToast::new",
        "status_toast",
        1,
    ),
    LinePattern(
        re.compile(r'\bMessageNotification::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "MessageNotification::new",
        "notification",
        1,
    ),
    LinePattern(
        re.compile(r'\bErrorMessagePrompt::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ErrorMessagePrompt::new",
        "error_prompt",
        1,
    ),
    LinePattern(
        re.compile(r'\bLoadingLabel::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "LoadingLabel::new",
        "loading_label",
        1,
    ),
    LinePattern(
        re.compile(r'\bcopilot_toast\s*\(\s*Some\(\s*("(?:\\.|[^"\\])*")'),
        "copilot_toast",
        "toast",
        1,
    ),
    LinePattern(
        re.compile(r'\bSectionHeader::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "SectionHeader::new",
        "section_header",
        1,
    ),
    LinePattern(
        re.compile(r'\bSettingsSectionHeader::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "SettingsSectionHeader::new",
        "settings_section_header",
        1,
    ),
    LinePattern(
        re.compile(r'\bSettingsPageItem::SectionHeader\s*\(\s*("(?:\\.|[^"\\])*")'),
        "SettingsPageItem::SectionHeader",
        "settings_section_header",
        1,
    ),
    LinePattern(
        re.compile(r'\bListBulletItem::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ListBulletItem::new",
        "list_bullet_item",
        1,
    ),
    LinePattern(
        re.compile(r'\bProfileModalHeader::new\s*\(\s*("(?:\\.|[^"\\])*")'),
        "ProfileModalHeader::new",
        "modal_header",
        1,
    ),
    LinePattern(
        re.compile(r'\.set_placeholder_text\s*\(\s*("(?:\\.|[^"\\])*")'),
        "set_placeholder_text",
        "placeholder",
        1,
    ),
    LinePattern(
        re.compile(r'\.tooltip_label\s*\(\s*("(?:\\.|[^"\\])*")'),
        "tooltip_label",
        "tooltip",
        1,
    ),
    LinePattern(
        re.compile(r'\.headline\s*\(\s*("(?:\\.|[^"\\])*")'),
        "headline",
        "headline",
        1,
    ),
    LinePattern(
        re.compile(r'\bmenu(?:\.[A-Za-z_][A-Za-z0-9_]*\([^)]*\))*\.header\s*\(\s*("(?:\\.|[^"\\])*")'),
        "header",
        "context_menu_header",
        1,
    ),
    LinePattern(
        re.compile(r'\.button_label\s*\(\s*("(?:\\.|[^"\\])*")'),
        "button_label",
        "button_label",
        1,
    ),
    LinePattern(
        re.compile(r'\.with_link_button\s*\(\s*("(?:\\.|[^"\\])*")(?:\.to_string\(\))?'),
        "with_link_button",
        "link_button",
        1,
    ),
    LinePattern(
        re.compile(r'\.primary_message\s*\(\s*("(?:\\.|[^"\\])*")'),
        "primary_message",
        "notification_message",
        1,
    ),
    LinePattern(
        re.compile(r'\.secondary_message\s*\(\s*("(?:\\.|[^"\\])*")'),
        "secondary_message",
        "notification_message",
        1,
    ),
    LinePattern(
        re.compile(r'\.link\s*\(\s*("(?:\\.|[^"\\])*")'),
        "link",
        "link",
        1,
    ),
    LinePattern(
        re.compile(r'\.link_with_handler\s*\(\s*("(?:\\.|[^"\\])*")'),
        "link_with_handler",
        "link",
        1,
    ),
    LinePattern(
        re.compile(r'\.label\s*\(\s*("(?:\\.|[^"\\])*")'),
        "label",
        "label",
        1,
    ),
    LinePattern(
        re.compile(r'\.child\s*\(\s*("(?:\\.|[^"\\])*")'),
        "child",
        "child_text",
        1,
    ),
    LinePattern(
        re.compile(r'\.entry\s*\(\s*("(?:\\.|[^"\\])*")'),
        "entry",
        "context_menu_entry",
        1,
    ),
    LinePattern(
        re.compile(r'\.action\s*\(\s*("(?:\\.|[^"\\])*")'),
        "action",
        "context_menu_action",
        1,
    ),
    LinePattern(
        re.compile(r'\.heading\s*\(\s*("(?:\\.|[^"\\])*")'),
        "heading",
        "announcement_heading",
        1,
    ),
)

MULTILINE_CALL_STARTS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r'\bMenuItem::action\s*\(\s*$'),
        "MenuItem::action",
        "menu_item",
    ),
    (
        re.compile(r'\bMenuItem::os_action\s*\(\s*$'),
        "MenuItem::os_action",
        "menu_item",
    ),
    (
        re.compile(r'\bContextMenuEntry::new\s*\(\s*$'),
        "ContextMenuEntry::new",
        "context_menu_entry",
    ),
    (
        re.compile(r'\.action\s*\(\s*$'),
        "action",
        "context_menu_action",
    ),
)

SETTINGS_UI_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\btitle:\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "settings_field_title",
        "setting_title",
        1,
    ),
    LinePattern(
        re.compile(r'\bdescription:\s*(?:Some\(\s*)?("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "settings_field_description",
        "setting_description",
        1,
    ),
    LinePattern(
        re.compile(r'\bbutton_text:\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "settings_action_button",
        "setting_action_button",
        1,
    ),
    LinePattern(
        re.compile(r'\bplaceholder:\s*(?:Some\()?("(?:\\.|[^"\\])*")'),
        "settings_field_placeholder",
        "setting_placeholder",
        1,
    ),
)

SETTINGS_UI_ROOT_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bSettingsUiFile::User\s*=>\s*Some\(\s*("(?:\\.|[^"\\])*")\.to_string\(\)\s*\)'),
        "SettingsUiFile.display_name",
        "settings_file_label",
        1,
    ),
)

SETTINGS_CONTENT_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*///\s+(.+\S)\s*$'),
        "rust_doc_comment",
        "rust_doc_comment",
        1,
        rust_literal=False,
    ),
)

ANNOUNCEMENT_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bheading:\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "announcement_heading",
        "announcement_heading",
        1,
    ),
    LinePattern(
        re.compile(r'\bdescription:\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "announcement_description",
        "announcement_description",
        1,
    ),
    LinePattern(
        re.compile(r'\bprimary_action_label:\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "announcement_primary_action",
        "announcement_primary_action",
        1,
    ),
    LinePattern(
        re.compile(r'\bbullet_items:\s*vec!\[\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?'),
        "announcement_bullet",
        "announcement_bullet",
        1,
    ),
)

ANNOUNCEMENT_BULLET_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*("(?:\\.|[^"\\])*")(?:\.into\(\))?,?\s*$'),
        "announcement_bullet",
        "announcement_bullet",
        1,
    ),
)

ICON_LABEL_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bSelf::new\s*\(\s*IconName::[A-Za-z0-9_]+,\s*("(?:\\.|[^"\\])*")'),
        "Self::new",
        "icon_label",
        1,
    ),
)

TITLE_BAR_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'("(?:\\.|[^"\\])*")\.to_string\(\)'),
        "to_string",
        "title_bar_label",
        1,
    ),
)


WORKSPACE_WELCOME_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\btitle:\s*("(?:\\.|[^"\\])*")'),
        "WelcomeSection.title",
        "welcome_section_title",
        1,
    ),
)


APP_MENU_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bname:\s*("(?:\\.|[^"\\])*")\.into\(\)'),
        "Menu.name",
        "menu",
        1,
    ),
)


WORKSPACE_PANE_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*Split[A-Za-z0-9_]*\s*=>\s*("(?:\\.|[^"\\])*")'),
        "split_structs",
        "action_description",
        1,
    ),
)


GIT_PANEL_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*("(?:\\.|[^"\\])*")\.into_any_element\(\),?\s*$'),
        "into_any_element",
        "child_text",
        1,
    ),
    LinePattern(
        re.compile(r'\bpanel_button\s*\(\s*("(?:\\.|[^"\\])*")'),
        "panel_button",
        "button",
        1,
    ),
    LinePattern(
        re.compile(r'\bpanel_filled_button\s*\(\s*("(?:\\.|[^"\\])*")'),
        "panel_filled_button",
        "button",
        1,
    ),
    LinePattern(
        re.compile(r'\bformat!\(\s*("(?:Are you sure you want to discard changes to \{\}\?|\\nand \{\} more…)")'),
        "git_panel_prompt_format",
        "prompt_message",
        1,
    ),
    LinePattern(
        re.compile(r'\bprompt\(\s*("(?:Discard changes to these files\?|Trash these files\?)")'),
        "git_panel_prompt",
        "prompt_message",
        1,
    ),
    LinePattern(
        re.compile(
            r'^\s*("(?:Are you sure you want to discard changes to \{\}\?|Discard changes to these files\?|Pick which remote to fetch|Pick which remote to push to|Where would you like to initialize this git repository\?)"),?\s*$'
        ),
        "git_panel_prompt",
        "prompt_message",
        1,
    ),
    LinePattern(
        re.compile(r'&\[\s*("(?:\\.|[^"\\])*")'),
        "git_panel_prompt_answer",
        "prompt_answer",
        1,
    ),
    LinePattern(
        re.compile(r'&\[\s*"(?:\\.|[^"\\])*"\s*,\s*("(?:\\.|[^"\\])*")'),
        "git_panel_prompt_answer",
        "prompt_answer",
        1,
    ),
    LinePattern(
        re.compile(r'("(?:Remove co-authored-by|Add co-authored-by)"),\s*IconName::'),
        "git_panel_coauthor_tooltip",
        "tooltip",
        1,
    ),
)


GIT_PANEL_MULTILINE_STARTS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r'\bpicker_prompt::prompt\s*\(\s*$'),
        "picker_prompt::prompt",
        "picker_prompt",
    ),
)


GIT_COMMIT_TOOLTIP_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\.unwrap_or(?:_else)?\(\s*("(?:<no name>|<no commit message>)")'),
        "git_commit_fallback",
        "git_commit_fallback",
        1,
    ),
)


GIT_BRANCH_PICKER_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bformat!\(\s*("(?:Based off \{\}|Based off \{url\})")'),
        "branch_picker_subtitle",
        "branch_picker_subtitle",
        1,
    ),
    LinePattern(
        re.compile(r'("(?:Based off the current branch)")\.to_string\(\)'),
        "branch_picker_subtitle",
        "branch_picker_subtitle",
        1,
    ),
)


GIT_PICKER_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'GitPickerTab::(?:Branches|Stash)\s*=>\s*("(?:Branches|Stash)")'),
        "GitPickerTab.to_string",
        "git_picker_tab",
        1,
    ),
)


GIT_REMOTE_OUTPUT_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\bmessage:\s*("(?:Fetch: Already up to date|Pull: Already up to date)")'),
        "SuccessMessage.message",
        "git_remote_toast",
        1,
    ),
    LinePattern(
        re.compile(
            r'\bformat!\(\s*('
            r'"(?:Synchronized with \{\}'
            r'|Received \{\} file change\{\} from \{\}'
            r'|Fast forwarded from \{\}'
            r'|Merged \{\} file change\{\} from \{\}'
            r'|Merged from \{\}'
            r'|Successfully rebased from \{\}'
            r'|Successfully pulled from \{\}'
            r'|Pushed \{\} to \{\})")'
        ),
        "SuccessMessage.message",
        "git_remote_toast",
        1,
    ),
    LinePattern(
        re.compile(r'("(?:Synchronized with remotes)")\.into\(\)'),
        "SuccessMessage.message",
        "git_remote_toast",
        1,
    ),
    LinePattern(
        re.compile(r'("(?:Push: Everything is up-to-date)")\.to_string\(\)'),
        "SuccessMessage.message",
        "git_remote_toast",
        1,
    ),
    LinePattern(
        re.compile(r'\("[^"]+",\s*("(?:Create Pull Request|Create Merge Request|View Merge Request)")'),
        "SuccessStyle::PushPrLink.text",
        "git_remote_link",
        1,
    ),
)


GIT_TEXT_DIFF_VIEW_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\btitle:\s*format!\(\s*("(?:\\.|[^"\\])*")'),
        "TextDiffView.title",
        "git_diff_title",
        1,
    ),
    LinePattern(
        re.compile(r'\bpath:\s*Some\(\s*format!\(\s*("(?:\\.|[^"\\])*")'),
        "TextDiffView.path",
        "git_diff_path",
        1,
    ),
)


GIT_WORKTREE_PICKER_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(
            r'\bformat!\(\s*("(?:Create new worktree based on \{branch_label\}|Create new worktree based on \{default_branch_name\})")'
        ),
        "WorktreePicker.create_label",
        "git_worktree_picker_label",
        1,
    ),
)


ACTIVITY_INDICATOR_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(
            r'\bformat!\(\s*('
            r'"(?:Language server \{server_name\}:\\n\\n\{status\}'
            r'|\(\{server_name\}\) (?:Warning|Error): '
            r'|(?:Installing|Updating|Removing) \{extension_id\} extension…)"'
            r')'
        ),
        "activity_indicator_format",
        "status_message",
        1,
    ),
    LinePattern(
        re.compile(r'\bwrite!\(\s*&mut\s+message,\s*(" \+ \{\} more")'),
        "activity_indicator_message_suffix",
        "status_message",
        1,
    ),
)


LANGUAGE_SELECTOR_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\blabel\.push_str\s*\(\s*("(?:\\.|[^"\\])*")'),
        "language_selector_current_suffix",
        "language_selector_label",
        1,
    ),
)


INLINE_PROMPT_EDITOR_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r"^\s*(\"(?:Changes will be discarded|Changes won't be discarded)\"),?\s*$"),
        "Tooltip::with_meta",
        "tooltip_meta",
        1,
    ),
)


KEYMAP_EDITOR_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(
            r'\.header\(vec!\["",\s*("Action"),\s*"Arguments",\s*"Keystrokes",\s*"Context",\s*"Source"\]'
        ),
        "Table.header",
        "table_header",
        1,
    ),
    LinePattern(
        re.compile(
            r'\.header\(vec!\["",\s*"Action",\s*("Arguments"),\s*"Keystrokes",\s*"Context",\s*"Source"\]'
        ),
        "Table.header",
        "table_header",
        1,
    ),
    LinePattern(
        re.compile(
            r'\.header\(vec!\["",\s*"Action",\s*"Arguments",\s*("Keystrokes"),\s*"Context",\s*"Source"\]'
        ),
        "Table.header",
        "table_header",
        1,
    ),
    LinePattern(
        re.compile(
            r'\.header\(vec!\["",\s*"Action",\s*"Arguments",\s*"Keystrokes",\s*("Context"),\s*"Source"\]'
        ),
        "Table.header",
        "table_header",
        1,
    ),
    LinePattern(
        re.compile(
            r'\.header\(vec!\["",\s*"Action",\s*"Arguments",\s*"Keystrokes",\s*"Context",\s*("Source")\]'
        ),
        "Table.header",
        "table_header",
        1,
    ),
    LinePattern(
        re.compile(r'anyhow::ensure!\([^,]+,\s*("Keystrokes cannot be empty")'),
        "validate_keystrokes",
        "input_error",
        1,
    ),
    LinePattern(
        re.compile(r'\.context\(\s*("(?:Failed to parse key context|Failed to validate action arguments)")'),
        "InputError.context",
        "input_error",
        1,
    ),
    LinePattern(
        re.compile(
            r'\bformat!\(\s*("(?:Your keybind would conflict with the \\"\{\}\\" action and \{\} other bindings|Your keybind would conflict with the \\"\{\}\\" action)")'
        ),
        "InputError.warning",
        "input_warning",
        1,
    ),
    LinePattern(
        re.compile(r'("(?:Your keybind would conflict with other actions)")\.to_string\(\)'),
        "InputError.warning",
        "input_warning",
        1,
    ),
)


KEYMAP_EDITOR_MULTILINE_STARTS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r'\.map\(add_filter\(\s*$'),
        "add_filter",
        "filter_label",
    ),
)


RUST_LANGUAGE_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\blabel:\s*format!\(\s*("(?:\\.|[^"\\])*")'),
        "TaskTemplate.label",
        "task_template_label",
        1,
    ),
    LinePattern(
        re.compile(r'\blabel:\s*("(?:\\.|[^"\\])*")\.into\(\)'),
        "TaskTemplate.label",
        "task_template_label",
        1,
    ),
)


RUST_LANGUAGE_MULTILINE_STARTS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r'^\s*label:\s*format!\(\s*$'),
        "TaskTemplate.label",
        "task_template_label",
    ),
)


AGENT_ENTRY_VIEW_STATE_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*("Edit message － @ to include context"),?\s*$'),
        "MessageEditor::new",
        "placeholder",
        1,
    ),
)


DEBUGGER_DAP_LOG_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(
            r'^\s*const\s+(?:ADAPTER_LOGS|RPC_MESSAGES|INITIALIZATION_SEQUENCE):\s*&str\s*=\s*("(?:\\.|[^"\\])*")'
        ),
        "dap_log_view_label",
        "debugger_view_label",
        1,
    ),
)


DEBUGGER_NEW_PROCESS_MODE_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'^\s*NewProcessMode::(?:Task|Debug|Attach|Launch)\s*=>\s*("(?:\\.|[^"\\])*")'),
        "NewProcessMode.display",
        "debugger_mode_label",
        1,
    ),
)


COPILOT_SIGN_IN_LINE_PATTERNS: tuple[LinePattern, ...] = (
    LinePattern(
        re.compile(r'\blet\s+(?:start_label|no_status_label)\s*=\s*("(?:\\.|[^"\\])*")'),
        "copilot_status_label",
        "status_message",
        1,
    ),
)


COPILOT_SIGN_IN_MULTILINE_STARTS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r'^\s*const\s+ERROR_LABEL:\s*&str\s*=\s*$'),
        "copilot_status_label",
        "status_message",
    ),
)


def _dedupe_occurrences(occurrences: list[StringOccurrence]) -> list[StringOccurrence]:
    seen: set[tuple[str, str, int]] = set()
    unique: list[StringOccurrence] = []
    for occurrence in occurrences:
        key = (occurrence.file, occurrence.source, occurrence.line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(occurrence)
    return unique
