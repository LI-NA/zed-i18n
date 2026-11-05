import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.apply_universal import apply_zed_runtime_patches
from tools.zed_i18n.config import load_project_config, zed_clean_extract_checkout_path


PATCH_TARGETS = (
    "Cargo.toml",
    "assets/settings/default.json",
    "crates/auto_update_helper/Cargo.toml",
    "crates/auto_update_helper/src/auto_update_helper.rs",
    "crates/agent_ui/Cargo.toml",
    "crates/agent_ui/src/agent_configuration/configure_context_server_modal.rs",
    "crates/agent_ui/src/agent_panel.rs",
    "crates/collab/tests/integration/integration_tests.rs",
    "crates/copilot_ui/Cargo.toml",
    "crates/copilot_ui/src/sign_in.rs",
    "crates/debugger_tools/Cargo.toml",
    "crates/debugger_tools/src/dap_log.rs",
    "crates/debugger_ui/Cargo.toml",
    "crates/debugger_ui/src/new_process_modal.rs",
    "crates/debugger_ui/src/session/running/memory_view.rs",
    "crates/editor/Cargo.toml",
    "crates/editor/src/code_lens.rs",
    "crates/editor/src/editor.rs",
    "crates/editor/src/mouse_context_menu.rs",
    "crates/gpui/src/elements/text.rs",
    "crates/json_schema_store/Cargo.toml",
    "crates/json_schema_store/src/json_schema_store.rs",
    "crates/git_ui/Cargo.toml",
    "crates/git_ui/src/remote_output.rs",
    "crates/keymap_editor/Cargo.toml",
    "crates/keymap_editor/src/keymap_editor.rs",
    "crates/language_models/Cargo.toml",
    "crates/language_models/src/provider/openai_subscribed.rs",
    "crates/language_models/src/provider/x_ai_subscribed.rs",
    "crates/x_ai_subscribed/Cargo.toml",
    "crates/x_ai_subscribed/src/x_ai_subscribed.rs",
    "crates/extensions_ui/src/extension_suggestions.rs",
    "crates/language_model/Cargo.toml",
    "crates/language_model/src/registry.rs",
    "crates/language_selector/Cargo.toml",
    "crates/language_selector/src/language_selector.rs",
    "crates/language_selector/src/active_buffer_language.rs",
    "crates/multi_buffer/Cargo.toml",
    "crates/multi_buffer/src/multi_buffer.rs",
    "crates/onboarding/Cargo.toml",
    "crates/onboarding/src/basics_page.rs",
    "crates/search/Cargo.toml",
    "crates/search/src/project_search.rs",
    "crates/search/src/search.rs",
    "crates/settings/Cargo.toml",
    "crates/settings/src/base_keymap_setting.rs",
    "crates/settings/src/vscode_import.rs",
    "crates/settings_content/src/settings_content.rs",
    "crates/settings_ui/Cargo.toml",
    "crates/settings_ui/src/components.rs",
    "crates/settings_ui/src/components/dropdown.rs",
    "crates/settings_ui/src/page_data.rs",
    "crates/settings_ui/src/settings_ui.rs",
    "crates/settings_ui/src/pages/sandbox_settings.rs",
    "crates/settings_ui/src/pages/tool_permissions_setup.rs",
    "crates/ui/Cargo.toml",
    "crates/title_bar/Cargo.toml",
    "crates/title_bar/src/application_menu.rs",
    "crates/zed/src/zed/app_menus.rs",
    "crates/ui/src/components/context_menu.rs",
    "crates/zed/Cargo.toml",
    "crates/zed/src/main.rs",
    "crates/zed/src/watcher_debug.rs",
    "crates/zed/src/zed.rs",
    "crates/workspace/Cargo.toml",
    "crates/workspace/src/pane.rs",
    "crates/workspace/src/welcome.rs",
    "crates/which_key/Cargo.toml",
    "crates/which_key/src/pending_bindings.rs",
)


class RuntimeOverlayPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd()
        self.source = zed_clean_extract_checkout_path(
            self.root, load_project_config(self.root)
        )
        if not self.source.exists():
            self.skipTest(f"clean Zed checkout not available: {self.source}")
        self.temp_root = self.root / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self.zed_root = self.temp_root / "zed"
        for relative in PATCH_TARGETS:
            source = self.source / relative
            destination = self.zed_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_applies_every_control_plane_patch_and_is_idempotent(self) -> None:
        first = apply_zed_runtime_patches(self.root, self.zed_root)
        snapshot = {
            path.relative_to(self.zed_root).as_posix(): path.read_bytes()
            for path in self.zed_root.rglob("*")
            if path.is_file()
        }
        second = apply_zed_runtime_patches(self.root, self.zed_root)

        self.assertGreater(first.changed_files, 10)
        self.assertEqual(second.changed_files, 0)
        self.assertEqual(
            snapshot,
            {
                path.relative_to(self.zed_root).as_posix(): path.read_bytes()
                for path in self.zed_root.rglob("*")
                if path.is_file()
            },
        )

        menus = self._read("crates/zed/src/zed/app_menus.rs")
        for name in ("File", "Edit", "Selection", "View", "Go", "Run", "Window", "Help"):
            self.assertIn(f'name: application_menu_name("{name}")', menus)
        self.assertIn('if cfg!(target_os = "macos")', menus)
        application_menu = self._read("crates/title_bar/src/application_menu.rs")
        self.assertIn("menu_labels::label(&menu_name, window, cx)", application_menu)
        self.assertIn("menu_labels::matches(&entry.menu.name, &pending_menu_open)", application_menu)
        self.assertIn("!menu_labels::matches(&e.menu.name, &pending_menu_open)", application_menu)
        self.assertIn("localization.workspace = true", self._read("crates/title_bar/Cargo.toml"))

        settings = self._read("crates/settings_content/src/settings_content.rs")
        self.assertIn("pub struct UiLocale(pub String);", settings)
        self.assertIn("pub ui_locale: Option<UiLocale>,", settings)
        self.assertIn('"ui_locale": "system"', self._read("assets/settings/default.json"))

        main = self._read("crates/zed/src/main.rs")
        self.assertIn("zed::initialize_localization(fs.clone(), cx);", main)
        watcher_debug = self._read("crates/zed/src/watcher_debug.rs")
        self.assertIn(
            'Self::ScanExclusions => localization::localized_str!(', watcher_debug
        )
        self.assertTrue((self.zed_root / "crates/zed/src/zed/ui_locale.rs").exists())
        self.assertTrue(
            (self.zed_root / "crates/settings_ui/src/components/locale_picker.rs").exists()
        )

        schema = self._read("crates/json_schema_store/src/json_schema_store.rs")
        self.assertIn("inject_ui_locale_schema(&mut schema);", schema)
        self.assertIn("localize_schema_metadata(&mut schema);", schema)
        self.assertIn("localization::translate_static", self._read("crates/keymap_editor/src/keymap_editor.rs"))

        dropdown = self._read("crates/settings_ui/src/components/dropdown.rs")
        self.assertIn("window.use_keyed_state(self.selected_index, cx,", dropdown)
        self.assertNotIn("window.use_keyed_state(current_value_label, cx,", dropdown)
        self.assertIn("localization::lookup(&display_source)", dropdown)
        self.assertIn(".or_else(|| localization::lookup(label))", dropdown)
        settings_ui = self._read("crates/settings_ui/src/settings_ui.rs")
        self.assertIn(
            'current_sub_page.link.title.as_ref()\n                    == localization::localized_str!("LLM Providers")',
            settings_ui,
        )
        self.assertNotIn(
            'current_sub_page.link.title.as_ref() == "LLM Providers"', settings_ui
        )
        context_menu = self._read("crates/ui/src/components/context_menu.rs")
        self.assertIn("MENU_ITEM-ACTION-", context_menu)
        self.assertNotIn('format!("MENU_ITEM-{}", label)', context_menu)
        self.assertIn(
            '"MENU_ITEM-ACTION-editor::Copy"',
            self._read("crates/editor/src/mouse_context_menu.rs"),
        )
        collab_tests = self._read("crates/collab/tests/integration/integration_tests.rs")
        self.assertEqual(
            collab_tests.count('"MENU_ITEM-ACTION-pane::CloseActiveItem"'), 2
        )
        self.assertNotIn('"MENU_ITEM-Close"', collab_tests)
        self.assertIn(
            '"MENU_ITEM-ACTION-agent::ManageSkills"',
            self._read("crates/agent_ui/src/agent_panel.rs"),
        )

        gpui_text = self._read("crates/gpui/src/elements/text.rs")
        self.assertIn("pub fn set_text_observer", gpui_text)
        self.assertIn("observe_text(*self);", gpui_text)
        self.assertIn("observe_text(self.as_ref());", gpui_text)

        helper = self._read("crates/auto_update_helper/src/auto_update_helper.rs")
        self.assertIn("initialize_localization(&app_dir);", helper)
        self.assertIn("HSTRING::from(localization::localized_str!", helper)
        self.assertIn("serde_json_lenient::from_str::<LocaleSettings>", helper)
        helper_cargo = self._read("crates/auto_update_helper/Cargo.toml")
        self.assertIn("serde_json_lenient.workspace = true", helper_cargo)
        self.assertNotIn("settings_json", helper_cargo)
        self.assertNotIn("paths.workspace", helper_cargo)

        search = self._read("crates/search/src/search.rs")
        self.assertIn('localization::localized_str!("Replace in project…")', search)
        self.assertNotIn("const REPLACE_PLACEHOLDER", search)
        project_search = self._read("crates/search/src/project_search.rs")
        self.assertIn(
            "set_placeholder_text(include_placeholder(), window, cx)", project_search
        )
        self.assertNotIn("INCLUDE_PLACEHOLDER", project_search)

        pending_bindings = self._read("crates/which_key/src/pending_bindings.rs")
        self.assertIn('localization::localized_str!("is waiting for more keys…")', pending_bindings)
        self.assertNotIn("HEADER_LABEL", pending_bindings)
        self.assertIn("SharedString::from(header_label())", pending_bindings)
        self.assertIn("Label::new(header_label())", pending_bindings)
        self.assertIn("localization.workspace = true", self._read("crates/which_key/Cargo.toml"))

        language_selector = self._read("crates/language_selector/src/language_selector.rs")
        self.assertIn("mod localized_language_name;", language_selector)
        self.assertIn(
            "crate::localized_language_name::localized_language_name(&mat.string)",
            language_selector,
        )
        self.assertIn(
            "crate::localized_language_name::localized_match_positions(&label, mat)",
            language_selector,
        )
        self.assertIn("HighlightedLabel::new(label, positions)", language_selector)
        self.assertNotIn(
            "HighlightedLabel::new(label, mat.positions.clone())", language_selector
        )
        self.assertIn(
            "pub(crate) fn localized_match_positions",
            (
                self.zed_root
                / "crates/language_selector/src/localized_language_name.rs"
            ).read_text(encoding="utf-8"),
        )
        self.assertIn(
            "crate::localized_language_name::localized_language_name(",
            self._read("crates/language_selector/src/active_buffer_language.rs"),
        )
        self.assertTrue(
            (
                self.zed_root
                / "crates/language_selector/src/localized_language_name.rs"
            ).exists()
        )
        self.assertIn(
            "localization.workspace = true",
            self._read("crates/language_selector/Cargo.toml"),
        )

        self.assertIn(
            "let modal_description = localization::localized_str!",
            self._read("crates/agent_ui/src/agent_configuration/configure_context_server_modal.rs"),
        )
        self.assertIn(
            "localization::translate_static(label)",
            self._read("crates/git_ui/src/remote_output.rs"),
        )
        self.assertIn(
            "localization::translate_static(tool.name)",
            self._read("crates/settings_ui/src/pages/tool_permissions_setup.rs"),
        )
        self.assertNotIn(
            "const SETTINGS_DISCLAIMER",
            self._read("crates/settings_ui/src/pages/tool_permissions_setup.rs"),
        )
        self.assertIn(
            "localization::translate_static(self.title)",
            self._read("crates/workspace/src/welcome.rs"),
        )
        self.assertIn(
            '#[error("{}", localization::localized_str!',
            self._read("crates/language_model/src/registry.rs"),
        )

        super_grok = self._read("crates/language_models/src/provider/x_ai_subscribed.rs")
        self.assertNotIn("const SUBSCRIPTION_DESCRIPTION", super_grok)
        self.assertIn("Label::new(subscription_description())", super_grok)
        self.assertIn("InlineDescription::Text(subscription_description().into())", super_grok)
        self.assertIn(
            "message: localization::translate_static(INFERENCE_FORBIDDEN_MESSAGE).to_string(),",
            self._read("crates/x_ai_subscribed/src/x_ai_subscribed.rs"),
        )
        self.assertIn(
            "localization.workspace = true",
            self._read("crates/x_ai_subscribed/Cargo.toml"),
        )
        extension_suggest = self._read("crates/extensions_ui/src/extension_suggestions.rs")
        for field in ("description", "title", "install_message"):
            self.assertIn(
                f"localization::translate_static(suggestion.{field})", extension_suggest
            )

    def test_fails_closed_when_an_upstream_anchor_drifts(self) -> None:
        path = self.zed_root / "crates/zed/src/main.rs"
        source = path.read_text(encoding="utf-8")
        path.write_text(
            source.replace("zed::watch_settings_files(fs.clone(), cx);", "zed::watch_settings_files_v2(fs.clone(), cx);"),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "structural patch anchor"):
            apply_zed_runtime_patches(self.root, self.zed_root)

    def _read(self, relative: str) -> str:
        return (self.zed_root / relative).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
