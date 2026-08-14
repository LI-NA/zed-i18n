import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import call, patch

from tools.zed_i18n.cli import (
    build_parser,
    main,
    preserve_manifest_statuses,
    resolve_runtime_zed_root,
    resolve_zed_root,
    run_apply_universal,
    run_fetch_zed,
    run_generate_runtime_bundles,
    run_prepare_translation,
    run_validate,
)
from tools.zed_i18n.apply_universal import UniversalApplyReport
from tools.zed_i18n.config import ProjectConfig
from tools.zed_i18n.runtime_bundles import RuntimeBundleReport
from tools.zed_i18n.translation_pipeline import PrepareTranslationReport
from tools.zed_i18n.version_diff import GeneratedVersionDiff


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
        self.assertFalse(hasattr(prepare_args, "current_version"))
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
        self.assertEqual(
            parser.parse_args(
                [
                    "extract-context-groups",
                    "--language",
                    "ko-KR",
                    "--group-type",
                    "prompt",
                ]
            ).group_type,
            "prompt",
        )
        packaging_args = parser.parse_args(
            [
                "generate-packaging",
                "--manifest",
                "release-assets/manifest.json",
                "--cask-out",
                "packaging/homebrew/Casks/zed-i18n.rb",
                "--bucket-out",
                "packaging/scoop/bucket",
                "--require-all-translations",
            ]
        )
        self.assertEqual(packaging_args.command, "generate-packaging")
        self.assertEqual(packaging_args.manifest, "release-assets/manifest.json")
        self.assertEqual(packaging_args.cask_out, "packaging/homebrew/Casks/zed-i18n.rb")
        self.assertEqual(packaging_args.bucket_out, "packaging/scoop/bucket")
        self.assertTrue(packaging_args.require_all_translations)

    def test_parser_accepts_generate_version_diff_default_and_explicit_base_ref(self) -> None:
        parser = build_parser()

        default_args = parser.parse_args(["generate-version-diff"])
        explicit_args = parser.parse_args(
            ["generate-version-diff", "--base-ref", "release/v1"]
        )

        self.assertEqual(default_args.command, "generate-version-diff")
        self.assertEqual(default_args.base_ref, "HEAD")
        self.assertEqual(explicit_args.base_ref, "release/v1")

    def test_parser_accepts_runtime_commands_without_a_locale(self) -> None:
        parser = build_parser()

        generate = parser.parse_args(
            ["generate-runtime-bundles", "--zed-root", ".cache/zed/v1.0.1"]
        )
        apply = parser.parse_args(["apply-universal"])

        self.assertEqual(generate.command, "generate-runtime-bundles")
        self.assertEqual(generate.zed_root, ".cache/zed/v1.0.1")
        self.assertFalse(hasattr(generate, "language"))
        self.assertEqual(apply.command, "apply-universal")
        self.assertIsNone(apply.zed_root)
        self.assertFalse(hasattr(apply, "language"))

    def test_runtime_commands_use_the_build_checkout_and_report_results(self) -> None:
        config = ProjectConfig(
            zed_version="v1.0.1",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )
        checkout = self.tmp / ".cache/zed/v1.0.1"
        bundle_report = RuntimeBundleReport(
            catalog_sha256="abc",
            locale_count=14,
            message_count=100,
            format_count=20,
            joined_message_count=3,
            raw_payload_bytes=4096,
            output_files=("assets/locales/index.json",),
        )
        apply_report = UniversalApplyReport(
            ok=True,
            already_applied=True,
            applied_occurrences=0,
            dependency_crates=("ui",),
            manifest_sha256="def",
        )
        self._write_json(
            self.tmp / "manifest/ui-strings.json",
            {"Open Settings": {"status": "accepted", "occurrences": []}},
        )

        with (
            patch("tools.zed_i18n.cli.load_project_config", return_value=config),
            patch(
                "tools.zed_i18n.cli.resolve_runtime_zed_root",
                return_value=checkout,
            ) as resolve,
            patch(
                "tools.zed_i18n.cli.generate_runtime_bundles",
                return_value=bundle_report,
            ) as generate,
            patch(
                "tools.zed_i18n.cli.apply_universal",
                return_value=apply_report,
            ) as apply,
            patch("builtins.print") as print_output,
        ):
            self.assertEqual(run_generate_runtime_bundles(self.tmp, None), 0)
            self.assertEqual(run_apply_universal(self.tmp, None), 0)

        self.assertEqual(resolve.call_args_list, [call(self.tmp, config, None)] * 2)
        generate.assert_called_once_with(self.tmp, checkout, config)
        apply.assert_called_once()
        self.assertEqual(apply.call_args.args[0:2], (self.tmp, checkout))
        self.assertIn("14 locales", print_output.call_args_list[0].args[0])
        self.assertIn("already applied", print_output.call_args_list[1].args[0])

    def test_runtime_zed_root_defaults_to_build_checkout_and_stays_in_workspace(self) -> None:
        root = Path.cwd()
        config = ProjectConfig(
            zed_version="v1.0.1",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )

        self.assertEqual(
            resolve_runtime_zed_root(root, config, None),
            (root / ".cache/zed/v1.0.1").resolve(),
        )
        with self.assertRaises(ValueError):
            resolve_runtime_zed_root(root, config, "..")

    def test_main_runs_generate_version_diff_and_prints_summary(self) -> None:
        output_path = (
            self.tmp
            / "reports"
            / "version-diff"
            / "v1-to-v2"
            / "key-changes.json"
        )
        generated = GeneratedVersionDiff(
            output_path=output_path,
            report={
                "summary": {"added": 2, "deleted": 1, "candidate_pairs": 3}
            },
        )

        with (
            patch(
                "tools.zed_i18n.cli.generate_version_diff",
                return_value=generated,
            ) as generate,
            patch("builtins.print") as print_output,
        ):
            exit_code = main(
                [
                    "--root",
                    str(self.tmp),
                    "generate-version-diff",
                    "--base-ref",
                    "release/v1",
                ]
            )

        self.assertEqual(exit_code, 0)
        generate.assert_called_once_with(self.tmp.resolve(), base_ref="release/v1")
        print_output.assert_called_once()
        message = print_output.call_args.args[0]
        for expected in (
            "2 added",
            "1 deleted",
            "3 candidates",
            "reports/version-diff/v1-to-v2/key-changes.json",
        ):
            self.assertIn(expected, message)

    def test_prepare_translation_passes_the_configured_current_version(self) -> None:
        config = ProjectConfig(
            zed_version="v2.0.0",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )
        checkout = self.tmp / ".cache" / "zed" / "v2.0.0-clean-extract"
        prepared = PrepareTranslationReport(
            language="ko-KR",
            source_count=1,
            batch_count=1,
            output_dir="custom-output",
        )

        with (
            patch("tools.zed_i18n.cli.load_project_config", return_value=config) as load,
            patch("tools.zed_i18n.cli.resolve_zed_root", return_value=checkout),
            patch(
                "tools.zed_i18n.cli.prepare_translation_batches",
                return_value=prepared,
            ) as prepare,
            patch("tools.zed_i18n.cli._write_json"),
            patch("builtins.print"),
        ):
            exit_code = run_prepare_translation(
                self.tmp,
                "ko-KR",
                None,
                40,
                12,
                True,
                "custom-output",
                None,
                None,
                None,
                3,
            )

        self.assertEqual(exit_code, 0)
        load.assert_called_once_with(self.tmp)
        options = prepare.call_args.kwargs["options"]
        self.assertEqual(options.current_version, "v2.0.0")
        self.assertEqual(prepare.call_args.kwargs["zed_root"], checkout)

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
