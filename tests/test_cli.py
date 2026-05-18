import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import call, patch

from tools.zed_i18n.cli import (
    build_parser,
    preserve_manifest_statuses,
    resolve_zed_root,
    run_fetch_zed,
    run_generate_vscode_glossary,
    run_validate,
)
from tools.zed_i18n.config import ProjectConfig


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parser_accepts_initial_commands(self) -> None:
        parser = build_parser()

        self.assertEqual(parser.parse_args(["fetch-zed"]).command, "fetch-zed")
        self.assertEqual(parser.parse_args(["extract"]).command, "extract")
        self.assertEqual(
            parser.parse_args(["extract", "--zed-root", ".cache/zed/v1.0.1-clean-extract"]).zed_root,
            ".cache/zed/v1.0.1-clean-extract",
        )
        self.assertEqual(parser.parse_args(["audit-candidates"]).command, "audit-candidates")
        self.assertEqual(
            parser.parse_args(
                ["audit-candidates", "--zed-root", ".cache/zed/v1.0.1-clean-extract"]
            ).zed_root,
            ".cache/zed/v1.0.1-clean-extract",
        )
        self.assertEqual(
            parser.parse_args(["validate", "--language", "ko-KR"]).language,
            "ko-KR",
        )
        self.assertFalse(
            parser.parse_args(["validate", "--language", "ko-KR", "--no-cleanup"]).cleanup
        )
        self.assertEqual(
            parser.parse_args(["apply", "--language", "ko-KR"]).language,
            "ko-KR",
        )
        prepare_args = parser.parse_args(
            [
                "prepare-translation",
                "--language",
                "ko-KR",
                "--zed-root",
                ".cache/zed/v1.0.1-clean-extract",
                "--batch-size",
                "25",
                "--context-lines",
                "8",
                "--all",
            ]
        )
        self.assertEqual(prepare_args.command, "prepare-translation")
        self.assertEqual(prepare_args.language, "ko-KR")
        self.assertEqual(prepare_args.batch_size, 25)
        self.assertEqual(prepare_args.context_lines, 8)
        self.assertFalse(prepare_args.missing_only)
        self.assertTrue(
            parser.parse_args(
                ["prepare-translation", "--language", "ko-KR", "--missing-only"]
            ).missing_only
        )
        merge_args = parser.parse_args(
            [
                "merge-translation",
                "--language",
                "ko-KR",
                "--results-dir",
                "reports/translation/ko-KR/results",
                "--output",
                "translations/ko-KR.model-a.json",
            ]
        )
        self.assertEqual(merge_args.command, "merge-translation")
        self.assertEqual(merge_args.language, "ko-KR")
        self.assertEqual(merge_args.results_dir, "reports/translation/ko-KR/results")
        self.assertEqual(merge_args.output, "translations/ko-KR.model-a.json")
        context_group_args = parser.parse_args(
            [
                "extract-context-groups",
                "--language",
                "ko-KR",
                "--group-type",
                "settings",
                "--output-dir",
                "reports/context-groups/ko-KR",
            ]
        )
        self.assertEqual(context_group_args.command, "extract-context-groups")
        self.assertEqual(context_group_args.language, "ko-KR")
        self.assertEqual(context_group_args.group_type, "settings")
        self.assertEqual(context_group_args.output_dir, "reports/context-groups/ko-KR")
        glossary_args = parser.parse_args(
            [
                "generate-vscode-glossary",
                "--language",
                "ko-KR",
                "--vscode-loc-root",
                ".cache/vscode-loc",
                "--vscode-source-root",
                ".cache/vscode-upstream",
                "--output",
                "reports/vscode-glossary/ko-KR.md",
            ]
        )
        self.assertEqual(glossary_args.command, "generate-vscode-glossary")
        self.assertEqual(glossary_args.language, "ko-KR")
        self.assertEqual(glossary_args.vscode_loc_root, ".cache/vscode-loc")
        self.assertEqual(glossary_args.vscode_source_root, ".cache/vscode-upstream")
        self.assertEqual(glossary_args.output, "reports/vscode-glossary/ko-KR.md")
        prompt_glossary_args = parser.parse_args(
            [
                "generate-vscode-glossary",
                "--language",
                "ko-KR",
                "--prompt-glossary-output-dir",
                "prompts/translation/glossary",
            ]
        )
        self.assertEqual(
            prompt_glossary_args.prompt_glossary_output_dir,
            "prompts/translation/glossary",
        )

    def test_preserves_existing_manifest_statuses_when_extracting_again(self) -> None:
        manifest = {
            "Open Settings": {"status": "needs_review", "occurrences": []},
            "Internal Identifier": {"status": "needs_review", "occurrences": []},
            "Previously Translated": {"status": "needs_review", "occurrences": []},
            "Brand New": {"status": "needs_review", "occurrences": []},
        }
        previous_manifest = {
            "Open Settings": {"status": "accepted", "occurrences": []},
            "Internal Identifier": {"status": "ignored", "occurrences": []},
        }
        translations = {"Previously Translated": "이미 번역됨"}

        preserve_manifest_statuses(manifest, previous_manifest, translations)

        self.assertEqual(manifest["Open Settings"]["status"], "accepted")
        self.assertEqual(manifest["Internal Identifier"]["status"], "ignored")
        self.assertEqual(manifest["Previously Translated"]["status"], "accepted")
        self.assertEqual(manifest["Brand New"]["status"], "needs_review")

    def test_resolves_zed_root_override_inside_workspace(self) -> None:
        root = Path.cwd()
        config = ProjectConfig(
            zed_version="v1.0.1",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )

        resolved = resolve_zed_root(root, config, ".cache/zed/v1.0.1-clean-extract")

        self.assertEqual(resolved, (root / ".cache/zed/v1.0.1-clean-extract").resolve())

    def test_resolves_clean_extract_checkout_by_default(self) -> None:
        root = Path.cwd()
        config = ProjectConfig(
            zed_version="v1.0.1",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )

        resolved = resolve_zed_root(root, config, None)

        self.assertEqual(resolved, (root / ".cache/zed/v1.0.1-clean-extract").resolve())

    def test_rejects_zed_root_override_outside_workspace(self) -> None:
        root = Path.cwd()
        config = ProjectConfig(
            zed_version="v1.0.1",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )

        with self.assertRaises(ValueError):
            resolve_zed_root(root, config, "..")

    def test_fetch_zed_clones_build_and_clean_extract_checkouts(self) -> None:
        self._write_project_config()

        with patch("tools.zed_i18n.cli.subprocess.run") as run:
            exit_code = run_fetch_zed(self.tmp)

        build_checkout = self.tmp / ".cache" / "zed" / "v1.0.1"
        clean_checkout = self.tmp / ".cache" / "zed" / "v1.0.1-clean-extract"
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            run.call_args_list,
            [
                call(
                    [
                        "git",
                        "clone",
                        "--branch",
                        "v1.0.1",
                        "--depth",
                        "1",
                        "https://github.com/zed-industries/zed",
                        str(build_checkout),
                    ],
                    check=True,
                ),
                call(
                    [
                        "git",
                        "clone",
                        "--branch",
                        "v1.0.1",
                        "--depth",
                        "1",
                        "https://github.com/zed-industries/zed",
                        str(clean_checkout),
                    ],
                    check=True,
                ),
            ],
        )

    def test_fetch_zed_clones_missing_clean_extract_when_build_checkout_exists(self) -> None:
        self._write_project_config()
        build_checkout = self.tmp / ".cache" / "zed" / "v1.0.1"
        build_checkout.mkdir(parents=True)

        with patch("tools.zed_i18n.cli.subprocess.run") as run:
            exit_code = run_fetch_zed(self.tmp)

        clean_checkout = self.tmp / ".cache" / "zed" / "v1.0.1-clean-extract"
        self.assertEqual(exit_code, 0)
        run.assert_called_once_with(
            [
                "git",
                "clone",
                "--branch",
                "v1.0.1",
                "--depth",
                "1",
                "https://github.com/zed-industries/zed",
                str(clean_checkout),
            ],
            check=True,
        )

    def test_validate_success_cleans_translation_workspace(self) -> None:
        self._write_json(
            self.tmp / "manifest" / "ui-strings.json",
            {"Open Settings": {"status": "accepted", "occurrences": []}},
        )
        self._write_json(self.tmp / "translations" / "ko-KR.json", {"Open Settings": "설정 열기"})
        translation_workspace = self.tmp / "reports" / "translation" / "ko-KR"
        (translation_workspace / "results").mkdir(parents=True)
        (translation_workspace / "results" / "batch-001.json").write_text(
            '{"Open Settings": "설정 열기"}',
            encoding="utf-8",
        )

        exit_code = run_validate(self.tmp, "ko-KR")

        self.assertEqual(exit_code, 0)
        self.assertFalse(translation_workspace.exists())
        self.assertTrue((self.tmp / "reports" / "validate-ko-KR.json").exists())

    def test_validate_success_can_keep_translation_workspace(self) -> None:
        self._write_json(
            self.tmp / "manifest" / "ui-strings.json",
            {"Open Settings": {"status": "accepted", "occurrences": []}},
        )
        self._write_json(self.tmp / "translations" / "ko-KR.json", {"Open Settings": "설정 열기"})
        translation_workspace = self.tmp / "reports" / "translation" / "ko-KR"
        (translation_workspace / "results").mkdir(parents=True)
        (translation_workspace / "results" / "batch-001.json").write_text(
            '{"Open Settings": "설정 열기"}',
            encoding="utf-8",
        )

        exit_code = run_validate(self.tmp, "ko-KR", cleanup=False)

        self.assertEqual(exit_code, 0)
        self.assertTrue(translation_workspace.exists())
        self.assertTrue((self.tmp / "reports" / "validate-ko-KR.json").exists())

    def test_validate_failure_keeps_translation_workspace(self) -> None:
        self._write_json(
            self.tmp / "manifest" / "ui-strings.json",
            {"Open Settings": {"status": "accepted", "occurrences": []}},
        )
        self._write_json(self.tmp / "translations" / "ko-KR.json", {})
        translation_workspace = self.tmp / "reports" / "translation" / "ko-KR"
        (translation_workspace / "results").mkdir(parents=True)
        (translation_workspace / "results" / "batch-001.json").write_text(
            "{}",
            encoding="utf-8",
        )

        exit_code = run_validate(self.tmp, "ko-KR")

        self.assertEqual(exit_code, 1)
        self.assertTrue(translation_workspace.exists())

    def test_generate_vscode_glossary_rejects_pseudo_localization(self) -> None:
        qps_package_path = (
            self.tmp
            / ".cache"
            / "vscode-loc"
            / "i18n"
            / "vscode-language-pack-qps-ploc"
            / "package.json"
        )
        self._write_json(
            qps_package_path,
            {
                "contributes": {
                    "localizations": [
                        {
                            "languageId": "qps-ploc",
                            "translations": [],
                        }
                    ]
                }
            },
        )
        prompt_path = self.tmp / "prompts" / "translation" / "vscode-glossary-terms.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text("- Command Palette\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "pseudo-localization"):
            run_generate_vscode_glossary(
                self.tmp,
                "qps-ploc",
                ".cache/vscode-loc",
                ".cache/vscode-upstream",
                "prompts/translation/vscode-glossary-terms.md",
                None,
                "prompts/translation/glossary",
            )
        self.assertFalse(
            (self.tmp / "prompts" / "translation" / "glossary" / "qps-ploc.md").exists()
        )

    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_project_config(self) -> None:
        config_path = self.tmp / "config" / "project.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            "\n".join(
                [
                    'zed_version = "v1.0.1"',
                    'zed_repository = "https://github.com/zed-industries/zed"',
                    'cache_dir = ".cache/zed"',
                    "",
                ]
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
