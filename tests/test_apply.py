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


if __name__ == "__main__":
    unittest.main()
