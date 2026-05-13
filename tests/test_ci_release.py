import json
from unittest.mock import patch
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.ci_release import (
    app_source_path,
    build_matrix,
    bundle_env,
    classify_asset,
    expected_app_asset_names,
    generate_release_metadata,
    list_translation_languages,
    patch_remote_server_build,
    runner_override_env_name,
    SIGNING_ENV_VARS,
    select_platforms,
    windows_signing_env_complete,
)
from tools.zed_i18n.distribution import DistributionConfig


class CiReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        (self.temp_root / "translations").mkdir(parents=True)
        (self.temp_root / "config").mkdir()
        (self.temp_root / "config" / "project.toml").write_text(
            'zed_version = "v1.2.3"\n'
            'zed_repository = "https://github.com/zed-industries/zed"\n'
            'cache_dir = ".cache/zed"\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def write_translation(self, language: str) -> None:
        (self.temp_root / "translations" / f"{language}.json").write_text(
            "{}\n",
            encoding="utf-8",
        )

    def write_zed_cargo_toml(self) -> None:
        cargo_toml = self.temp_root / "crates" / "zed" / "Cargo.toml"
        cargo_toml.parent.mkdir(parents=True)
        cargo_toml.write_text('[package]\nname = "zed"\nversion = "1.2.3"\n', encoding="utf-8")

    def test_lists_translation_languages_from_json_files(self) -> None:
        self.write_translation("ko-KR")
        self.write_translation("de-DE")
        (self.temp_root / "translations" / "README.md").write_text("", encoding="utf-8")

        self.assertEqual(list_translation_languages(self.temp_root), ["de-DE", "ko-KR"])

    def test_build_matrix_shards_languages_for_each_platform(self) -> None:
        for language in ["cs-CZ", "de-DE", "es-ES", "fr-FR", "ko-KR"]:
            self.write_translation(language)

        languages, rows = build_matrix(
            self.temp_root,
            language_spec="all",
            platform_spec="linux-x86_64,macos-aarch64",
            shard_size=2,
        )

        self.assertEqual(languages, ["cs-CZ", "de-DE", "es-ES", "fr-FR", "ko-KR"])
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["languages"], "cs-CZ,de-DE")
        self.assertNotIn("include_remote", rows[0])
        self.assertEqual(rows[3]["platform"], "macos")
        self.assertEqual(rows[3]["runner"], "macos-15")

    def test_select_platform_family_expands_to_architectures(self) -> None:
        platforms = select_platforms("linux,windows-x86_64")

        self.assertEqual(
            [platform.id for platform in platforms],
            ["linux-x86_64", "linux-aarch64", "windows-x86_64"],
        )

    def test_build_matrix_allows_runner_overrides_from_environment(self) -> None:
        self.write_translation("ko-KR")
        env = {runner_override_env_name("windows-x86_64"): "self-32vcpu-windows-2022"}

        with patch.dict("os.environ", env, clear=False):
            _, rows = build_matrix(
                self.temp_root,
                language_spec="ko-KR",
                platform_spec="windows-x86_64",
            )

        self.assertEqual(rows[0]["runner"], "self-32vcpu-windows-2022")

    def test_build_matrix_allows_json_runner_label_overrides(self) -> None:
        self.write_translation("ko-KR")
        env = {runner_override_env_name("windows-x86_64"): '["self-hosted","Windows","X64"]'}

        with patch.dict("os.environ", env, clear=False):
            _, rows = build_matrix(
                self.temp_root,
                language_spec="ko-KR",
                platform_spec="windows-x86_64",
            )

        self.assertEqual(rows[0]["runner"], ["self-hosted", "Windows", "X64"])

    def test_classifies_only_app_assets(self) -> None:
        self.assertEqual(
            classify_asset(Path("zed-ko-KR-linux-x86_64.tar.gz")),
            {
                "name": "zed-ko-KR-linux-x86_64.tar.gz",
                "kind": "app",
                "locale": "ko-KR",
                "platform": "linux",
                "arch": "x86_64",
            },
        )
        with self.assertRaises(ValueError):
            classify_asset(Path("zed-remote-server-windows-aarch64.zip"))

    def test_generates_manifest_and_checksums(self) -> None:
        dist_dir = self.temp_root / "dist"
        dist_dir.mkdir()
        (dist_dir / "zed-ko-KR-linux-x86_64.tar.gz").write_text("app", encoding="utf-8")
        (dist_dir / "zed-remote-server-linux-x86_64.gz").write_text("server", encoding="utf-8")

        generate_release_metadata(
            root=self.temp_root,
            dist_dir=dist_dir,
            manifest_path=dist_dir / "manifest.json",
            checksums_path=dist_dir / "SHA256SUMS.txt",
            release_tag="v1.2.3-i18n.1",
            repository="owner/repo",
            run_id="123",
        )

        manifest = json.loads((dist_dir / "manifest.json").read_text(encoding="utf-8"))
        checksums = (dist_dir / "SHA256SUMS.txt").read_text(encoding="utf-8")

        self.assertEqual(manifest["zed_version"], "v1.2.3")
        self.assertEqual(manifest["release_tag"], "v1.2.3-i18n.1")
        self.assertEqual(manifest["asset_count"], 1)
        self.assertEqual([asset["kind"] for asset in manifest["assets"]], ["app"])
        self.assertIn("zed-ko-KR-linux-x86_64.tar.gz", checksums)
        self.assertNotIn("zed-remote-server-linux-x86_64.gz", checksums)

    def test_expected_app_asset_names_follow_selected_languages_and_platforms(self) -> None:
        platforms = select_platforms("linux-x86_64,windows-aarch64")

        self.assertEqual(
            expected_app_asset_names(["ko-KR", "ja-JP"], platforms),
            [
                "Zed-ja-JP-windows-aarch64.exe",
                "Zed-ko-KR-windows-aarch64.exe",
                "zed-ja-JP-linux-x86_64.tar.gz",
                "zed-ko-KR-linux-x86_64.tar.gz",
            ],
        )

    def test_release_metadata_rejects_missing_expected_assets(self) -> None:
        dist_dir = self.temp_root / "dist"
        dist_dir.mkdir()
        (dist_dir / "zed-ko-KR-linux-x86_64.tar.gz").write_text("app", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing expected release assets"):
            generate_release_metadata(
                root=self.temp_root,
                dist_dir=dist_dir,
                manifest_path=dist_dir / "manifest.json",
                checksums_path=dist_dir / "SHA256SUMS.txt",
                release_tag="v1.2.3-i18n.1",
                repository="owner/repo",
                run_id="123",
                expected_assets=[
                    "zed-ko-KR-linux-x86_64.tar.gz",
                    "Zed-ko-KR-windows-x86_64.exe",
                ],
            )

    def test_manifest_includes_update_urls_and_i18n_revision(self) -> None:
        dist_dir = self.temp_root / "dist"
        dist_dir.mkdir()
        (dist_dir / "Zed-ko-KR-windows-x86_64.exe").write_text("app", encoding="utf-8")

        generate_release_metadata(
            root=self.temp_root,
            dist_dir=dist_dir,
            manifest_path=dist_dir / "manifest.json",
            checksums_path=dist_dir / "SHA256SUMS.txt",
            release_tag="v1.2.3-i18n.5",
            repository="owner/repo",
            run_id="123",
        )

        manifest = json.loads((dist_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["i18n_revision"], 5)
        self.assertEqual(
            manifest["latest_manifest_url"],
            "https://github.com/owner/repo/releases/latest/download/manifest.json",
        )
        self.assertEqual(
            manifest["assets"][0]["download_url"],
            "https://github.com/owner/repo/releases/download/v1.2.3-i18n.5/Zed-ko-KR-windows-x86_64.exe",
        )

    def test_windows_app_source_path_uses_distribution_setup_name(self) -> None:
        config = DistributionConfig(windows_setup_name="Zed-i18n")

        self.assertEqual(
            app_source_path(self.temp_root, "windows", "x86_64", config),
            self.temp_root / "target" / "Zed-i18n-x86_64.exe",
        )

    def test_windows_bundle_env_disables_ci_signing_when_values_are_empty(self) -> None:
        self.write_zed_cargo_toml()
        env = {"CI": "true", **{name: "" for name in SIGNING_ENV_VARS}}

        self.assertFalse(windows_signing_env_complete(env))
        with patch.dict("os.environ", env, clear=True):
            bundle = bundle_env(self.temp_root, "windows")

        self.assertNotIn("CI", bundle)

    def test_release_workflow_enables_distribution_patches_for_tag_pushes(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("DISTRIBUTION_PATCHES_ENABLED", workflow)
        self.assertIn(
            "github.event_name != 'workflow_dispatch' || inputs.distribution_patches",
            workflow,
        )
        self.assertNotIn("inputs.distribution_patches == false && ''", workflow)

    def test_release_workflow_uses_clear_publish_boundary(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("  publish:\n    name: Publish GitHub Release", workflow)
        self.assertIn("    permissions:\n      contents: write", workflow)
        self.assertIn("    environment:\n      name: release", workflow)
        self.assertIn("--verify-tag", workflow)
        self.assertNotIn("--clobber", workflow)

    def test_release_workflow_attests_release_artifacts(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("attestations: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("actions/attest@281a49d4cbb0a72c9575a50d18f6deb515a11deb", workflow)
        self.assertIn("subject-path: release-artifacts/*", workflow)

    def test_release_workflow_pins_actions_to_full_commit_shas(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotRegex(workflow, r"uses:\s+[^#\n]+@v\d")
        self.assertIn("actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5", workflow)
        self.assertIn("astral-sh/setup-uv@e58605a9b6da7c637471fab8847a5e5a6b8df081", workflow)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", workflow)

    def test_patches_bundle_scripts_to_skip_remote_server_build(self) -> None:
        script_dir = self.temp_root / "script"
        script_dir.mkdir(parents=True)
        (script_dir / "bundle-linux").write_text(
            """
cargo build --release --target "${remote_server_triple}" --package remote_server
llvm-objcopy --strip-debug "${target_dir}/${remote_server_triple}/release/remote_server"
gzip -f --stdout --best "${target_dir}/${remote_server_triple}/release/remote_server" > "${target_dir}/zed-remote-server-linux-${arch}.gz"
""".lstrip(),
            encoding="utf-8",
        )
        (script_dir / "bundle-mac").write_text(
            """
cargo build ${build_flag} --package remote_server --target $target_triple
sign_binary "target/$target_triple/release/remote_server"
gzip -f --stdout --best target/$target_triple/release/remote_server > target/zed-remote-server-macos-$arch_suffix.gz
""".lstrip(),
            encoding="utf-8",
        )
        (script_dir / "bundle-windows.ps1").write_text(
            """
BuildZedAndItsFriends
BuildRemoteServer
ZipZedAndItsFriendsDebug
""".lstrip(),
            encoding="utf-8",
        )

        patch_remote_server_build(self.temp_root, "linux")
        patch_remote_server_build(self.temp_root, "macos")
        patch_remote_server_build(self.temp_root, "windows")

        linux = (script_dir / "bundle-linux").read_text(encoding="utf-8")
        macos = (script_dir / "bundle-mac").read_text(encoding="utf-8")
        windows = (script_dir / "bundle-windows.ps1").read_text(encoding="utf-8")
        self.assertNotIn("--package remote_server", linux)
        self.assertNotIn("zed-remote-server-linux", linux)
        self.assertNotIn("--package remote_server", macos)
        self.assertNotIn("zed-remote-server-macos", macos)
        self.assertNotIn("BuildRemoteServer", windows)


if __name__ == "__main__":
    unittest.main()
