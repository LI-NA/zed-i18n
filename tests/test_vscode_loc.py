import json
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.vscode_loc import (
    find_vscode_references,
    load_vscode_translation_memory,
)


class VscodeLocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.vscode_loc_root = self.root / ".cache" / "vscode-loc"
        self.pack_root = self.vscode_loc_root / "i18n" / "vscode-language-pack-ko"
        self.vscode_source_root = self.root / ".cache" / "vscode-upstream"
        (self.pack_root / "translations" / "extensions").mkdir(parents=True)
        (self.vscode_source_root / "extensions" / "git").mkdir(parents=True)
        (self.vscode_source_root / "src" / "vs" / "workbench" / "browser" / "parts" / "editor").mkdir(
            parents=True
        )
        self._write_json(
            self.pack_root / "package.json",
            {
                "contributes": {
                    "localizations": [
                        {
                            "languageId": "ko",
                            "translations": [
                                {
                                    "id": "vscode.git",
                                    "path": "./translations/extensions/vscode.git.i18n.json",
                                },
                                {
                                    "id": "vscode",
                                    "path": "./translations/main.i18n.json",
                                },
                            ],
                        }
                    ]
                }
            },
        )
        self._write_json(
            self.pack_root / "translations" / "extensions" / "vscode.git.i18n.json",
            {
                "contents": {
                    "package": {
                        "command.clone": "클론",
                        "Open Settings": "설정 열기",
                        "Command Palette": "명령 팔레트",
                        "git.command.stage": "스테이징",
                    }
                }
            },
        )
        self._write_json(
            self.vscode_source_root / "extensions" / "git" / "package.json",
            {"publisher": "vscode", "name": "git"},
        )
        self._write_json(
            self.vscode_source_root / "extensions" / "git" / "package.nls.json",
            {
                "command.clone": "Clone",
                "git.command.stage": "Stage Changes",
            },
        )
        (
            self.vscode_source_root
            / "src"
            / "vs"
            / "workbench"
            / "browser"
            / "parts"
            / "editor"
            / "breadcrumbsPicker.ts"
        ).write_text(
            "\n".join(
                [
                    "return localize('breadcrumbs', \"Breadcrumbs\");",
                    "return localize('searchWithEllipsis', \"Search...\");",
                    "return localize('taskLabel', \"Task\");",
                    "return localize('extensionLabel', \"Extension\");",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self._write_json(
            self.pack_root / "translations" / "main.i18n.json",
            {
                "contents": {
                    "vs/workbench/browser/parts/editor/breadcrumbsPicker": {
                        "breadcrumbs": "이동 경로",
                        "searchWithEllipsis": "검색...",
                        "taskLabel": "태스크",
                        "extensionLabel": "확장",
                    }
                }
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_load_translation_memory_uses_language_pack_for_locale(self) -> None:
        memory = load_vscode_translation_memory(self.vscode_loc_root, "ko-KR")

        by_source = {entry.source: entry.translation for entry in memory}
        self.assertEqual(by_source["Open Settings"], "설정 열기")
        self.assertEqual(by_source["Command Palette"], "명령 팔레트")
        self.assertNotIn("git.command.stage", by_source)

    def test_load_translation_memory_can_recover_english_sources_from_vscode(self) -> None:
        memory = load_vscode_translation_memory(
            self.vscode_loc_root,
            "ko-KR",
            self.vscode_source_root,
        )

        by_source = {entry.source: entry.translation for entry in memory}
        self.assertEqual(by_source["Clone"], "클론")
        self.assertEqual(by_source["Stage Changes"], "스테이징")
        self.assertEqual(by_source["Breadcrumbs"], "이동 경로")

    def test_find_vscode_references_prefers_exact_source_matches(self) -> None:
        memory = load_vscode_translation_memory(self.vscode_loc_root, "ko-KR")

        references = find_vscode_references("Open Settings", memory, limit=2)

        self.assertEqual(references[0]["source"], "Open Settings")
        self.assertEqual(references[0]["translation"], "설정 열기")
        self.assertEqual(references[0]["score"], 1.0)

    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
