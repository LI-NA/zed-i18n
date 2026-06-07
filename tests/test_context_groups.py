import json
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.context_groups import (
    build_context_groups,
    context_groups_by_source,
    source_batches_for_context_groups,
    write_context_group_reports,
)


class ContextGroupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.zed_root = self.root / "zed"
        self.zed_root.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_builds_setting_group_with_title_description_and_current_translations(self) -> None:
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Line Width",',
                    '        description: "The width of the indent guides in pixels, between 1 and 10.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("editor.indent_guides.line_width"),',
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "}",
                ]
            ),
        )
        manifest = {
            "Line Width": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "The width of the indent guides in pixels, between 1 and 10.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        4,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={"Line Width": "선 너비"},
        )

        self.assertEqual(len(groups.settings), 1)
        group = groups.settings[0]
        self.assertEqual(group["type"], "setting")
        self.assertEqual(group["file"], "crates/settings_ui/src/page_data.rs")
        self.assertEqual(group["context_key"], "editor.indent_guides.line_width")
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in group["entries"]],
            [
                ("title", "Line Width"),
                ("description", "The width of the indent guides in pixels, between 1 and 10."),
            ],
        )
        self.assertEqual(group["entries"][0]["current_translation"], "선 너비")

    def test_builds_connected_line_group_from_adjacent_doc_comments(self) -> None:
        self._write_source(
            "crates/agent_ui/src/agent_ui.rs",
            "\n".join(
                [
                    "/// Action to authorize a tool call with a specific permission option.",
                    "/// This is used by the permission granularity dropdown to authorize tool calls.",
                    "#[derive(Action)]",
                    "pub struct AuthorizeToolCall;",
                ]
            ),
        )
        manifest = {
            "Action to authorize a tool call with a specific permission option.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/agent_ui/src/agent_ui.rs",
                        1,
                        "action_doc_comment",
                        "action_description",
                    )
                ],
            },
            "This is used by the permission granularity dropdown to authorize tool calls.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/agent_ui/src/agent_ui.rs",
                        2,
                        "action_doc_comment",
                        "action_description",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={},
        )

        self.assertEqual(len(groups.connected_lines), 1)
        group = groups.connected_lines[0]
        self.assertEqual(group["type"], "connected_lines")
        self.assertEqual(
            group["joined_source"],
            "Action to authorize a tool call with a specific permission option. "
            "This is used by the permission granularity dropdown to authorize tool calls.",
        )
        self.assertEqual([entry["line"] for entry in group["entries"]], [1, 2])

    def test_builds_prompt_component_group_for_project_panel_delete_prompt(self) -> None:
        file = "crates/project_panel/src/project_panel.rs"
        manifest = {
            "A file or folder with name {} ": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 4342, "prompt", "prompt_message")
                ],
            },
            "already exists in the destination folder. ": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 4343, "replace_prompt_message", "prompt_message")
                ],
            },
            "Do you want to replace it?": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 4344, "replace_prompt_message", "prompt_message")
                ],
            },
            "Do you want to trash": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 2350, "delete_prompt_message_start", "prompt_message")
                ],
            },
            "Are you sure you want to permanently delete": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 2352, "delete_prompt_message_start", "prompt_message")
                ],
            },
            "{message_start} {}?{unsaved_warning}": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 2363, "delete_prompt_format", "prompt_message")
                ],
            },
            "\n\nIt has unsaved changes, which will be lost.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(file, 2357, "delete_prompt_unsaved_warning", "prompt_message")
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={"Do you want to trash": "휴지통으로 이동"},
        )

        self.assertEqual(len(groups.prompt_components), 2)
        group = next(
            group
            for group in groups.prompt_components
            if group["subtype"] == "project_panel_delete_prompt"
        )
        self.assertEqual(group["type"], "prompt_components")
        self.assertEqual(group["subtype"], "project_panel_delete_prompt")
        self.assertEqual(
            [entry["source"] for entry in group["entries"]],
            [
                "Do you want to trash",
                "Are you sure you want to permanently delete",
                "\n\nIt has unsaved changes, which will be lost.",
                "{message_start} {}?{unsaved_warning}",
            ],
        )
        self.assertEqual(group["entries"][0]["current_translation"], "휴지통으로 이동")

        replace_group = next(
            group
            for group in groups.prompt_components
            if group["subtype"] == "project_panel_replace_prompt"
        )
        self.assertEqual(
            [entry["source"] for entry in replace_group["entries"]],
            [
                "A file or folder with name {} ",
                "already exists in the destination folder. ",
                "Do you want to replace it?",
            ],
        )

        contexts = context_groups_by_source(
            groups,
            {"{message_start} {}?{unsaved_warning}"},
        )
        self.assertEqual(
            contexts["{message_start} {}?{unsaved_warning}"]["subtype"],
            "project_panel_delete_prompt",
        )

        batches = source_batches_for_context_groups(
            [
                "Do you want to trash",
                "Are you sure you want to permanently delete",
                "{message_start} {}?{unsaved_warning}",
                "\n\nIt has unsaved changes, which will be lost.",
            ],
            manifest,
            groups,
            batch_size=10,
        )
        self.assertEqual(
            batches,
            [
                [
                    "Do you want to trash",
                    "Are you sure you want to permanently delete",
                    "\n\nIt has unsaved changes, which will be lost.",
                    "{message_start} {}?{unsaved_warning}",
                ]
            ],
        )

    def test_builds_setting_enum_group_from_dropdown_variant_labels(self) -> None:
        self._write_source(
            "crates/settings_content/src/agent.rs",
            "\n".join(
                [
                    "pub enum ThinkingBlockDisplay {",
                    "    Auto,",
                    "    Preview,",
                    "    AlwaysExpanded,",
                    "}",
                ]
            ),
        )
        manifest = {
            "Auto": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/agent.rs",
                        2,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Preview": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/agent.rs",
                        3,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Always Expanded": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/agent.rs",
                        4,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={"Auto": "자동"},
        )

        self.assertEqual(len(groups.settings), 1)
        group = groups.settings[0]
        self.assertEqual(group["subtype"], "settings_enum")
        self.assertEqual(group["context_key"], "ThinkingBlockDisplay")
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in group["entries"]],
            [
                ("option", "Auto"),
                ("option", "Preview"),
                ("option", "Always Expanded"),
            ],
        )
        self.assertEqual(group["entries"][0]["current_translation"], "자동")

    def test_builds_setting_groups_with_dropdown_options(self) -> None:
        self._write_source(
            "crates/settings_content/src/theme.rs",
            "\n".join(
                [
                    "pub struct ThemeSettingsContent {",
                    "    pub buffer_line_height: Option<BufferLineHeight>,",
                    "}",
                    "pub enum BufferLineHeight {",
                    "    Comfortable,",
                    "    Standard,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_content/src/workspace.rs",
            "\n".join(
                [
                    "pub struct ProjectPanelSettingsContent {",
                    "    pub entry_spacing: Option<ProjectPanelEntrySpacing>,",
                    "}",
                    "pub enum ProjectPanelEntrySpacing {",
                    "    Comfortable,",
                    "    Standard,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Line Height",',
                    '        description: "Line height for editor text.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("buffer_line_height$"),',
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "    settings::BufferLineHeightDiscriminants::Custom => vec![SettingItem {",
                    '        title: "Custom Line Height",',
                    '        description: "Custom line height value (must be at least 1.0).",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("buffer_line_height"),',
                    "            pick: |settings_content| match settings_content.theme.buffer_line_height.as_ref()? {",
                    "                settings::BufferLineHeight::Custom(line_height) => Some(line_height),",
                    "                _ => None,",
                    "            },",
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Entry Spacing",',
                    '        description: "Spacing between worktree entries in the project panel.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("project_panel.entry_spacing"),',
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "}",
                ]
            ),
        )
        manifest = {
            "Line Height": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Line height for editor text.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        4,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Entry Spacing": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        23,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Spacing between worktree entries in the project panel.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        24,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Custom Line Height": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        11,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Custom line height value (must be at least 1.0).": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        12,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Comfortable": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        5,
                        "strum::EnumDiscriminants",
                        "settings_enum_discriminant_label",
                    ),
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        5,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                ],
            },
            "Standard": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        6,
                        "strum::EnumDiscriminants",
                        "settings_enum_discriminant_label",
                    ),
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        6,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={"Line Height": "줄 높이"},
        )

        setting_groups = {
            group["context_key"]: group
            for group in groups.settings
            if group.get("subtype") == "setting_with_options"
        }
        self.assertEqual(set(setting_groups), {"buffer_line_height$", "project_panel.entry_spacing"})
        custom_group = next(
            group
            for group in groups.settings
            if group.get("context_key") == "buffer_line_height"
        )
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in custom_group["entries"]],
            [
                ("title", "Custom Line Height"),
                ("description", "Custom line height value (must be at least 1.0)."),
            ],
        )
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in setting_groups["buffer_line_height$"]["entries"]],
            [
                ("title", "Line Height"),
                ("description", "Line height for editor text."),
                ("option", "Comfortable"),
                ("option", "Standard"),
            ],
        )
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in setting_groups["project_panel.entry_spacing"]["entries"]],
            [
                ("title", "Entry Spacing"),
                ("description", "Spacing between worktree entries in the project panel."),
                ("option", "Comfortable"),
                ("option", "Standard"),
            ],
        )

        contexts = context_groups_by_source(groups, {"Comfortable"})
        self.assertEqual(contexts["Comfortable"]["type"], "related_context_groups")
        self.assertEqual(len(contexts["Comfortable"]["groups"]), 2)

        batches = source_batches_for_context_groups(
            ["Comfortable", "Standard"],
            manifest,
            groups,
            batch_size=40,
        )
        self.assertEqual([source for batch in batches for source in batch], ["Comfortable", "Standard"])

    def test_builds_setting_group_options_from_full_json_path_when_field_name_is_ambiguous(self) -> None:
        self._write_source(
            "crates/settings_content/src/editor.rs",
            "\n".join(
                [
                    "pub struct EditorSettingsContent {",
                    "    pub minimap: Option<MinimapContent>,",
                    "    pub indent_guides: Option<IndentGuidesSettingsContent>,",
                    "}",
                    "pub struct MinimapContent {",
                    "    pub show: Option<ShowMinimap>,",
                    "}",
                    "pub struct IndentGuidesSettingsContent {",
                    "    pub show: Option<ShowIndentGuides>,",
                    "}",
                    "pub enum ShowMinimap {",
                    "    Auto,",
                    "    Always,",
                    "    Never,",
                    "}",
                    "pub enum ShowIndentGuides {",
                    "    Always,",
                    "    Never,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Show Minimap",',
                    '        description: "When to show the minimap in the editor.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("minimap.show"),',
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "}",
                ]
            ),
        )
        manifest = {
            "Show Minimap": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "When to show the minimap in the editor.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        4,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Auto": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/editor.rs",
                        12,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Always": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/editor.rs",
                        13,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                    self._occurrence(
                        "crates/settings_content/src/editor.rs",
                        17,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                ],
            },
            "Never": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/editor.rs",
                        14,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                    self._occurrence(
                        "crates/settings_content/src/editor.rs",
                        18,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    ),
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={},
        )

        group = next(group for group in groups.settings if group.get("context_key") == "minimap.show")
        self.assertEqual(group["subtype"], "setting_with_options")
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in group["entries"]],
            [
                ("title", "Show Minimap"),
                ("description", "When to show the minimap in the editor."),
                ("option", "Auto"),
                ("option", "Always"),
                ("option", "Never"),
            ],
        )

    def test_does_not_link_dropdown_options_when_pick_path_disagrees_with_json_path(self) -> None:
        self._write_source(
            "crates/settings_content/src/workspace.rs",
            "\n".join(
                [
                    "pub struct CollaborationPanelSettingsContent {",
                    "    pub dock: Option<DockPosition>,",
                    "    pub default_width: Option<Pixels>,",
                    "}",
                    "pub enum DockPosition {",
                    "    Left,",
                    "    Bottom,",
                    "    Right,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Collaboration Panel Dock",',
                    '        description: "Where to dock the collaboration panel.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("collaboration_panel.dock"),',
                    "            pick: |settings_content| {",
                    "                settings_content.collaboration_panel.as_ref()?.dock.as_ref()",
                    "            },",
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Collaboration Panel Default Width",',
                    '        description: "Default width of the collaboration panel in pixels.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("collaboration_panel.dock"),',
                    "            pick: |settings_content| {",
                    "                settings_content.collaboration_panel.as_ref()?.default_width.as_ref()",
                    "            },",
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "}",
                ]
            ),
        )
        manifest = {
            "Collaboration Panel Dock": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Where to dock the collaboration panel.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        4,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Collaboration Panel Default Width": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        14,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Default width of the collaboration panel in pixels.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        15,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Left": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        6,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Bottom": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        7,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Right": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        8,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={},
        )

        by_title = {
            next(entry["source"] for entry in group["entries"] if entry["role"] == "title"): group
            for group in groups.settings
            if any(entry["role"] == "title" for entry in group["entries"])
        }
        self.assertEqual(by_title["Collaboration Panel Dock"]["subtype"], "setting_with_options")
        self.assertEqual(
            [entry["source"] for entry in by_title["Collaboration Panel Dock"]["entries"] if entry["role"] == "option"],
            ["Left", "Bottom", "Right"],
        )
        self.assertEqual(by_title["Collaboration Panel Default Width"]["subtype"], "setting")
        self.assertEqual(
            [entry["source"] for entry in by_title["Collaboration Panel Default Width"]["entries"]],
            [
                "Collaboration Panel Default Width",
                "Default width of the collaboration panel in pixels.",
            ],
        )

    def test_builds_dynamic_child_setting_group_with_its_own_dropdown_options(self) -> None:
        self._write_source(
            "crates/settings_content/src/theme.rs",
            "\n".join(
                [
                    "pub struct ThemeSettingsContent {",
                    "    pub theme: Option<ThemeSelection>,",
                    "}",
                    "pub enum ThemeSelection {",
                    "    Static(ThemeName),",
                    "    Dynamic {",
                    "        mode: ThemeAppearanceMode,",
                    "    },",
                    "}",
                    "pub enum ThemeAppearanceMode {",
                    "    Light,",
                    "    Dark,",
                    "    System,",
                    "}",
                    "pub struct EditPredictionSettingsContent {",
                    "    pub mode: Option<EditPredictionsMode>,",
                    "}",
                    "pub enum EditPredictionsMode {",
                    "    Subtle,",
                    "    Eager,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    settings::ThemeSelectionDiscriminants::Dynamic => vec![SettingItem {",
                    '        title: "Mode",',
                    '        description: "Choose whether to use the selected light or dark theme or to follow your OS appearance configuration.",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("theme.mode"),',
                    "            pick: |settings_content| match settings_content.theme.theme.as_ref()? {",
                    "                settings::ThemeSelection::Dynamic { mode, .. } => Some(mode),",
                    "                _ => None,",
                    "            },",
                    "        }),",
                    "        metadata: None,",
                    "    }];",
                    "}",
                ]
            ),
        )
        manifest = {
            "Mode": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Choose whether to use the selected light or dark theme or to follow your OS appearance configuration.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        4,
                        "SettingItem.description",
                        "setting_description",
                    )
                ],
            },
            "Light": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        11,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Dark": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        12,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "System": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        13,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Subtle": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        19,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Eager": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/theme.rs",
                        20,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={},
        )

        group = next(group for group in groups.settings if group.get("context_key") == "theme.mode")
        self.assertEqual(group["subtype"], "setting_with_options")
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in group["entries"]],
            [
                ("title", "Mode"),
                (
                    "description",
                    "Choose whether to use the selected light or dark theme or to follow your OS appearance configuration.",
                ),
                ("option", "Light"),
                ("option", "Dark"),
                ("option", "System"),
            ],
        )

    def test_builds_title_only_setting_group_when_dropdown_has_no_static_description(self) -> None:
        self._write_source(
            "crates/settings_content/src/workspace.rs",
            "\n".join(
                [
                    "pub struct LanguageSettingsContent {",
                    "    pub semantic_tokens: Option<SemanticTokens>,",
                    "}",
                    "pub enum SemanticTokens {",
                    "    Off,",
                    "    Combined,",
                    "    Full,",
                    "}",
                ]
            ),
        )
        self._write_source(
            "crates/settings_ui/src/page_data.rs",
            "\n".join(
                [
                    "fn page() {",
                    "    SettingsPageItem::SettingItem(SettingItem {",
                    '        title: "Semantic Tokens",',
                    "        field: Box::new(SettingField {",
                    '            json_path: Some("languages.$(language).semantic_tokens"),',
                    "        }),",
                    "        metadata: None,",
                    "    });",
                    "}",
                ]
            ),
        )
        manifest = {
            "Semantic Tokens": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_ui/src/page_data.rs",
                        3,
                        "SettingItem.title",
                        "setting_title",
                    )
                ],
            },
            "Off": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        5,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Combined": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        6,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
            "Full": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        "crates/settings_content/src/workspace.rs",
                        7,
                        "strum::VariantNames",
                        "settings_enum_variant_label",
                    )
                ],
            },
        }

        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest=manifest,
            translations={},
        )

        group = next(group for group in groups.settings if group.get("context_key") == "languages.$(language).semantic_tokens")
        self.assertEqual(group["subtype"], "setting_with_options")
        self.assertEqual(
            [(entry["role"], entry["source"]) for entry in group["entries"]],
            [
                ("title", "Semantic Tokens"),
                ("option", "Off"),
                ("option", "Combined"),
                ("option", "Full"),
            ],
        )

    def test_writes_settings_connected_line_and_prompt_component_review_reports(self) -> None:
        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest={},
            translations={},
        )
        groups.settings.append(
            {
                "id": "setting:main.rs:1",
                "type": "setting",
                "file": "main.rs",
                "start_line": 1,
                "end_line": 2,
                "context_key": "editor.line_width",
                "entries": [
                    {
                        "role": "title",
                        "source": "Line Width",
                        "kind": "setting_title",
                        "call": "SettingItem.title",
                        "line": 1,
                        "current_translation": "선 너비",
                    }
                ],
            }
        )
        groups.connected_lines.append(
            {
                "id": "connected:main.rs:10",
                "type": "connected_lines",
                "file": "main.rs",
                "start_line": 10,
                "end_line": 11,
                "joined_source": "First sentence. Second sentence.",
                "joined_current_translation": "첫 문장. 둘째 문장.",
                "entries": [
                    {
                        "role": "line",
                        "source": "First sentence.",
                        "kind": "action_description",
                        "call": "action_doc_comment",
                        "line": 10,
                        "current_translation": "첫 문장.",
                    }
                ],
            }
        )
        groups.prompt_components.append(
            {
                "id": "prompt_components:project_panel_delete_prompt:main.rs:20",
                "type": "prompt_components",
                "subtype": "project_panel_delete_prompt",
                "file": "main.rs",
                "start_line": 20,
                "end_line": 22,
                "joined_source": "Do you want to trash {message_start} {}?",
                "joined_current_translation": "휴지통으로 이동",
                "entries": [
                    {
                        "role": "message_start",
                        "source": "Do you want to trash",
                        "kind": "prompt_message",
                        "call": "delete_prompt_message_start",
                        "line": 20,
                        "current_translation": "휴지통으로 이동",
                    }
                ],
            }
        )

        write_context_group_reports(
            output_dir=self.root / "reports" / "context-groups" / "ko-KR",
            groups=groups,
        )

        settings_json = self._read_json(
            self.root / "reports" / "context-groups" / "ko-KR" / "settings-groups.json"
        )
        self.assertEqual(settings_json[0]["context_key"], "editor.line_width")
        settings_md = (
            self.root / "reports" / "context-groups" / "ko-KR" / "settings-groups.md"
        ).read_text(encoding="utf-8")
        connected_md = (
            self.root / "reports" / "context-groups" / "ko-KR" / "connected-lines.md"
        ).read_text(encoding="utf-8")
        connected_json = self._read_json(
            self.root / "reports" / "context-groups" / "ko-KR" / "connected-lines.json"
        )
        prompt_components_md = (
            self.root / "reports" / "context-groups" / "ko-KR" / "prompt-components.md"
        ).read_text(encoding="utf-8")
        prompt_components_json = self._read_json(
            self.root / "reports" / "context-groups" / "ko-KR" / "prompt-components.json"
        )
        summary = self._read_json(
            self.root / "reports" / "context-groups" / "ko-KR" / "summary.json"
        )
        self.assertIn("Line Width", settings_md)
        self.assertEqual(len(connected_json), 1)
        self.assertEqual(len(prompt_components_json), 1)
        self.assertEqual(summary["connected_lines"], 1)
        self.assertEqual(summary["prompt_components"], 1)
        self.assertIn("First sentence. Second sentence.", connected_md)
        self.assertNotIn("project_panel_delete_prompt", connected_md)
        self.assertIn("project_panel_delete_prompt", prompt_components_md)

    def test_writes_only_prompt_component_reports_for_prompt_group_type(self) -> None:
        groups = build_context_groups(
            zed_root=self.zed_root,
            manifest={},
            translations={},
        )
        groups.connected_lines.append(
            {
                "id": "connected:main.rs:10",
                "type": "connected_lines",
                "file": "main.rs",
                "start_line": 10,
                "end_line": 11,
                "joined_source": "First sentence. Second sentence.",
                "entries": [],
            }
        )
        groups.prompt_components.append(
            {
                "id": "prompt_components:project_panel_delete_prompt:main.rs:20",
                "type": "prompt_components",
                "subtype": "project_panel_delete_prompt",
                "file": "main.rs",
                "start_line": 20,
                "end_line": 22,
                "joined_source": "Do you want to trash {message_start} {}?",
                "entries": [],
            }
        )

        write_context_group_reports(
            output_dir=self.root / "reports" / "context-groups" / "ko-KR",
            groups=groups,
            group_type="prompt",
        )

        report_dir = self.root / "reports" / "context-groups" / "ko-KR"
        self.assertFalse((report_dir / "settings-groups.json").exists())
        self.assertFalse((report_dir / "connected-lines.json").exists())
        self.assertTrue((report_dir / "prompt-components.json").exists())
        summary = self._read_json(report_dir / "summary.json")
        self.assertEqual(summary["connected_lines"], 1)
        self.assertEqual(summary["prompt_components"], 1)

    def _write_source(self, relative_path: str, text: str) -> None:
        path = self.zed_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    def _occurrence(self, file: str, line: int, call: str, kind: str) -> dict[str, object]:
        return {
            "file": file,
            "line": line,
            "call": call,
            "kind": kind,
            "start_byte": 0,
            "end_byte": 0,
        }

    def _read_json(self, path: Path) -> object:
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
