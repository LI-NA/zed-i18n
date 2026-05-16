import os
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.ci_release import patch_remote_server_build
from tools.zed_i18n.config import load_project_config, zed_checkout_path
from tools.zed_i18n.distribution import apply_distribution_patches, load_distribution_config


PATCH_TARGETS = (
    "crates/zed/src/zed.rs",
    "crates/release_channel/src/lib.rs",
    "crates/zed/Cargo.toml",
    "script/bundle-linux",
    "script/bundle-mac",
    "script/bundle-windows.ps1",
    "crates/windows_resources/src/windows_resources.rs",
    "crates/explorer_command_injector/AppxManifest.xml",
    "crates/zed/resources/windows/zed.iss",
    "crates/auto_update/src/auto_update.rs",
    "crates/zed/src/zed/app_menus.rs",
)


class ZedPatchContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd()
        self.require_contract = os.environ.get("ZED_I18N_REQUIRE_ZED_PATCH_CONTRACT") == "1"
        self.source_zed_root = self.resolve_source_zed_root()
        self.temp_root = self.root / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self.zed_root = self.temp_root / "zed"
        self.copy_patch_targets()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def resolve_source_zed_root(self) -> Path:
        override = os.environ.get("ZED_I18N_PATCH_CONTRACT_ZED_ROOT")
        if override:
            path = Path(override)
            if not path.is_absolute():
                path = self.root / path
        else:
            path = zed_checkout_path(self.root, load_project_config(self.root))

        if path.exists():
            return path
        if self.require_contract:
            self.fail(f"required Zed patch contract checkout does not exist: {path}")
        self.skipTest(f"Zed checkout not available for patch contract test: {path}")

    def copy_patch_targets(self) -> None:
        for relative in PATCH_TARGETS:
            source = self.source_zed_root / relative
            if not source.exists():
                message = f"required Zed patch target does not exist: {source}"
                if self.require_contract:
                    self.fail(message)
                self.skipTest(message)
            destination = self.zed_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def test_current_zed_checkout_accepts_release_patch_sequence(self) -> None:
        config = load_distribution_config(self.root / "config" / "distribution.toml")

        apply_distribution_patches(self.zed_root, config)
        for platform in ("linux", "macos", "windows"):
            patch_remote_server_build(self.zed_root, platform)
        apply_distribution_patches(self.zed_root, config)
        for platform in ("linux", "macos", "windows"):
            patch_remote_server_build(self.zed_root, platform)

        zed_rs = (self.zed_root / "crates/zed/src/zed.rs").read_text(encoding="utf-8")
        release_channel = (
            self.zed_root / "crates/release_channel/src/lib.rs"
        ).read_text(encoding="utf-8")
        zed_cargo_toml = (self.zed_root / "crates/zed/Cargo.toml").read_text(
            encoding="utf-8"
        )
        auto_update = (
            self.zed_root / "crates/auto_update/src/auto_update.rs"
        ).read_text(encoding="utf-8")
        bundle_linux = (self.zed_root / "script/bundle-linux").read_text(encoding="utf-8")
        bundle_macos = (self.zed_root / "script/bundle-mac").read_text(encoding="utf-8")
        bundle_windows = (
            self.zed_root / "script/bundle-windows.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("i18n_build: Option<SharedString>", zed_rs)
        self.assertIn('ReleaseChannel::Stable => "dev.zed-i18n.Zed"', release_channel)
        self.assertIn('identifier = "dev.zed-i18n.Zed"', zed_cargo_toml)
        self.assertIn("get_i18n_release_asset", auto_update)
        self.assertNotIn("--package remote_server", bundle_linux)
        self.assertNotIn("--package remote_server", bundle_macos)
        self.assertNotIn("BuildRemoteServer", bundle_windows)
        self.assertIn("function create_dmg_with_retry()", bundle_macos)
        self.assertEqual(bundle_macos.count("function create_dmg_with_retry()"), 1)
        self.assertIn(
            'create_dmg_with_retry "${dmg_source_directory}" "${dmg_file_path}"',
            bundle_macos,
        )
        self.assertEqual(
            bundle_macos.count('create_dmg_with_retry "${dmg_source_directory}" "${dmg_file_path}"'),
            1,
        )
        self.assertIn("for attempt in 1 2 3; do", bundle_macos)
        self.assertIn('rm -f "${source_directory}/Applications"', bundle_macos)
        self.assertIn('rm -f "${source_directory}/Applications" || true', bundle_macos)
        self.assertIn('ln -s /Applications "${source_directory}/Applications"', bundle_macos)
        self.assertIn('rm -f "$file_path" || true', bundle_macos)
        self.assertIn('hdiutil detach "$device" -force || true', bundle_macos)
        self.assertIn("Retrying git binary download", bundle_macos)
        self.assertIn("|| rc=$?", bundle_macos)
        self.assertIn('if mv "${tmp_dir}/git" "${target_binary}"; then', bundle_macos)
        self.assertIn('rm -rf "$tmp_dir"', bundle_macos)


if __name__ == "__main__":
    unittest.main()
