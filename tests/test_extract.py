import unittest

from tools.zed_i18n.extract import extract_ui_strings_from_source


class ExtractTests(unittest.TestCase):
    def test_extracts_high_confidence_ui_string_literals(self) -> None:
        source = "\n".join(
            [
                "fn app_menus() {",
                '    MenuItem::action("Open Settings", zed_actions::OpenSettings);',
                '    Label::new("Welcome to Zed");',
                '    Button::new("save", "Save All");',
                '    Tooltip::text("Leave Call");',
                '    editor.set_placeholder_text("Search channels…", window, cx);',
                '    let id = "not visible";',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/example/src/lib.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Open Settings", "Welcome to Zed", "Save All", "Leave Call", "Search channels…"})
        self.assertEqual(by_source["Open Settings"].call, "MenuItem::action")
        self.assertEqual(by_source["Open Settings"].kind, "menu_item")
        self.assertEqual(by_source["Save All"].call, "Button::new")
        self.assertEqual(by_source["Save All"].line, 4)

    def test_skips_excluded_paths(self) -> None:
        occurrences = extract_ui_strings_from_source(
            'Label::new("Fixture Text");',
            relative_path="crates/agent/src/tools/evals/fixtures/example.rs",
        )

        self.assertEqual(occurrences, [])

        occurrences = extract_ui_strings_from_source(
            'Label::new("Test Text");',
            relative_path="crates/project_panel/src/project_panel_tests.rs",
        )

        self.assertEqual(occurrences, [])

    def test_skips_commented_out_ui_calls_in_non_doc_sources(self) -> None:
        occurrences = extract_ui_strings_from_source(
            '// div().child("notebook controls")',
            relative_path="crates/repl/src/notebook/notebook_ui.rs",
        )

        self.assertEqual(occurrences, [])

    def test_extracts_call_literals_inside_macro_token_trees(self) -> None:
        source = "\n".join(
            [
                "fn app_menus() {",
                "    vec![",
                '        MenuItem::action("Open Settings", zed_actions::OpenSettings),',
                '        MenuItem::action("Save All", workspace::SaveAll),',
                "    ];",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/zed/src/zed/app_menus.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Open Settings", "Save All"},
        )

    def test_extracts_action_doc_comments_inside_actions_macro(self) -> None:
        source = "\n".join(
            [
                "actions!(",
                "    agent,",
                "    [",
                "        /// Cycles through favorited models in the ACP model selector.",
                "        CycleFavoriteModels,",
                "        /// Opens the permission granularity dropdown for the current tool call.",
                "        #[action(name = \"OpenPermissionDropdown\")]",
                "        OpenPermissionDropdownAction,",
                "    ]",
                ");",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_ui.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Cycles through favorited models in the ACP model selector.",
                "Opens the permission granularity dropdown for the current tool call.",
            },
        )
        self.assertEqual(
            by_source["Cycles through favorited models in the ACP model selector."].kind,
            "action_description",
        )
        self.assertEqual(
            by_source["Opens the permission granularity dropdown for the current tool call."].call,
            "action_doc_comment",
        )

    def test_extracts_doc_comments_for_derive_action_structs(self) -> None:
        source = "\n".join(
            [
                "/// Action to authorize a tool call with a specific permission option.",
                "/// This is used by the permission granularity dropdown to authorize tool calls.",
                "#[derive(Clone, PartialEq, Deserialize, JsonSchema, Action)]",
                "#[action(namespace = agent)]",
                "pub struct AuthorizeToolCall {",
                "    pub tool_call_id: String,",
                "}",
                "",
                "/// A normal model doc comment.",
                "#[derive(Clone, PartialEq)]",
                "pub struct NotAnAction;",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_ui.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Action to authorize a tool call with a specific permission option.",
                "This is used by the permission granularity dropdown to authorize tool calls.",
            },
        )

    def test_extracts_action_doc_literals_from_split_structs_macro(self) -> None:
        source = "\n".join(
            [
                "macro_rules! split_structs {",
                "    ($($name:ident => $doc:literal),* $(,)?) => {",
                "        $(",
                "            #[doc = $doc]",
                "            #[derive(Clone, PartialEq, Debug, Deserialize, JsonSchema, Default, Action)]",
                "            pub struct $name;",
                "        )*",
                "    };",
                "}",
                "split_structs!(",
                '    SplitLeft => "Splits the pane to the left.",',
                '    SplitRight => "Splits the pane to the right.",',
                '    SplitVertical => "Splits the pane vertically."',
                ");",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/pane.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Splits the pane to the left.",
                "Splits the pane to the right.",
                "Splits the pane vertically.",
            },
        )
        self.assertEqual(by_source["Splits the pane to the right."].kind, "action_description")
        self.assertEqual(by_source["Splits the pane to the right."].call, "split_structs")

    def test_extracts_multiline_menu_item_actions_inside_macro_token_trees(self) -> None:
        source = "\n".join(
            [
                "fn app_menus() {",
                "    vec![",
                "        MenuItem::action(",
                '            "Open Recent...",',
                "            zed_actions::OpenRecent { create_new_window: false },",
                "        ),",
                "    ];",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/zed/src/zed/app_menus.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Open Recent..."},
        )

    def test_extracts_os_menu_item_actions(self) -> None:
        source = "\n".join(
            [
                "fn app_menus() {",
                '    MenuItem::os_action("Undo", editor::actions::Undo, OsAction::Undo);',
                '    MenuItem::os_action("Redo", editor::actions::Redo, OsAction::Redo);',
                "    MenuItem::os_action(",
                '        "Select All",',
                "        editor::actions::SelectAll,",
                "        OsAction::SelectAll,",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/zed/src/zed/app_menus.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Undo", "Redo", "Select All"})
        self.assertEqual(by_source["Undo"].call, "MenuItem::os_action")
        self.assertEqual(by_source["Undo"].kind, "menu_item")

    def test_extracts_app_menu_names_from_app_menus_only(self) -> None:
        source = "\n".join(
            [
                "fn app_menus() -> Vec<Menu> {",
                "    vec![Menu {",
                '        name: "Editor Layout".into(),',
                "        disabled: false,",
                "        items: vec![],",
                "    }]",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/zed/src/zed/app_menus.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Editor Layout"})
        self.assertEqual(by_source["Editor Layout"].call, "Menu.name")
        self.assertEqual(by_source["Editor Layout"].kind, "menu")

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/model_selector.rs",
        )

        self.assertEqual(occurrences, [])

    def test_extracts_visible_labels_when_identifier_argument_is_not_literal(self) -> None:
        source = "\n".join(
            [
                "fn render(id: SharedString) {",
                '    Button::new(id.clone(), "Trust and Continue");',
                '    Headline::new("Unrecognized Workspace");',
                '    Checkbox::new("trust-parent", ToggleState::Unselected)',
                '        .label("Trust all projects in parent directory");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/trust.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Trust and Continue",
                "Unrecognized Workspace",
                "Trust all projects in parent directory",
            },
        )
        self.assertEqual(by_source["Trust and Continue"].call, "Button::new")
        self.assertEqual(by_source["Unrecognized Workspace"].kind, "headline")
        self.assertEqual(by_source["Trust all projects in parent directory"].call, "label")

    def test_extracts_welcome_section_titles_from_static_content(self) -> None:
        source = "\n".join(
            [
                "struct SectionEntry {",
                "    title: &'static str,",
                "}",
                "const CONTENT: (Section<1>, Section<1>) = (",
                "    Section {",
                '        title: "Get Started",',
                "        entries: [",
                "            SectionEntry {",
                '                title: "Open Command Palette",',
                "            },",
                "        ],",
                "    },",
                "    Section {",
                '        title: "Configure",',
                "        entries: [",
                "            SectionEntry {",
                '                title: "Customize Keymaps",',
                "            },",
                "        ],",
                "    },",
                ");",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/welcome.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {"Get Started", "Open Command Palette", "Configure", "Customize Keymaps"},
        )
        self.assertEqual(by_source["Open Command Palette"].call, "WelcomeSection.title")
        self.assertEqual(by_source["Open Command Palette"].kind, "welcome_section_title")

    def test_extracts_agent_configuration_section_titles_and_descriptions(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                "    self.render_section_title(",
                '        "LLM Providers",',
                '        "Add at least one provider to use AI-powered features with Zed\'s native agent.",',
                "        popover_menu.into_any_element(),",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_configuration.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "LLM Providers",
                "Add at least one provider to use AI-powered features with Zed's native agent.",
            },
        )
        self.assertEqual(by_source["LLM Providers"].call, "render_section_title")
        self.assertEqual(by_source["LLM Providers"].kind, "section_title")
        self.assertEqual(
            by_source["Add at least one provider to use AI-powered features with Zed's native agent."].kind,
            "section_description",
        )

    def test_extracts_settings_page_struct_field_text(self) -> None:
        source = "\n".join(
            [
                "fn page() -> SettingsPage {",
                "    SettingsPage {",
                '        title: "Developer",',
                "        items: Box::new([",
                '            SettingsPageItem::SectionHeader("Feature Flags"),',
                "            SettingsPageItem::SettingItem(SettingItem {",
                '                title: "Project Name",',
                '                description: "The displayed name of this project.",',
                "                metadata: Some(Box::new(SettingsFieldMetadata {",
                '                    placeholder: Some("Project Name"),',
                "                })),",
                "            }),",
                "        ]),",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/page_data.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Developer",
                "Feature Flags",
                "Project Name",
                "The displayed name of this project.",
            },
        )
        self.assertEqual(by_source["Developer"].kind, "settings_page_title")
        self.assertEqual(by_source["Feature Flags"].call, "SettingsPageItem::SectionHeader")
        self.assertEqual(by_source["The displayed name of this project."].kind, "setting_description")

    def test_extracts_language_model_effort_labels(self) -> None:
        source = "\n".join(
            [
                "fn supported_effort_levels(effort: ReasoningEffort) {",
                "    vec![",
                "        language_model::LanguageModelEffortLevel {",
                '            name: "Low".into(),',
                '            value: "low".into(),',
                "            is_default: false,",
                "        },",
                "    ];",
                "    match effort {",
                '        ReasoningEffort::None => ("None", "none"),',
                '        ReasoningEffort::XHigh => ("Extra High", "xhigh"),',
                "    };",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/language_models/src/provider/open_ai.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Low", "Extra High"})
        self.assertEqual(by_source["Low"].call, "LanguageModelEffortLevel.name")
        self.assertEqual(by_source["Extra High"].call, "reasoning_effort_display")
        self.assertEqual(by_source["Extra High"].kind, "language_model_effort_label")

    def test_extracts_visible_strings_inside_ui_expression_arguments(self) -> None:
        source = "\n".join(
            [
                "fn render(copied: bool, notification_id: NotificationId, search_query: &str, cx: &mut App) {",
                '    Label::new(if copied { "Copied!" } else { "Copy" });',
                '    Label::new(format!("No settings match \\"{}\\"", search_query));',
                "    Button::new(",
                '        "cancel",',
                '        if copied { "Cancel" } else { "Dismiss" },',
                "    );",
                "    Tooltip::text(if copied {",
                '        "Show All Threads"',
                "    } else {",
                '        "Show Only Archived Threads"',
                "    });",
                '    Toast::new(notification_id.clone(), "No more matches");',
                '    StatusToast::new("No threads found to import.", cx, |this, _cx| this);',
                '    ErrorMessagePrompt::new("Couldn\'t load release notes", cx);',
                '    MessageNotification::new(format!("Updated to {app_name} {}", version), cx);',
                '    ModalHeader::new().headline("Import External Agent Threads");',
                '    SectionHeader::new("Recent Projects");',
                '    CopyButton::new("copy-error-message", message).tooltip_label("Copy Error Message");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/notifications.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Copied!",
                "Copy",
                'No settings match "{}"',
                "Cancel",
                "Dismiss",
                "Show All Threads",
                "Show Only Archived Threads",
                "No more matches",
                "No threads found to import.",
                "Couldn't load release notes",
                "Updated to {app_name} {}",
                "Import External Agent Threads",
                "Recent Projects",
                "Copy Error Message",
            },
        )
        self.assertEqual(by_source["No more matches"].kind, "toast")
        self.assertEqual(by_source["Import External Agent Threads"].call, "headline")
        self.assertEqual(by_source["Copy Error Message"].call, "tooltip_label")

    def test_extracts_prompt_callout_and_tooltip_meta_strings(self) -> None:
        source = "\n".join(
            [
                "fn render(window: &mut Window, cx: &mut App) {",
                '    window.prompt(PromptLevel::Warning, "Discard changes?", Some("This cannot be undone."), &["Discard", "Cancel"], cx);',
                "    Callout::new()",
                '        .title("Authentication Required")',
                '        .description("Sign in again to continue.");',
                '    ModalHeader::new().description("Choose which agents to include.");',
                '    Tooltip::with_meta("Locked File", None, "This file is read-only", cx);',
                '    Tooltip::for_action_title("Switch Branch", &SwitchBranch);',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/pane.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Discard changes?",
                "This cannot be undone.",
                "Discard",
                "Cancel",
                "Authentication Required",
                "Sign in again to continue.",
                "Choose which agents to include.",
                "Locked File",
                "This file is read-only",
                "Switch Branch",
            },
        )
        self.assertEqual(by_source["Discard changes?"].kind, "prompt_message")
        self.assertEqual(by_source["Discard"].kind, "prompt_answer")
        self.assertEqual(by_source["Authentication Required"].call, "title")
        self.assertEqual(by_source["This file is read-only"].kind, "tooltip_meta")

    def test_extracts_direct_shared_string_literals_as_review_candidates(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                '    let model = SharedString::from("Select a Model");',
                '    let call = SharedString::new("Current Call");',
                '    let label = SharedString::new_static("Offline");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_model_selector.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Select a Model", "Current Call", "Offline"})
        self.assertEqual(by_source["Select a Model"].kind, "shared_string")

    def test_extracts_context_menu_actions_and_action_tooltips(self) -> None:
        source = "\n".join(
            [
                "fn render(menu: ContextMenu, cx: &mut App) {",
                '    menu.action("New Terminal", Box::new(NewTerminal::default()))',
                '        .action("Spawn Task", Box::new(SpawnTask));',
                '    menu.action_disabled_when(!has_git_repo, "Copy Permalink", Box::new(CopyPermalinkToLine));',
                '    Tooltip::for_action("Project Diagnostics", &Deploy, cx);',
                '    Tooltip::for_action(if zoomed { "Zoom Out" } else { "Zoom In" }, &ToggleZoom, cx);',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/pane.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "New Terminal",
                "Spawn Task",
                "Copy Permalink",
                "Project Diagnostics",
                "Zoom Out",
                "Zoom In",
            },
        )
        self.assertEqual(by_source["New Terminal"].kind, "context_menu_action")
        self.assertEqual(by_source["Copy Permalink"].call, "action_disabled_when")
        self.assertEqual(by_source["Project Diagnostics"].call, "Tooltip::for_action")

    def test_extracts_context_menu_entries_and_headers(self) -> None:
        source = "\n".join(
            [
                "fn render(menu: ContextMenu, request: RequestBuilder) {",
                '    menu.header("Current Thread")',
                '        .submenu("Panel Layout", |menu, _, _| menu)',
                '        .submenu_with_icon("Autofill", IconName::Wand, |menu, _, _| menu)',
                '        .item(ContextMenuEntry::new("New From Summary"))',
                '        .separator()',
                '        .header("External Agents");',
                '    request.header("Content-Type", "application/json");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_panel.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Current Thread",
                "Panel Layout",
                "Autofill",
                "New From Summary",
                "External Agents",
            },
        )
        self.assertEqual(by_source["New From Summary"].call, "ContextMenuEntry::new")
        self.assertEqual(by_source["New From Summary"].kind, "context_menu_entry")
        self.assertEqual(by_source["Current Thread"].kind, "context_menu_header")
        self.assertEqual(by_source["Panel Layout"].kind, "context_menu_submenu")

    def test_extracts_tooltip_and_link_helper_labels(self) -> None:
        source = "\n".join(
            [
                "fn render(cx: &mut App) {",
                '    Tooltip::simple("No Changes to Commit", cx);',
                '    Tooltip::new("Previous Alternative").key_binding("ctrl-up");',
                '    LoadingLabel::new("Awaiting Confirmation");',
                '    ButtonLink::new("OpenAI\'s console", "https://platform.openai.com/api-keys");',
                '    ProfileModalHeader::new("Agent Profiles", None);',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_configuration.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "No Changes to Commit",
                "Previous Alternative",
                "Awaiting Confirmation",
                "OpenAI's console",
                "Agent Profiles",
            },
        )
        self.assertEqual(by_source["No Changes to Commit"].call, "Tooltip::simple")
        self.assertEqual(by_source["Previous Alternative"].call, "Tooltip::new")
        self.assertEqual(by_source["OpenAI's console"].kind, "button_link")

    def test_extracts_notification_link_and_card_button_labels(self) -> None:
        source = "\n".join(
            [
                "fn render(cx: &mut App) {",
                '    ConfiguredApiCard::new("Authorized").button_label("Sign Out");',
                '    ErrorMessagePrompt::new(err.to_string(), cx).with_link_button("See docs", docs_url);',
                '    prompt.with_link_button("View in Browser".to_string(), url);',
                '    MessageNotification::new("Failed to load the database file.", cx)',
                '        .primary_message("File an Issue")',
                '        .secondary_message("Don\'t Show Again");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/notifications.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Authorized",
                "Sign Out",
                "See docs",
                "View in Browser",
                "Failed to load the database file.",
                "File an Issue",
                "Don't Show Again",
            },
        )
        self.assertEqual(by_source["Authorized"].call, "ConfiguredApiCard::new")
        self.assertEqual(by_source["Sign Out"].call, "button_label")
        self.assertEqual(by_source["See docs"].call, "with_link_button")
        self.assertEqual(by_source["File an Issue"].kind, "notification_message")

    def test_extracts_dropdown_labels_and_tab_titles(self) -> None:
        source = "\n".join(
            [
                "fn render(menu: Entity<ContextMenu>) {",
                '    DropdownMenu::new("failure-mode-dropdown", "Issue", menu);',
                '    InputField::new(window, cx, "Type an action name").label("Action");',
                "}",
                "impl Item for Onboarding {",
                "    fn tab_content_text(&self, _detail: usize, _cx: &App) -> SharedString {",
                '        "Onboarding".into()',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/onboarding/src/onboarding.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Issue", "Type an action name", "Action", "Onboarding"})
        self.assertEqual(by_source["Issue"].call, "DropdownMenu::new")
        self.assertEqual(by_source["Type an action name"].call, "InputField::new")
        self.assertEqual(by_source["Onboarding"].kind, "tab_title")

    def test_extracts_copilot_sign_in_status_messages(self) -> None:
        source = "\n".join(
            [
                'const ERROR_LABEL: &str =',
                '    "Copilot had issues starting. You can try reinstalling it and signing in again."; ',
                "fn initiate_sign_out(window: &Window, cx: &mut App) {",
                '    copilot_toast(Some("Signing out of Copilot…"), window, cx);',
                "}",
                "fn loading_message(&self) -> Option<SharedString> {",
                '    Some("Starting Copilot…".into())',
                "}",
                "fn render_for_edit_prediction(&self) {",
                '    let start_label = "To use Copilot for edit predictions, you need to be logged in to GitHub.".into();',
                '    let no_status_label = "Copilot requires an active GitHub Copilot subscription.".into();',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/copilot_ui/src/sign_in.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Copilot had issues starting. You can try reinstalling it and signing in again.",
                "Signing out of Copilot…",
                "Starting Copilot…",
                "To use Copilot for edit predictions, you need to be logged in to GitHub.",
                "Copilot requires an active GitHub Copilot subscription.",
            },
        )

    def test_extracts_direct_children_menu_links_and_documentation_asides(self) -> None:
        source = "\n".join(
            [
                "fn render(menu: ContextMenu, cx: &mut App) {",
                '    div().child("Could not open file");',
                "    menu.link(",
                '        "Go to Copilot Settings",',
                "        OpenBrowser { url }.boxed_clone(),",
                "    );",
                "    menu.link_with_handler(",
                '        "Learn More",',
                "        OpenBrowser { url }.boxed_clone(),",
                "        |_, _| {},",
                "    );",
                '    ContextMenuEntry::new("Training Data Collection")',
                "        .documentation_aside(DocumentationSide::Left, move |cx| {",
                "            let (msg, color) = match enabled {",
                '                true => ("Project identified as open source, and you\'re sharing data.", Color::Default),',
                '                false => ("Project not identified as open source. No data captured.", Color::Muted),',
                "            };",
                "            v_flex()",
                "                .child(Label::new(indoc!{",
                '                    "Help us improve our open dataset model by sharing data from open source repositories."',
                "                }))",
                "                .child(div().child(msg))",
                "        });",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/edit_prediction_ui/src/edit_prediction_button.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Could not open file",
                "Go to Copilot Settings",
                "Learn More",
                "Training Data Collection",
                "Project identified as open source, and you're sharing data.",
                "Project not identified as open source. No data captured.",
                "Help us improve our open dataset model by sharing data from open source repositories.",
            },
        )

    def test_extracts_switch_field_labels_and_descriptions(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                "    SwitchField::new(",
                '        "onboarding-vim-mode",',
                '        Some("Vim Mode"),',
                '        Some("Coming from Neovim? Use our first-class implementation of Vim Mode".into()),',
                "        toggle_state,",
                "        move |_, _, _| {},",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/onboarding/src/basics_page.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Vim Mode",
                "Coming from Neovim? Use our first-class implementation of Vim Mode",
            },
        )

    def test_extracts_settings_action_links_and_optional_descriptions(self) -> None:
        source = "\n".join(
            [
                "fn page() {",
                "    SettingsPageItem::ActionLink(ActionLink {",
                '        title: "Audio Test".into(),',
                '        description: Some("Test your microphone and speaker setup".into()),',
                '        button_text: "Test Audio".into(),',
                "    });",
                "    SettingsPageItem::SubPageLink(SubPageLink {",
                '        title: "Tool Permissions".into(),',
                '        description: Some("Set up regex patterns to auto-allow, auto-deny, or always request confirmation, for specific tool inputs.".into()),',
                "    });",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/page_data.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Audio Test",
                "Test your microphone and speaker setup",
                "Test Audio",
                "Tool Permissions",
                "Set up regex patterns to auto-allow, auto-deny, or always request confirmation, for specific tool inputs.",
            },
        )

    def test_extracts_activity_indicator_content_messages(self) -> None:
        source = "\n".join(
            [
                "fn content() -> Content {",
                "    Content {",
                '        message: format!("Downloading {}...", name),',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/activity_indicator/src/activity_indicator.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Downloading {}..."})
        self.assertEqual(by_source["Downloading {}..."].call, "Content.message")

    def test_extracts_activity_indicator_dynamic_status_messages(self) -> None:
        source = "\n".join(
            [
                "fn status() {",
                '    write!(&mut message, " + {} more", additional_work_count).unwrap();',
                '    let warning = format!("({server_name}) Warning: ");',
                '    let installing = format!("Installing {extension_id} extension…");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/activity_indicator/src/activity_indicator.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                " + {} more",
                "({server_name}) Warning: ",
                "Installing {extension_id} extension…",
            },
        )

    def test_content_message_rule_is_scoped_to_activity_indicator(self) -> None:
        source = "\n".join(
            [
                "fn content() -> Content {",
                "    Content {",
                '        message: "protocol payload".to_string(),',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/context_server/src/client.rs",
        )

        self.assertEqual(occurrences, [])

    def test_extracts_picker_placeholder_and_no_matches_text(self) -> None:
        source = "\n".join(
            [
                "impl PickerDelegate for RecentProjectsDelegate {",
                "    fn placeholder_text(&self, _window: &mut Window, _cx: &mut App) -> Arc<str> {",
                '        "Search projects…".into()',
                "    }",
                "    fn no_matches_text(&self, _window: &mut Window, _cx: &mut App) -> Option<SharedString> {",
                "        let text = if self.workspaces.is_empty() {",
                '            "Recently opened projects will show up here"',
                "        } else {",
                '            "No matches"',
                "        };",
                "        Some(text.into())",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/recent_projects/src/recent_projects.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Search projects…",
                "Recently opened projects will show up here",
                "No matches",
            },
        )

    def test_extracts_input_helpers(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                '    SettingsInputField::new().with_placeholder("Add regex pattern…");',
                '    div().child(input_output_header("Raw Input:".into()));',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/pages/tool_permissions_setup.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Add regex pattern…", "Raw Input:"})
        self.assertEqual(by_source["Add regex pattern…"].call, "with_placeholder")
        self.assertEqual(by_source["Raw Input:"].call, "input_output_header")

    def test_extracts_project_picker_headers(self) -> None:
        source = "\n".join(
            [
                "fn update_matches(&mut self) {",
                '    entries.push(ProjectPickerEntry::Header("This Window".into()));',
                '    entries.push(ProjectPickerEntry::Header("Recent Projects".into()));',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/recent_projects/src/recent_projects.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"This Window", "Recent Projects"})
        self.assertEqual(by_source["This Window"].kind, "project_picker_header")

    def test_extracts_search_option_tooltip_labels(self) -> None:
        source = "\n".join(
            [
                "impl SearchOption {",
                "    pub fn label(&self) -> &'static str {",
                "        match self {",
                '            SearchOption::WholeWord => "Match Whole Words",',
                '            SearchOption::CaseSensitive => "Match Case Sensitivity",',
                '            SearchOption::Regex => "Use Regular Expressions",',
                "        }",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/search/src/search.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Match Whole Words",
                "Match Case Sensitivity",
                "Use Regular Expressions",
            },
        )
        self.assertEqual(by_source["Match Whole Words"].call, "SearchOption.label")

    def test_extracts_platform_reveal_in_file_manager_labels(self) -> None:
        source = "\n".join(
            [
                "pub fn reveal_in_file_manager_label(is_remote: bool) -> &'static str {",
                '    if cfg!(target_os = "macos") && !is_remote {',
                '        "Reveal in Finder"',
                '    } else if cfg!(target_os = "windows") && !is_remote {',
                '        "Reveal in File Explorer"',
                "    } else {",
                '        "Reveal in File Manager"',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/ui/src/utils.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Reveal in Finder",
                "Reveal in File Explorer",
                "Reveal in File Manager",
            },
        )
        self.assertEqual(
            by_source["Reveal in File Explorer"].call,
            "reveal_in_file_manager_label",
        )

    def test_extracts_workspace_pane_tab_tooltips(self) -> None:
        source = "\n".join(
            [
                "fn render_tab() {",
                '    end_slot_tooltip_text = "Unpin Tab";',
                '    end_slot_tooltip_text = "Close Tab";',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/pane.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Unpin Tab", "Close Tab"})
        self.assertEqual(by_source["Close Tab"].kind, "tab_tooltip")

    def test_extracts_workspace_pane_dirty_buffer_prompt(self) -> None:
        source = "\n".join(
            [
                "fn dirty_message_for(buffer_path: Option<ProjectPath>, path_style: PathStyle) -> String {",
                '    const CONFLICT_MESSAGE: &str = "This file has changed on disk since you started editing it. Do you want to overwrite it?";',
                '    const DELETED_MESSAGE: &str = "This file has been deleted on disk since you started editing it. Do you want to recreate it?";',
                '    format!("{path} contains unsaved edits. Do you want to save it?")',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/pane.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "This file has changed on disk since you started editing it. Do you want to overwrite it?",
                "This file has been deleted on disk since you started editing it. Do you want to recreate it?",
                "{path} contains unsaved edits. Do you want to save it?",
            },
        )
        self.assertEqual(
            by_source["{path} contains unsaved edits. Do you want to save it?"].kind,
            "prompt_message",
        )

    def test_extracts_project_empty_state_panel_labels(self) -> None:
        source = "\n".join(
            [
                "fn render_empty_state(focus_handle: FocusHandle, cx: &mut App) {",
                "    ProjectEmptyState::new(",
                '        "Project Panel",',
                "        focus_handle.clone(),",
                "        KeyBinding::for_action(&workspace::Open::default(), cx),",
                "    );",
                '    ProjectEmptyState::new("Threads Sidebar", focus_handle, key_binding);',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/project_panel/src/project_panel.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Project Panel", "Threads Sidebar"})
        self.assertEqual(by_source["Project Panel"].kind, "project_empty_state_label")
        self.assertEqual(by_source["Threads Sidebar"].call, "ProjectEmptyState::new")

    def test_extracts_project_panel_unsaved_delete_warnings(self) -> None:
        source = "\n".join(
            [
                "fn delete_prompt(dirty_buffers: usize) {",
                '    let prompt = format!("Discard changes to {}?", file_name);',
                "    let message_start = if trash {",
                '        "Do you want to trash"',
                "    } else {",
                '        "Are you sure you want to permanently delete"',
                "    };",
                "    let single = if dirty_buffers > 0 {",
                '        "\\n\\nIt has unsaved changes, which will be lost."',
                "    } else {",
                '        ""',
                "    };",
                "    format!(",
                '        "{message_start} {}?{unsaved_warning}",',
                "        MarkdownInlineCode(path)",
                "    );",
                "    let many = if dirty_buffers == 1 {",
                '        "\\n\\n1 of these has unsaved changes, which will be lost.".to_string()',
                "    } else {",
                "        format!(",
                '            "\\n\\n{dirty_buffers} of these have unsaved changes, which will be lost."',
                "        )",
                "    };",
                '    paths.push(".. 1 file not shown".into());',
                '    paths.push(format!(".. {} files not shown", truncated_path_counts));',
                "    format!(",
                '        "{message_start} the following {} files?\\n{}{unsaved_warning}",',
                "        file_paths.len(),",
                "        names.join(\"\\n\")",
                "    );",
                '    let detail = (!trash).then_some("This cannot be undone.");',
                "    let prompt_message = format!(",
                "        concat!(",
                '            "A file or folder with name {} ",',
                '            "already exists in the destination folder. ",',
                '            "Do you want to replace it?"',
                "        ),",
                "        filename",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/project_panel/src/project_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "A file or folder with name {} ",
                "Do you want to trash",
                "Are you sure you want to permanently delete",
                "Discard changes to {}?",
                "already exists in the destination folder. ",
                "Do you want to replace it?",
                "{message_start} {}?{unsaved_warning}",
                "{message_start} the following {} files?\n{}{unsaved_warning}",
                "\n\nIt has unsaved changes, which will be lost.",
                "\n\n1 of these has unsaved changes, which will be lost.",
                "\n\n{dirty_buffers} of these have unsaved changes, which will be lost.",
                ".. 1 file not shown",
                ".. {} files not shown",
                "This cannot be undone.",
            },
        )

    def test_extracts_agent_dirty_buffer_permission_messages(self) -> None:
        source = "\n".join(
            [
                "fn authorize_dirty_buffer(kind: DirtyBufferPromptKind) {",
                "    let (message, options) = match kind {",
                "        DirtyBufferPromptKind::Edit => (",
                '            "This file has unsaved changes. Do you want to save or discard them \\',
                '             before the agent continues editing?"',
                "                .to_string(),",
                "            vec![],",
                "        ),",
                "        DirtyBufferPromptKind::Overwrite => (",
                '            "This file has unsaved changes and the agent wants to overwrite it.".to_string(),',
                "            vec![],",
                "        ),",
                "    };",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent/src/tools/tool_permissions.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "This file has unsaved changes. Do you want to save or discard them before the agent continues editing?",
                "This file has unsaved changes and the agent wants to overwrite it.",
            },
        )

    def test_extracts_tool_permission_tool_info_strings(self) -> None:
        source = "\n".join(
            [
                'const HARDCODED_RULES_DESCRIPTION: &str =',
                '    "`rm -rf` commands are always blocked";',
                'const SETTINGS_DISCLAIMER: &str = "Note: custom tool permissions only apply to the Zed native agent.";',
                "const TOOLS: &[ToolInfo] = &[",
                "    ToolInfo {",
                '        id: "terminal",',
                '        name: "Terminal",',
                '        description: "Commands executed in the terminal",',
                '        regex_explanation: "Patterns are matched against each command in the input.",',
                "    },",
                "];",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/pages/tool_permissions_setup.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "`rm -rf` commands are always blocked",
                "Note: custom tool permissions only apply to the Zed native agent.",
                "Terminal",
                "Commands executed in the terminal",
                "Patterns are matched against each command in the input.",
            },
        )
        self.assertEqual(by_source["Terminal"].kind, "tool_permission_tool_name")
        self.assertEqual(
            by_source["Patterns are matched against each command in the input."].call,
            "ToolInfo.regex_explanation",
        )

    def test_extracts_tool_permission_rule_section_strings(self) -> None:
        source = "\n".join(
            [
                'parts.push("1 rule".to_string());',
                'parts.push(format!("{} rules", rule_count));',
                'parts.push(format!("{} invalid", invalid_count));',
                "render_rule_section(",
                '    "terminal",',
                '    "Always Deny",',
                '    "If any of these regexes match, the tool action will be denied.",',
                "    ToolPermissionMode::Deny,",
                ");",
                'ToolPermissionMode::Deny => ("Always Deny", Color::Error),',
                '"always_deny" => "Always Deny",',
                'Some(',
                '    "A pattern with that name already exists in this rule list."',
                '        .to_string(),',
                ')',
                'format!("Invalid regex: {err}. Pattern saved but will block this tool until fixed or removed.")',
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/pages/tool_permissions_setup.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "1 rule",
                "{} rules",
                "{} invalid",
                "Always Deny",
                "If any of these regexes match, the tool action will be denied.",
                "A pattern with that name already exists in this rule list.",
                "Invalid regex: {err}. Pattern saved but will block this tool until fixed or removed.",
            },
        )
        always_deny_kinds = {
            occurrence.kind for occurrence in occurrences if occurrence.source == "Always Deny"
        }
        self.assertIn("tool_permission_rule_section_title", always_deny_kinds)
        self.assertIn("tool_permission_rule_type_label", always_deny_kinds)
        self.assertEqual(
            by_source["If any of these regexes match, the tool action will be denied."].kind,
            "tool_permission_rule_section_description",
        )

    def test_extracts_settings_enum_variant_dropdown_labels(self) -> None:
        source = "\n".join(
            [
                "#[derive(",
                "    Clone,",
                "    strum::VariantArray,",
                "    strum::VariantNames,",
                ")]",
                "pub enum ThinkingBlockDisplay {",
                "    Auto,",
                "    Preview,",
                "    AlwaysExpanded,",
                '    #[strum(serialize = "Custom Label")]',
                "    CustomLabel,",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_content/src/agent.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {"Auto", "Preview", "Always Expanded", "Custom Label"},
        )
        self.assertEqual(by_source["Always Expanded"].kind, "settings_enum_variant_label")
        self.assertEqual(by_source["Custom Label"].line, 10)

    def test_extracts_settings_enum_labels_with_zed_dropdown_title_case(self) -> None:
        source = "\n".join(
            [
                "#[derive(",
                "    strum::VariantArray,",
                "    strum::VariantNames,",
                ")]",
                "pub enum EditPredictionPromptFormatContent {",
                "    Zeta2_1,",
                "    CodeGemma,",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_content/src/language.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Zeta2 1", "Code Gemma"},
        )

    def test_extracts_settings_enum_discriminant_dropdown_labels(self) -> None:
        source = "\n".join(
            [
                "#[derive(",
                "    Clone,",
                "    strum::EnumDiscriminants,",
                ")]",
                "#[strum_discriminants(derive(strum::VariantArray, strum::VariantNames))]",
                "pub enum AutosaveSetting {",
                "    Off,",
                "    AfterDelay { milliseconds: DelayMs },",
                '    #[strum_discriminants(strum(serialize = "On Window Change"))]',
                "    OnWindowChange,",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_content/src/workspace.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Off", "After Delay", "On Window Change"})
        self.assertEqual(by_source["After Delay"].kind, "settings_enum_discriminant_label")
        self.assertEqual(by_source["On Window Change"].line, 9)

    def test_extracts_tool_permission_display_labels(self) -> None:
        source = "\n".join(
            [
                "impl std::fmt::Display for ToolPermissionMode {",
                "    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {",
                "        match self {",
                '            ToolPermissionMode::Allow => write!(f, "Allow"),',
                '            ToolPermissionMode::Deny => write!(f, "Deny"),',
                '            ToolPermissionMode::Confirm => write!(f, "Confirm"),',
                "        }",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_content/src/agent.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Allow", "Deny", "Confirm"})
        self.assertEqual(by_source["Confirm"].call, "ToolPermissionMode.display")

    def test_extracts_agent_message_editor_placeholder(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                "    MessageEditor::new(",
                '        "Edit message － @ to include context",',
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/entry_view_state.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Edit message － @ to include context"},
        )

    def test_extracts_toggleable_entries_and_tooltip_format_bindings(self) -> None:
        source = "\n".join(
            [
                "fn render(menu: ContextMenu, dock: Dock) {",
                '    menu.toggleable_entry("Vim Mode", enabled, IconPosition::Start, None, move |_, _| {});',
                '    menu.toggleable_entry(format!("Dock {}", dock.position.label()), selected, IconPosition::Start, None, move |_, _| {});',
                "    let (action, tooltip) = if active {",
                "        let action = dock.toggle_action();",
                '        let tooltip: SharedString = format!("Close {} Dock", dock.position.label()).into();',
                "        (action, tooltip)",
                "    } else {",
                "        (entry.panel.toggle_action(window, cx), icon_tooltip.into())",
                "    };",
                "    let focus_handle = dock.focus_handle(cx);",
                "    let icon_label = entry.panel.icon_label(window, cx);",
                '    IconButton::new("close-dock", IconName::Close).tooltip(Tooltip::for_action(tooltip.clone(), &*action, cx));',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/dock.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Vim Mode", "Dock {}", "Close {} Dock"},
        )

    def test_extracts_dock_position_labels_used_in_dynamic_tooltips(self) -> None:
        source = "\n".join(
            [
                "impl DockPosition {",
                "    fn label(&self) -> &'static str {",
                "        match self {",
                '            Self::Left => "Left",',
                '            Self::Bottom => "Bottom",',
                '            Self::Right => "Right",',
                "        }",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/workspace/src/dock.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Left", "Bottom", "Right"},
        )

    def test_extracts_keybinding_hint_suffixes(self) -> None:
        source = "\n".join(
            [
                "fn render(focused: bool, cx: &mut App) {",
                "    let focus_keybind_label = if focused {",
                '        "Focus Content"',
                "    } else {",
                '        "Focus Navbar"',
                "    };",
                "    KeybindingHint::new(kb, bg).suffix(focus_keybind_label);",
                '    KeybindingHint::new(close_kb, bg).suffix("Cancel");',
                '    tempfile::Builder::new().suffix(".png");',
                '    "ignored".strip_suffix("ed");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/settings_ui.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Focus Content", "Focus Navbar", "Cancel"},
        )

    def test_extracts_git_diff_titles_and_paths(self) -> None:
        multi_diff_source = "\n".join(
            [
                "impl MultiDiffView {",
                "    fn title(&self) -> SharedString {",
                "        let suffix = if self.file_count == 1 {",
                '            "1 file".to_string()',
                "        } else {",
                '            format!("{} files", self.file_count)',
                "        };",
                '        format!("Diff ({suffix})").into()',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            multi_diff_source,
            relative_path="crates/git_ui/src/multi_diff_view.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"1 file", "{} files", "Diff ({suffix})"},
        )

        text_diff_source = "\n".join(
            [
                "fn new() -> Self {",
                "    Self {",
                '        title: format!("Clipboard ↔ {selection_location_title}").into(),',
                '        path: Some(format!("Clipboard ↔ {selection_location_path}").into()),',
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            text_diff_source,
            relative_path="crates/git_ui/src/text_diff_view.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Clipboard ↔ {selection_location_title}",
                "Clipboard ↔ {selection_location_path}",
            },
        )

    def test_extracts_inline_prompt_dynamic_tooltips(self) -> None:
        source = "\n".join(
            [
                "impl GenerationMode {",
                "    fn tooltip_interrupt(self) -> &'static str {",
                "        match self {",
                '            GenerationMode::Generate => "Interrupt Generation",',
                '            GenerationMode::Transform => "Interrupt Transform",',
                "        }",
                "    }",
                "}",
                "fn render(mode: GenerationMode, cx: &mut App) {",
                "    Tooltip::with_meta(",
                "        mode.tooltip_interrupt(),",
                "        Some(&menu::Cancel),",
                "        \"Changes won't be discarded\",",
                "        cx,",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/inline_prompt_editor.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Interrupt Generation",
                "Interrupt Transform",
                "Changes won't be discarded",
            },
        )

    def test_extracts_language_selector_current_suffix(self) -> None:
        occurrences = extract_ui_strings_from_source(
            'label.push_str(" (current)");',
            relative_path="crates/language_selector/src/language_selector.rs",
        )

        self.assertEqual({occurrence.source for occurrence in occurrences}, {" (current)"})

    def test_extracts_rust_task_template_labels(self) -> None:
        source = "\n".join(
            [
                "fn templates() {",
                "    TaskTemplate {",
                "        label: format!(",
                '            "Check (package: {})",',
                "            RUST_PACKAGE_TASK_VARIABLE.template_value(),",
                "        ),",
                "    };",
                "    TaskTemplate {",
                '        label: "Clean".into(),',
                "    };",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/languages/src/rust.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Check (package: {})", "Clean"},
        )

    def test_extracts_git_prompts_tabs_and_remote_statuses(self) -> None:
        git_panel_source = "\n".join(
            [
                "fn render(window: &mut Window, cx: &mut Context<Self>) {",
                '    let prompt = prompt("Trash these files?", Some(&details), window, cx);',
                "    let prompt = window.prompt(",
                "        PromptLevel::Warning,",
                '        &format!("Are you sure you want to discard changes to {}?", path),',
                "        None,",
                '        &["Discard Changes", "Cancel"],',
                "        cx,",
                "    );",
                "    picker_prompt::prompt(",
                '        "Pick which remote to fetch",',
                "        remotes,",
                "        workspace,",
                "        window,",
                "        cx,",
                "    );",
                '    let (tooltip_label, icon) = ("Add co-authored-by", IconName::UserCheck);',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            git_panel_source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Trash these files?",
                "Are you sure you want to discard changes to {}?",
                "Discard Changes",
                "Cancel",
                "Pick which remote to fetch",
                "Add co-authored-by",
            },
        )

        remote_output_source = "\n".join(
            [
                "fn format_output() {",
                '    SuccessMessage { message: "Fetch: Already up to date".into(), style };',
                '    let message = format!("Synchronized with {}", remote.name);',
                '    let message = "Push: Everything is up-to-date".to_string();',
                '    let pr_hints = [("Create a pull request", "Create Pull Request")];',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            remote_output_source,
            relative_path="crates/git_ui/src/remote_output.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Fetch: Already up to date",
                "Synchronized with {}",
                "Push: Everything is up-to-date",
                "Create Pull Request",
            },
        )

    def test_extracts_git_picker_and_commit_fallbacks(self) -> None:
        self.assertEqual(
            {
                occurrence.source
                for occurrence in extract_ui_strings_from_source(
                    'GitPickerTab::Branches => "Branches",\nGitPickerTab::Stash => "Stash",',
                    relative_path="crates/git_ui/src/git_picker.rs",
                )
            },
            {"Branches", "Stash"},
        )

        self.assertEqual(
            {
                occurrence.source
                for occurrence in extract_ui_strings_from_source(
                    'blame.author.unwrap_or("<no name>".to_string());\nmessage.unwrap_or("<no commit message>".into_any());',
                    relative_path="crates/git_ui/src/commit_tooltip.rs",
                )
            },
            {"<no name>", "<no commit message>"},
        )

    def test_extracts_keymap_empty_states_headers_and_warnings(self) -> None:
        source = "\n".join(
            [
                "fn render_no_matches_hint(&self) {",
                '    "No conflicting keybinds found"',
                '    "No matches found for the provided query"',
                "}",
                'Table::new(COLS).header(vec!["", "Action", "Arguments", "Keystrokes", "Context", "Source"]);',
                ".map(add_filter(",
                '    "No Action",',
                "));",
                'anyhow::ensure!(!new_keystrokes.is_empty(), "Keystrokes cannot be empty");',
                'parse(&context).context("Failed to parse key context")?;',
                'format!("Your keybind would conflict with the \\"{}\\" action", name);',
                '"Your keybind would conflict with other actions".to_string();',
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/keymap_editor/src/keymap_editor.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "No conflicting keybinds found",
                "No matches found for the provided query",
                "Action",
                "Arguments",
                "Keystrokes",
                "Context",
                "Source",
                "No Action",
                "Keystrokes cannot be empty",
                "Failed to parse key context",
                'Your keybind would conflict with the "{}" action',
                "Your keybind would conflict with other actions",
            },
        )

    def test_unwrap_or_fallbacks_are_scoped_to_placeholders(self) -> None:
        source = "\n".join(
            [
                "fn render(name: Option<&str>, provider: Option<SharedString>, suggested: Option<SharedString>) {",
                '    div().child(name.unwrap_or("<no name>").to_string());',
                '    DropdownMenu::new("provider", provider.unwrap_or("No provider set".into()), None);',
                '    let placeholder_text = suggested.unwrap_or("Enter commit message".into());',
                "    editor.set_placeholder_text(&placeholder_text, window, cx);",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Enter commit message"},
        )

    def test_extracts_panel_icon_tooltips(self) -> None:
        source = "\n".join(
            [
                "impl Panel for GitPanel {",
                "    fn icon_tooltip(&self, _window: &Window, _cx: &App) -> Option<&'static str> {",
                '        Some("Git Panel")',
                "    }",
                "}",
                "impl Panel for DebuggerPanel {",
                "    fn icon_tooltip(&self, _window: &Window, cx: &App) -> Option<&'static str> {",
                "        if enabled(cx) {",
                '            Some("Debug Panel")',
                "        } else {",
                "            None",
                "        }",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Git Panel", "Debug Panel"})
        self.assertEqual(by_source["Git Panel"].call, "icon_tooltip")
        self.assertEqual(by_source["Git Panel"].kind, "panel_tooltip")

    def test_extracts_settings_user_file_display_name(self) -> None:
        source = "\n".join(
            [
                "impl SettingsWindow {",
                "    pub(crate) fn display_name(&self, file: &SettingsUiFile) -> Option<String> {",
                "        match file {",
                '            SettingsUiFile::User => Some("User".to_string()),',
                '            SettingsUiFile::Project(_) => Some("{}{}{}".to_string()),',
                "        }",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/settings_ui.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"User"},
        )

    def test_local_tuple_binding_resolution_uses_matching_element_only(self) -> None:
        source = "\n".join(
            [
                "fn render(is_busy: bool) {",
                "    let (button_id, button_label) = if is_busy {",
                '        ("connect", "Connecting…")',
                "    } else {",
                '        ("sign_in", "Sign In with GitHub")',
                "    };",
                "    Button::new(button_id, button_label);",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/collab_ui/src/collab_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"Connecting…", "Sign In with GitHub"},
        )

    def test_extracts_git_panel_dynamic_labels(self) -> None:
        source = "\n".join(
            [
                "impl GitHeaderEntry {",
                "    pub fn title(&self) -> &'static str {",
                "        match self.header {",
                '            Section::Conflict => "Conflicts",',
                '            Section::Tracked => "Tracked",',
                '            Section::New => "Untracked",',
                "        }",
                "    }",
                "}",
                "impl GitPanel {",
                "    pub fn configure_commit_button(&self, cx: &mut Context<Self>) -> (bool, &'static str) {",
                "        if self.has_unstaged_conflicts() {",
                '            (false, "You must resolve conflicts before committing")',
                "        } else if !self.has_staged_changes() {",
                '            (false, "No changes to commit")',
                "        } else if self.pending_commit.is_some() {",
                '            (false, "Commit in progress")',
                "        } else if !self.has_commit_message(cx) {",
                '            (false, "No commit message")',
                "        } else {",
                "            (true, self.commit_button_title())",
                "        }",
                "    }",
                "    pub fn commit_button_title(&self) -> &'static str {",
                "        if self.amend_pending {",
                '            "Amend Tracked"',
                "        } else {",
                '            "Commit Tracked"',
                "        }",
                "    }",
                "    fn render_panel_header(&self) {",
                "        let (text, action, stage, tooltip) = if all_staged {",
                '            ("Unstage All", UnstageAll.boxed_clone(), false, "git reset")',
                "        } else {",
                '            ("Stage All", StageAll.boxed_clone(), true, "git add --all")',
                "        };",
                "        let change_string = match self.changes_count {",
                '            0 => "No Changes".to_string(),',
                '            1 => "1 Change".to_string(),',
                '            count => format!("{} Changes", count),',
                "        };",
                "        panel_button(change_string);",
                "        panel_filled_button(text);",
                "        Tooltip::for_action_title_in(tooltip, action.as_ref(), &self.focus_handle);",
                "    }",
                "    fn set_placeholder(&self, suggested_commit_message: Option<SharedString>) {",
                '        let placeholder_text = suggested_commit_message.unwrap_or("Enter commit message".into());',
                "        editor.set_placeholder_text(&placeholder_text, window, cx);",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Conflicts",
                "Tracked",
                "Untracked",
                "You must resolve conflicts before committing",
                "No changes to commit",
                "Commit in progress",
                "No commit message",
                "Amend Tracked",
                "Commit Tracked",
                "Unstage All",
                "Stage All",
                "git reset",
                "git add --all",
                "No Changes",
                "1 Change",
                "{} Changes",
                "Enter commit message",
            },
        )

    def test_extracts_git_panel_tab_labels_passed_to_local_closure(self) -> None:
        source = "\n".join(
            [
                "impl GitPanel {",
                "    fn render_tab_bar(&self, cx: &mut Context<Self>) -> impl IntoElement {",
                "        let tab = |id: ElementId,",
                "                   active: bool,",
                "                   show_changes: bool,",
                "                   label: SharedString,",
                "                   set_active_tab: GitPanelTab| {",
                "            h_flex().child(Label::new(label))",
                "        };",
                "        h_flex()",
                "            .child(tab(",
                '                ElementId::Name("changes-tab".into()),',
                "                active_tab == GitPanelTab::Changes,",
                "                true,",
                '                "Changes".into(),',
                "                GitPanelTab::Changes,",
                "            ))",
                "            .child(tab(",
                '                ElementId::Name("history-tab".into()),',
                "                active_tab != GitPanelTab::Changes,",
                "                false,",
                '                "History".into(),',
                "                GitPanelTab::History,",
                "            ));",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Changes", "History"})
        self.assertEqual(by_source["Changes"].call, "git_panel_tab")
        self.assertEqual(by_source["History"].kind, "tab_title")

    def test_extracts_git_panel_macro_embedded_labels(self) -> None:
        source = "\n".join(
            [
                "impl GitPanel {",
                "    fn render_uninitialized_ui(&self) -> Vec<AnyElement> {",
                "        vec![",
                "            div()",
                "                .self_stretch()",
                "                .text_center()",
                '                .child("No Git Repositories")',
                "                .into_any_element(),",
                '            panel_filled_button("Initialize Repository")',
                "                .tooltip(Tooltip::for_action_title_in(",
                '                    "git init",',
                "                    &git::Init,",
                "                    &self.focus_handle,",
                "                ))",
                "                .into_any_element(),",
                "        ]",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {"No Git Repositories", "Initialize Repository"},
        )

    def test_extracts_git_remote_button_helpers(self) -> None:
        source = "\n".join(
            [
                "fn render_fetch_button() {",
                "    split_button(",
                "        id,",
                '        "Fetch",',
                "        0,",
                "        0,",
                "        None,",
                "        keybinding_target.clone(),",
                "        move |_, window, cx| {},",
                "        move |_window, cx| {",
                "            git_action_tooltip(",
                '                "Fetch updates from remote",',
                "                &git::Fetch,",
                '                "git fetch",',
                "                keybinding_target.clone(),",
                "                cx,",
                "            )",
                "        },",
                "    )",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/git_ui/src/git_ui.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(set(by_source), {"Fetch", "Fetch updates from remote"})
        self.assertEqual(by_source["Fetch"].kind, "button")
        self.assertEqual(by_source["Fetch updates from remote"].kind, "tooltip")

    def test_extracts_settings_fields_inside_macro_token_trees(self) -> None:
        source = "\n".join(
            [
                "fn page() {",
                "    fields: dynamic_variants::<ThemeSelection>().into_iter().map(|variant| {",
                "        vec![SettingItem {",
                '            title: "Mode",',
                '            description: "Choose whether to use the selected light or dark theme or to follow your OS appearance configuration.",',
                "            field: Box::new(SettingField { json_path: Some(\"theme.mode\") }),",
                "            metadata: None,",
                "        }]",
                "    });",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_ui/src/page_data.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Mode",
                "Choose whether to use the selected light or dark theme or to follow your OS appearance configuration.",
            },
        )
        self.assertEqual(by_source["Mode"].kind, "setting_title")

    def test_extracts_announcement_and_update_button_strings(self) -> None:
        source = "\n".join(
            [
                "fn announcement() {",
                "    let mut bullet_items: Vec<SharedString> = Vec::with_capacity(3);",
                '    bullet_items.push(format!("Skills live in {GLOBAL_SKILLS_DIR_DISPLAY}/<name>/SKILL.md").into());',
                '    bullet_items.push("Type / to manually invoke a skill".into());',
                "    if migrated_anything {",
                "        bullet_items.push(",
                '            "The Rules Library is making way for skills: your default rules are now in a global AGENTS.md, and your other rules have been converted to skills".into(),',
                "        );",
                "    }",
                "    Some(AnnouncementContent {",
                '        heading: "Introducing Parallel Agents".into(),',
                '        description: "Run multiple threads of your favorite agents simultaneously across projects.".into(),',
                "        bullet_items: vec![",
                '            "Use your favorite agents in parallel".into(),',
                "        ],",
                '        primary_action_label: "Try Agentic Layout".into(),',
                '        secondary_action_label: "Read Documentation".into(),',
                "    });",
                '    Self::new(IconName::Download, "Restart to Update");',
                '    AnnouncementToast::new().heading("Introducing Parallel Agents");',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/auto_update_ui/src/auto_update_ui.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "Introducing Parallel Agents",
                "Run multiple threads of your favorite agents simultaneously across projects.",
                "Skills live in {GLOBAL_SKILLS_DIR_DISPLAY}/<name>/SKILL.md",
                "Type / to manually invoke a skill",
                "The Rules Library is making way for skills: your default rules are now in a global AGENTS.md, and your other rules have been converted to skills",
                "Use your favorite agents in parallel",
                "Try Agentic Layout",
                "Read Documentation",
                "Restart to Update",
            },
        )

    def test_extracts_skills_illustration_badge_literals(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                "    let skill_crease = |label: SharedString, source: SharedString| {",
                "        h_flex()",
                "            .child(Label::new(label))",
                '            .child(Label::new(format!("({source})")));',
                "    };",
                "    div()",
                '        .child(skill_crease("img-gen".into(), "studio".into()))',
                '        .child(skill_crease("frontend-design".into(), "global".into()))',
                '        .child(skill_crease("brainstorming".into(), "global".into()))',
                '        .child(skill_crease("borrow-checker-expert".into(), "zed".into()))',
                '        .child(skill_crease("grill-with-docs".into(), "global".into()))',
                '        .child(skill_crease("video-edit".into(), "studio".into()));',
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/ui/src/components/ai/skills_illustration.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "({source})",
                "img-gen",
                "studio",
                "frontend-design",
                "global",
                "brainstorming",
                "borrow-checker-expert",
                "zed",
                "grill-with-docs",
                "video-edit",
            },
        )
        self.assertEqual(by_source["img-gen"].kind, "skill_illustration_name")
        self.assertEqual(by_source["global"].call, "skill_crease.source")

    def test_extracts_settings_content_doc_comments_used_as_ui_descriptions(self) -> None:
        source = "\n".join(
            [
                "pub enum SemanticTokens {",
                "    /// Do not request semantic tokens from language servers.",
                "    Off,",
                "    /// Use LSP semantic tokens together with tree-sitter highlighting.",
                "    Combined,",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/settings_content/src/workspace.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Do not request semantic tokens from language servers.",
                "Use LSP semantic tokens together with tree-sitter highlighting.",
            },
        )
        self.assertEqual(
            by_source["Do not request semantic tokens from language servers."].kind,
            "rust_doc_comment",
        )

    def test_extracts_agent_error_callout_helper_text(self) -> None:
        source = "\n".join(
            [
                "fn render(provider: &str) {",
                "    self.render_error_callout(",
                '        "Rate Limit Reached",',
                '        format!("{provider}\'s rate limit was reached. Zed will retry automatically."),',
                "        true,",
                "        true,",
                "        cx,",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/conversation_view/thread_view.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Rate Limit Reached",
                "{provider}'s rate limit was reached. Zed will retry automatically.",
            },
        )
        self.assertEqual(by_source["Rate Limit Reached"].kind, "callout_title")
        self.assertEqual(
            by_source["{provider}'s rate limit was reached. Zed will retry automatically."].kind,
            "callout_description",
        )

    def test_extracts_reviewed_ui_helper_arguments(self) -> None:
        source = "\n".join(
            [
                "fn render(focus_handle: FocusHandle) {",
                "    self.render_metric_row(",
                '        "Latency",',
                '        "Time for data to travel to the server",',
                "        value,",
                "        format_ms,",
                "        rate_latency,",
                "    );",
                '    self.render_loading("Connecting Server…");',
                "    render_action_button(",
                '        "search",',
                "        IconName::X,",
                "        None,",
                '        "Close Search Bar",',
                "        &CloseSearchBar,",
                "        focus_handle,",
                "    );",
                "    self.render_feature_upsell_banner(",
                '        "Claude Agent support is built-in to Zed!".into(),',
                '        "https://zed.dev/docs/agent".into(),',
                "        false,",
                "        cx,",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/search/src/search_bar.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Latency",
                "Time for data to travel to the server",
                "Connecting Server…",
                "Close Search Bar",
                "Claude Agent support is built-in to Zed!",
            },
        )
        self.assertEqual(by_source["Latency"].kind, "metric_title")
        self.assertEqual(by_source["Close Search Bar"].kind, "tooltip")
        self.assertEqual(
            by_source["Claude Agent support is built-in to Zed!"].call,
            "render_feature_upsell_banner",
        )

    def test_extracts_namespaced_toasts_and_notification_helpers(self) -> None:
        source = "\n".join(
            [
                "fn render(notification_id: NotificationId, cx: &mut App) {",
                "    workspace.show_toast(",
                "        workspace::Toast::new(",
                "            notification_id,",
                '            "Thread copied to clipboard (base64 encoded)",',
                "        )",
                "        .autohide(),",
                "        cx,",
                "    );",
                '    Self::show_deferred_toast(&self.workspace, "No clipboard content available", cx);',
                '    show_etw_notification(cx, "ETW recording cancelled");',
                "    show_etw_notification_with_action(",
                "        cx,",
                '        "ETW recording saved",',
                '        "Show in File Manager",',
                "        move |cx| {},",
                "    );",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent_ui/src/agent_panel.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Thread copied to clipboard (base64 encoded)",
                "No clipboard content available",
                "ETW recording cancelled",
                "ETW recording saved",
                "Show in File Manager",
            },
        )
        self.assertEqual(
            by_source["Thread copied to clipboard (base64 encoded)"].call,
            "Toast::new",
        )
        self.assertEqual(by_source["No clipboard content available"].call, "show_deferred_toast")
        self.assertEqual(by_source["Show in File Manager"].kind, "notification_action")

    def test_extracts_agent_tool_initial_titles_without_json_lookup_keys(self) -> None:
        source = "\n".join(
            [
                "fn initial_title(&self, input: Result<Self::Input, serde_json::Value>, _cx: &mut App) -> SharedString {",
                "    match input {",
                "        Ok(input) => {",
                "            let page = input.page();",
                "            let regex_str = MarkdownInlineCode(&input.regex);",
                '            format!("Get page {page} of search results for regex {regex_str}")',
                "        }",
                "        Err(value) => value",
                '            .get("label")',
                "            .and_then(|v| v.as_str())",
                "            .map(|s| SharedString::from(s.to_owned()))",
                '            .unwrap_or_else(|| "Search with regex".into()),',
                "    }",
                "    .into()",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent/src/tools/grep_tool.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Get page {page} of search results for regex {regex_str}",
                "Search with regex",
            },
        )
        self.assertNotIn("label", by_source)
        self.assertEqual(
            by_source["Get page {page} of search results for regex {regex_str}"].call,
            "initial_title",
        )

    def test_extracts_fast_mode_confirmation_copy(self) -> None:
        source = "\n".join(
            [
                "fn fast_mode_confirmation(&self, _cx: &App) -> Option<FastModeConfirmation> {",
                "    Some(FastModeConfirmation {",
                '        title: "Enable Fast Mode for OpenAI?".into(),',
                '        message: "Fast mode sends requests using OpenAI priority.".into(),',
                "    })",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/language_models/src/provider/open_ai.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Enable Fast Mode for OpenAI?",
                "Fast mode sends requests using OpenAI priority.",
            },
        )
        self.assertEqual(
            by_source["Enable Fast Mode for OpenAI?"].call,
            "FastModeConfirmation.title",
        )
        self.assertEqual(
            by_source["Fast mode sends requests using OpenAI priority."].kind,
            "fast_mode_confirmation_message",
        )

    def test_extracts_update_title_tool_helper_strings(self) -> None:
        source = "\n".join(
            [
                "impl UpdateTitleTool {",
                "    pub(crate) fn title_for_input(input: Result<UpdateTitleToolInput, serde_json::Value>) -> SharedString {",
                "        let Ok(input) = input else {",
                '            return "Update title".into();',
                "        };",
                '        format!("Update title: {title}").into()',
                "    }",
                "}",
                "impl AgentTool for UpdateTitleTool {",
                "    fn run(self: Arc<Self>) -> Task<Result<Self::Output, Self::Output>> {",
                '        Ok("Session title updated".to_string())',
                "    }",
                "}",
                "fn normalize_title(title: &str) -> Result<String, String> {",
                '    let title = title.lines().next().unwrap_or("").trim();',
                "    if title.is_empty() {",
                '        return Err("Title cannot be empty".to_string());',
                "    }",
                "    Ok(title.to_string())",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/agent/src/tools/update_title_tool.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "Update title",
                "Update title: {title}",
                "Session title updated",
                "Title cannot be empty",
            },
        )
        self.assertNotIn("", by_source)
        self.assertEqual(by_source["Update title"].call, "UpdateTitleTool.title_for_input")
        self.assertEqual(by_source["Session title updated"].kind, "agent_tool_output")
        self.assertEqual(by_source["Title cannot be empty"].kind, "agent_tool_error")

    def test_extracts_small_component_and_debugger_labels(self) -> None:
        source = "\n".join(
            [
                "fn render() {",
                '    ui::Chip::new("signed in");',
                '    Chip::new("Latest");',
                '    ToggleButtonSimple::new("Not Installed", selected, |_, _, _| {});',
                '    ViewWidth::new(1, "1 byte");',
                "}",
                'const ADAPTER_LOGS: &str = "Adapter Logs";',
                "impl std::fmt::Display for NewProcessMode {",
                "    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {",
                "        f.write_str(match self {",
                '            NewProcessMode::Debug => "Debug",',
                '            NewProcessMode::Attach => "Attach",',
                "        })",
                "    }",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/debugger_ui/src/new_process_modal.rs",
        )

        by_source = {occurrence.source: occurrence for occurrence in occurrences}
        self.assertEqual(
            set(by_source),
            {
                "signed in",
                "Latest",
                "Not Installed",
                "1 byte",
                "Debug",
                "Attach",
            },
        )
        self.assertEqual(by_source["signed in"].kind, "chip")
        self.assertEqual(by_source["Not Installed"].call, "ToggleButtonSimple::new")
        self.assertEqual(by_source["1 byte"].kind, "debugger_memory_width")
        self.assertEqual(by_source["Debug"].call, "NewProcessMode.display")

    def test_extracts_visible_strings_from_local_bindings_used_by_ui_calls(self) -> None:
        source = "\n".join(
            [
                "fn render(query: Option<String>, is_archive: bool, cx: &mut App) {",
                "    let header = if query.is_some() {",
                '        "No matches for query"',
                "    } else {",
                '        "No outlines available"',
                "    };",
                "    Label::new(header);",
                "    let label = if is_archive {",
                '        "Hide Thread History"',
                "    } else {",
                '        "Show Thread History"',
                "    };",
                "    Tooltip::for_action(label, &ToggleThreadHistory, cx);",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/outline_panel/src/outline_panel.rs",
        )

        self.assertEqual(
            {occurrence.source for occurrence in occurrences},
            {
                "No matches for query",
                "No outlines available",
                "Hide Thread History",
                "Show Thread History",
            },
        )

    def test_local_binding_resolution_does_not_follow_the_current_let_initializer(self) -> None:
        source = "\n".join(
            [
                "fn render(title: SharedString) {",
                "    let title = SharedString::from(title);",
                "    Label::new(title.clone());",
                "}",
            ]
        )

        occurrences = extract_ui_strings_from_source(
            source,
            relative_path="crates/activity_indicator/src/activity_indicator.rs",
        )

        self.assertEqual(occurrences, [])


if __name__ == "__main__":
    unittest.main()
