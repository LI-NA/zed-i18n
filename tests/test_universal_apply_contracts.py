"""Contract test for the real universal release apply sequence.

Runs `generate-runtime-bundles` -> `apply-universal` -> distribution patches
against an actual Zed build checkout, exactly as `ci_release build-shard
--mode universal` does before building.

Opt-in: set ZED_I18N_UNIVERSAL_CONTRACT_ZED_ROOT to a Zed build checkout that
the test may freely mutate; it is restored with `git reset --hard` plus
`git clean -fd` before and after. The release pipeline itself only runs
`git reset --hard` (plus marker removal); the extra `git clean -fd` here
also drops the untracked outputs (assets/locales, overlay crates) so the
checkout returns to its pristine state, while the ignored target/ build
cache stays untouched. Set ZED_I18N_REQUIRE_UNIVERSAL_CONTRACT=1 to fail
instead of skipping when the checkout is unavailable.
"""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from tools.zed_i18n.apply_universal import apply_universal
from tools.zed_i18n.config import load_project_config
from tools.zed_i18n.distribution import apply_distribution_patches, load_distribution_config
from tools.zed_i18n.runtime_bundles import generate_runtime_bundles


class UniversalApplyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd()
        self.require_contract = (
            os.environ.get("ZED_I18N_REQUIRE_UNIVERSAL_CONTRACT") == "1"
        )
        override = os.environ.get("ZED_I18N_UNIVERSAL_CONTRACT_ZED_ROOT")
        if not override:
            message = "ZED_I18N_UNIVERSAL_CONTRACT_ZED_ROOT is not set"
            if self.require_contract:
                self.fail(message)
            self.skipTest(message)

        path = Path(override)
        if not path.is_absolute():
            path = self.root / path
        if not (path / ".git").exists():
            message = f"universal contract checkout is not a git checkout: {path}"
            if self.require_contract:
                self.fail(message)
            self.skipTest(message)
        self.zed_root = path

        # A private global git config keeps the opted-in checkout usable even
        # when its files are owned by another account (safe.directory is only
        # honored from protected config, so `git -c` would not work) without
        # touching the user's real ~/.gitconfig.
        self.temp_dir = self.root / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.git_config_path = self.temp_dir / "gitconfig"
        self.git_config_path.write_text(
            "[safe]\n"
            f"\tdirectory = {self.zed_root.resolve().as_posix()}\n"
            "[core]\n"
            "\tlongpaths = true\n",
            encoding="utf-8",
        )

    def run_git(self, *args: str) -> None:
        env = dict(os.environ)
        env["GIT_CONFIG_GLOBAL"] = str(self.git_config_path)
        subprocess.run(["git", *args], cwd=self.zed_root, check=True, env=env)

    def restore_checkout(self) -> None:
        self.run_git("reset", "--hard")
        self.run_git("clean", "-fd")

    def test_release_apply_sequence_patches_a_pristine_checkout(self) -> None:
        self.restore_checkout()
        self.addCleanup(self.restore_checkout)

        project = load_project_config(self.root)
        bundle_report = generate_runtime_bundles(self.root, self.zed_root, project)
        self.assertGreater(bundle_report.locale_count, 0)
        self.assertGreater(bundle_report.message_count, 0)

        manifest = json.loads(
            (self.root / "manifest" / "ui-strings.json").read_text(encoding="utf-8")
        )
        report = apply_universal(self.root, self.zed_root, manifest)
        self.assertTrue(report.ok)
        self.assertFalse(report.already_applied)
        self.assertGreater(report.applied_occurrences, 0)

        config = load_distribution_config(self.root / "config" / "distribution.toml")
        apply_distribution_patches(self.zed_root, config)
        apply_distribution_patches(self.zed_root, config)

        app_menus = (
            self.zed_root / "crates" / "zed" / "src" / "zed" / "app_menus.rs"
        ).read_text(encoding="utf-8")
        self.assertIn("localization::localized_str!", app_menus)
        if config.publisher_url:
            self.assertEqual(app_menus.count(config.publisher_url), 1)
            self.assertIn(
                'localization::localized_str!("Zed Repository").replacen(',
                app_menus,
            )
            self.assertNotIn('                "Zed-i18n Repository",', app_menus)

        zed_rs = (self.zed_root / "crates" / "zed" / "src" / "zed.rs").read_text(
            encoding="utf-8"
        )
        self.assertIn("i18n_build: Option<SharedString>", zed_rs)
        self.assertIn("mod ui_locale;", zed_rs)
        self.assertIn("initialize_localization", zed_rs)
        self.assertTrue(
            (self.zed_root / "assets" / "locales" / "index.json").exists()
        )


if __name__ == "__main__":
    unittest.main()
