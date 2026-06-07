import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.apply import apply_translations


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_applies_accepted_translation_at_recorded_location(self) -> None:
        source_path = self.root / "crates" / "zed" / "src" / "zed" / "app_menus.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            'MenuItem::action("Open Settings", zed_actions::OpenSettings);\n'
            'MenuItem::action("Save All", workspace::SaveAll);\n',
            encoding="utf-8",
        )
        manifest = {
            "Open Settings": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/zed/src/zed/app_menus.rs",
                        "line": 1,
                        "call": "MenuItem::action",
                        "kind": "menu_item",
                    }
                ],
            },
            "Save All": {
                "status": "needs_review",
                "occurrences": [
                    {
                        "file": "crates/zed/src/zed/app_menus.rs",
                        "line": 2,
                        "call": "MenuItem::action",
                        "kind": "menu_item",
                    }
                ],
            },
        }
        translations = {"Open Settings": "설정 열기", "Save All": "모두 저장"}

        report = apply_translations(self.root, manifest, translations)

        self.assertEqual(report.applied, ["Open Settings"])
        self.assertEqual(report.skipped, ["Save All"])
        self.assertEqual(report.missing, [])
        self.assertIn('"설정 열기"', source_path.read_text(encoding="utf-8"))
        self.assertIn('"Save All"', source_path.read_text(encoding="utf-8"))

    def test_reports_missing_translation_without_modifying_source(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text('Label::new("Welcome");\n', encoding="utf-8")
        manifest = {
            "Welcome": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {})

        self.assertEqual(report.applied, [])
        self.assertEqual(report.missing, ["Welcome"])
        self.assertFalse(report.ok)
        self.assertIn('"Welcome"', source_path.read_text(encoding="utf-8"))

    def test_reports_stale_occurrence_when_recorded_source_is_not_present(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text('Label::new("환영합니다");\n', encoding="utf-8")
        manifest = {
            "Welcome": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"Welcome": "환영합니다"})

        self.assertEqual(report.applied, [])
        self.assertEqual(report.stale, ["Welcome"])
        self.assertFalse(report.ok)

    def test_stale_fallback_does_not_rewrite_later_matching_literals(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text(
            'Label::new("환영합니다");\n'
            'Label::new("Welcome");\n',
            encoding="utf-8",
        )
        manifest = {
            "Welcome": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"Welcome": "환영합니다"})

        self.assertEqual(report.applied, [])
        self.assertEqual(report.stale, ["Welcome"])
        self.assertIn('"Welcome"', source_path.read_text(encoding="utf-8"))

    def test_partially_stale_source_is_not_reported_as_applied(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text(
            'Label::new("환영합니다");\n'
            'Label::new("Welcome");\n',
            encoding="utf-8",
        )
        manifest = {
            "Welcome": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    },
                    {
                        "file": "main.rs",
                        "line": 2,
                        "call": "Label::new",
                        "kind": "label",
                    },
                    {
                        "file": "main.rs",
                        "line": 3,
                        "call": "Label::new",
                        "kind": "label",
                    },
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"Welcome": "환영합니다"})

        self.assertEqual(report.applied, [])
        self.assertEqual(report.stale, ["Welcome"])
        self.assertFalse(report.ok)
        self.assertIn('"환영합니다"', source_path.read_text(encoding="utf-8"))

    def test_applies_translation_to_rust_doc_comment_occurrence(self) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "workspace.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "/// Do not request semantic tokens from language servers.\n"
            "Off,\n",
            encoding="utf-8",
        )
        manifest = {
            "Do not request semantic tokens from language servers.": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/workspace.rs",
                        "line": 1,
                        "call": "rust_doc_comment",
                        "kind": "rust_doc_comment",
                    }
                ],
            }
        }
        translations = {
            "Do not request semantic tokens from language servers.": "언어 서버에서 시맨틱 토큰을 요청하지 않습니다."
        }

        report = apply_translations(self.root, manifest, translations)

        self.assertEqual(
            report.applied,
            ["Do not request semantic tokens from language servers."],
        )
        self.assertIn(
            "/// 언어 서버에서 시맨틱 토큰을 요청하지 않습니다.",
            source_path.read_text(encoding="utf-8"),
        )

    def test_applies_translation_to_line_continued_rust_string_literal(self) -> None:
        source_path = self.root / "main.rs"
        source = (
            "This file has unsaved changes. Do you want to save or discard them "
            "before the agent continues editing?"
        )
        source_path.write_text(
            'let message = "This file has unsaved changes. Do you want to save or discard them \\\n'
            '             before the agent continues editing?".to_string();\n',
            encoding="utf-8",
        )
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "authorize_dirty_buffer",
                        "kind": "prompt_message",
                    }
                ],
            }
        }

        report = apply_translations(
            self.root,
            manifest,
            {source: "저장되지 않은 변경 사항이 있습니다. 계속 편집하기 전에 저장하거나 버리시겠습니까?"},
        )

        self.assertEqual(report.applied, [source])
        self.assertEqual(report.stale, [])
        self.assertIn(
            '"저장되지 않은 변경 사항이 있습니다. 계속 편집하기 전에 저장하거나 버리시겠습니까?"',
            source_path.read_text(encoding="utf-8"),
        )

    def test_applies_translation_to_legacy_line_continued_manifest_source(self) -> None:
        source_path = self.root / "main.rs"
        source = (
            "Run LLMs locally on your machine with Ollama, or connect to an Ollama server. "
            "                Can provide access to Llama, Mistral, Gemma, and hundreds of other models."
        )
        source_path.write_text(
            'Label::new("Run LLMs locally on your machine with Ollama, or connect to an Ollama server. \\\n'
            '                Can provide access to Llama, Mistral, Gemma, and hundreds of other models.");\n',
            encoding="utf-8",
        )
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            }
        }

        report = apply_translations(
            self.root,
            manifest,
            {source: "로컬 Ollama로 LLM을 실행하거나 Ollama 서버에 연결할 수 있습니다."},
        )

        self.assertEqual(report.applied, [source])
        self.assertEqual(report.stale, [])
        self.assertIn(
            '"로컬 Ollama로 LLM을 실행하거나 Ollama 서버에 연결할 수 있습니다."',
            source_path.read_text(encoding="utf-8"),
        )

    def test_allows_named_placeholders_to_move_around_implicit_placeholders(self) -> None:
        source_path = self.root / "main.rs"
        source = "{message_start} the following {} files?\n{}{unsaved_warning}"
        source_path.write_text(
            'format!("{message_start} the following {} files?\\n{}{unsaved_warning}", count, names);\n',
            encoding="utf-8",
        )
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "delete_prompt_format",
                        "kind": "prompt_message",
                    }
                ],
            }
        }

        report = apply_translations(
            self.root,
            manifest,
            {source: "다음 {}개 파일을 {message_start}하시겠습니까?\n{}{unsaved_warning}"},
        )

        self.assertEqual(report.applied, [source])
        self.assertEqual(report.stale, [])

    def test_applies_translation_to_action_doc_comment_occurrence(self) -> None:
        source_path = self.root / "crates" / "agent_ui" / "src" / "agent_ui.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "actions!(\n"
            "    agent,\n"
            "    [\n"
            "        /// Cycles through favorited models in the ACP model selector.\n"
            "        CycleFavoriteModels,\n"
            "    ]\n"
            ");\n",
            encoding="utf-8",
        )
        manifest = {
            "Cycles through favorited models in the ACP model selector.": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/agent_ui/src/agent_ui.rs",
                        "line": 4,
                        "call": "action_doc_comment",
                        "kind": "action_description",
                    }
                ],
            }
        }
        translations = {
            "Cycles through favorited models in the ACP model selector.": "ACP 모델 선택기에서 즐겨찾기한 모델을 순환합니다."
        }

        report = apply_translations(self.root, manifest, translations)

        self.assertEqual(
            report.applied,
            ["Cycles through favorited models in the ACP model selector."],
        )
        self.assertIn(
            "/// ACP 모델 선택기에서 즐겨찾기한 모델을 순환합니다.",
            source_path.read_text(encoding="utf-8"),
        )

    def test_applies_split_structs_action_doc_as_string_literal(self) -> None:
        source_path = self.root / "crates" / "workspace" / "src" / "pane.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            'SplitRight => "Splits the pane to the right.",\n',
            encoding="utf-8",
        )
        manifest = {
            "Splits the pane to the right.": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/workspace/src/pane.rs",
                        "line": 1,
                        "call": "split_structs",
                        "kind": "action_description",
                    }
                ],
            }
        }
        translations = {
            "Splits the pane to the right.": '오른쪽 "pane"으로 분할합니다.',
        }

        report = apply_translations(self.root, manifest, translations)

        self.assertTrue(report.ok)
        self.assertIn(
            'SplitRight => "오른쪽 \\"pane\\"으로 분할합니다.",',
            source_path.read_text(encoding="utf-8"),
        )

    def test_applies_translation_to_generated_strum_variant_label(self) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "agent.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "pub enum ThinkingBlockDisplay {\n"
            "    #[default]\n"
            "    AlwaysExpanded,\n"
            "}\n",
            encoding="utf-8",
        )
        manifest = {
            "Always Expanded": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 3,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"Always Expanded": "항상 펼침"})

        self.assertTrue(report.ok)
        self.assertIn(
            '    #[strum(serialize = "항상 펼침")]\n    AlwaysExpanded,',
            source_path.read_text(encoding="utf-8"),
        )

    def test_disables_settings_dropdown_title_case_for_generated_strum_labels(self) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "agent.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "pub enum ThinkingBlockDisplay {\n"
            "    AlwaysExpanded,\n"
            "}\n",
            encoding="utf-8",
        )
        settings_ui_path = self.root / "crates" / "settings_ui" / "src" / "settings_ui.rs"
        settings_ui_path.parent.mkdir(parents=True)
        settings_ui_path.write_text(
            "fn render_text_field(\n"
            "    metadata: Option<&SettingsFieldMetadata>,\n"
            ") {\n"
            "    let _ = metadata;\n"
            "}\n\n"
            "fn render_dropdown<T>(\n"
            "    field: &'static SettingField<T>,\n"
            "    file: SettingsUiFile,\n"
            "    metadata: Option<&SettingsFieldMetadata>,\n"
            "    _window: &mut Window,\n"
            "    cx: &mut App,\n"
            ") -> AnyElement\n"
            "where\n"
            "    T: strum::VariantArray + strum::VariantNames + Copy + PartialEq + Send + Sync + 'static,\n"
            "{\n"
            "    let variants = || -> &'static [T] { <T as strum::VariantArray>::VARIANTS };\n"
            "    let labels = || -> &'static [&'static str] { <T as strum::VariantNames>::VARIANTS };\n"
            "    let should_do_titlecase = metadata\n"
            "        .and_then(|metadata| metadata.should_do_titlecase)\n"
            "        .unwrap_or(true);\n"
            "    EnumVariantDropdown::new(\"dropdown\", current_value, variants(), labels(), {})\n"
            "        .tab_index(0)\n"
            "        .title_case(should_do_titlecase)\n"
            "        .into_any_element()\n"
            "}\n",
            encoding="utf-8",
        )
        manifest = {
            "Always Expanded": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 2,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"Always Expanded": "항상 펼침"})

        self.assertTrue(report.ok)
        settings_ui = settings_ui_path.read_text(encoding="utf-8")
        self.assertIn("fn render_text_field(\n    metadata: Option<&SettingsFieldMetadata>,", settings_ui)
        self.assertIn("    _metadata: Option<&SettingsFieldMetadata>,", settings_ui)
        self.assertEqual(settings_ui.count("    _metadata: Option<&SettingsFieldMetadata>,"), 1)
        self.assertIn("    let should_do_titlecase = false;", settings_ui)
        self.assertIn("        .title_case(should_do_titlecase)", settings_ui)
        self.assertNotIn("metadata.should_do_titlecase", settings_ui)

    def test_reapplying_generated_strum_variant_label_updates_existing_attribute(self) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "agent.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "pub enum ThinkingBlockDisplay {\n"
            "    Auto,\n"
            "    AlwaysExpanded,\n"
            "}\n",
            encoding="utf-8",
        )
        manifest = {
            "Always Expanded": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 3,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            }
        }

        self.assertTrue(
            apply_translations(self.root, manifest, {"Always Expanded": "항상 펼침"}).ok
        )
        self.assertTrue(
            apply_translations(self.root, manifest, {"Always Expanded": "항상 확장"}).ok
        )

        text = source_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("#[strum(serialize"), 1)
        self.assertIn('    #[strum(serialize = "항상 확장")]\n', text)

    def test_applies_translation_to_generated_strum_discriminant_label(self) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "workspace.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "pub enum AutosaveSetting {\n"
            "    AfterDelay { milliseconds: DelayMs },\n"
            "}\n",
            encoding="utf-8",
        )
        manifest = {
            "After Delay": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/workspace.rs",
                        "line": 2,
                        "call": "strum::EnumDiscriminants",
                        "kind": "settings_enum_discriminant_label",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"After Delay": "지연 후"})

        self.assertTrue(report.ok)
        self.assertIn(
            '    #[strum_discriminants(strum(serialize = "지연 후"))]\n'
            "    AfterDelay { milliseconds: DelayMs },",
            source_path.read_text(encoding="utf-8"),
        )

    def test_reapplying_shifted_generated_strum_labels_does_not_duplicate_attributes(
        self,
    ) -> None:
        source_path = self.root / "crates" / "settings_content" / "src" / "agent.rs"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "pub enum ThinkingBlockDisplay {\n"
            "    Auto,\n"
            "    AlwaysExpanded,\n"
            "    AlwaysCollapsed,\n"
            "}\n",
            encoding="utf-8",
        )
        manifest = {
            "Auto": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 2,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            },
            "Always Expanded": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 3,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            },
            "Always Collapsed": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/settings_content/src/agent.rs",
                        "line": 4,
                        "call": "strum::VariantNames",
                        "kind": "settings_enum_variant_label",
                    }
                ],
            },
        }
        translations = {
            "Auto": "자동",
            "Always Expanded": "항상 펼침",
            "Always Collapsed": "항상 접힘",
        }

        self.assertTrue(apply_translations(self.root, manifest, translations).ok)
        self.assertTrue(apply_translations(self.root, manifest, translations).ok)

        text = source_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("#[strum(serialize"), 3)

    def test_applies_translation_to_multiline_string_literal(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text(
            'Label::new(indoc!{"\n'
            '    Open your settings to add sensitive paths for which Zed will never predict edits."});\n',
            encoding="utf-8",
        )
        source = "\n    Open your settings to add sensitive paths for which Zed will never predict edits."
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            }
        }
        translations = {
            source: "\n    Zed가 편집을 예측하지 않을 민감한 경로를 추가하려면 설정을 여세요."
        }

        report = apply_translations(self.root, manifest, translations)

        self.assertTrue(report.ok)
        self.assertIn(
            '"\\n    Zed가 편집을 예측하지 않을 민감한 경로를 추가하려면 설정을 여세요."',
            source_path.read_text(encoding="utf-8"),
        )

    def test_applies_later_occurrences_before_multiline_rewrites_shift_lines(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text(
            'Label::new(indoc!{"\n'
            '    Open your settings to add sensitive paths for which Zed will never predict edits."});\n'
            'Label::new("Actions");\n',
            encoding="utf-8",
        )
        multiline_source = "\n    Open your settings to add sensitive paths for which Zed will never predict edits."
        manifest = {
            multiline_source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            },
            "Actions": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 3,
                        "call": "Label::new",
                        "kind": "label",
                    }
                ],
            },
        }
        translations = {
            multiline_source: "\n    Zed가 편집을 예측하지 않을 민감한 경로를 추가하려면 설정을 여세요.",
            "Actions": "동작",
        }

        report = apply_translations(self.root, manifest, translations)

        text = source_path.read_text(encoding="utf-8")
        self.assertTrue(report.ok)
        self.assertIn('"동작"', text)
        self.assertIn(
            '"\\n    Zed가 편집을 예측하지 않을 민감한 경로를 추가하려면 설정을 여세요."',
            text,
        )

    def test_applies_translation_to_rust_unicode_escape_literal(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text('Tooltip::text("New Thread\\u{2026}");\n', encoding="utf-8")
        manifest = {
            "New Thread\\u{2026}": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "Tooltip::text",
                        "kind": "tooltip",
                    }
                ],
            }
        }

        report = apply_translations(self.root, manifest, {"New Thread\\u{2026}": "새 스레드…"})

        self.assertTrue(report.ok)
        self.assertIn('"새 스레드…"', source_path.read_text(encoding="utf-8"))

    def test_preserves_rust_unicode_escapes_inside_format_strings(self) -> None:
        source_path = self.root / "main.rs"
        source_path.write_text(
            'let message = format!("Available. Saved to {sep}\\u{2039}name\\u{203A}{sep}{file}.");\n',
            encoding="utf-8",
        )
        source = "Available. Saved to {sep}\\u{2039}name\\u{203A}{sep}{file}."
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "main.rs",
                        "line": 1,
                        "call": "format!",
                        "kind": "format",
                    }
                ],
            }
        }

        report = apply_translations(
            self.root,
            manifest,
            {
                source: "사용 가능. {sep}\\u{2039}name\\u{203A}{sep}{file}에 저장됩니다.",
            },
        )

        text = source_path.read_text(encoding="utf-8")
        self.assertTrue(report.ok)
        self.assertIn("\\u{2039}name\\u{203A}", text)
        self.assertNotIn("\\\\u{2039}", text)


if __name__ == "__main__":
    unittest.main()
