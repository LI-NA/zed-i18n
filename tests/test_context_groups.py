import json
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.context_groups import build_context_groups, write_context_group_reports


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

    def test_writes_settings_and_connected_line_review_reports(self) -> None:
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
        self.assertIn("Line Width", settings_md)
        self.assertIn("First sentence. Second sentence.", connected_md)

    def _write_source(self, relative_path: str, text: str) -> None:
        path = self.zed_root / relative_path
        path.parent.mkdir(parents=True)
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
