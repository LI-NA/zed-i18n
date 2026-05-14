import json
from unittest.mock import patch
import shutil
import unittest
from pathlib import Path
import zipfile

from tools.zed_i18n.ci_release import (
    app_source_path,
    build_matrix,
    bundle_env,
    classify_asset,
    configure_github_rust_cache_env,
    create_windows_portable_zip,
    disk_summary_entries,
    expected_app_asset_names,
    generate_release_metadata,
    github_matrix_outputs,
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
        self.assertEqual(
            [row["id"] for row in rows],
            [
                "linux-x86_64-shard-1",
                "linux-x86_64-shard-2",
                "linux-x86_64-shard-3",
                "macos-aarch64-shard-1",
                "macos-aarch64-shard-2",
                "macos-aarch64-shard-3",
            ],
        )
        self.assertEqual(rows[0]["languages"], "cs-CZ,de-DE")
        self.assertNotIn("include_remote", rows[0])
        self.assertEqual(rows[3]["platform"], "macos")
        self.assertEqual(rows[3]["runner"], "macos-15")

    def test_build_matrix_uses_locale_names_for_single_language_shards(self) -> None:
        for language in ["de-DE", "ko-KR"]:
            self.write_translation(language)

        _, rows = build_matrix(
            self.temp_root,
            language_spec="all",
            platform_spec="linux-x86_64",
            shard_size=1,
        )

        self.assertEqual([row["id"] for row in rows], ["linux-x86_64-de-DE", "linux-x86_64-ko-KR"])
        self.assertEqual(
            [row["artifact"] for row in rows],
            ["zed-i18n-linux-x86_64-de-DE", "zed-i18n-linux-x86_64-ko-KR"],
        )
        self.assertEqual([row["languages"] for row in rows], ["de-DE", "ko-KR"])

    def test_build_matrix_defaults_to_single_language_shards(self) -> None:
        for language in ["de-DE", "ko-KR"]:
            self.write_translation(language)

        _, rows = build_matrix(
            self.temp_root,
            language_spec="all",
            platform_spec="linux-x86_64",
        )

        self.assertEqual([row["id"] for row in rows], ["linux-x86_64-de-DE", "linux-x86_64-ko-KR"])

    def test_github_matrix_outputs_split_rows_by_platform(self) -> None:
        for language in ["de-DE", "ko-KR"]:
            self.write_translation(language)

        outputs = github_matrix_outputs(
            self.temp_root,
            language_spec="all",
            platform_spec="linux-x86_64,macos-aarch64,windows-x86_64",
            shard_size=1,
        )

        self.assertEqual(outputs["build-count"], "6")
        self.assertEqual(outputs["linux-build-count"], "2")
        self.assertEqual(outputs["macos-build-count"], "2")
        self.assertEqual(outputs["windows-build-count"], "2")
        linux_matrix = json.loads(outputs["linux-matrix"])
        macos_matrix = json.loads(outputs["macos-matrix"])
        windows_matrix = json.loads(outputs["windows-matrix"])
        self.assertEqual(
            [row["id"] for row in linux_matrix["include"]],
            ["linux-x86_64-de-DE", "linux-x86_64-ko-KR"],
        )
        self.assertEqual(
            [row["id"] for row in macos_matrix["include"]],
            ["macos-aarch64-de-DE", "macos-aarch64-ko-KR"],
        )
        self.assertEqual(
            [row["id"] for row in windows_matrix["include"]],
            ["windows-x86_64-de-DE", "windows-x86_64-ko-KR"],
        )

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

        self.assertEqual(
            classify_asset(Path("Zed-ko-KR-windows-x86_64.zip")),
            {
                "name": "Zed-ko-KR-windows-x86_64.zip",
                "kind": "portable_app",
                "locale": "ko-KR",
                "platform": "windows",
                "arch": "x86_64",
            },
        )

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
                "Zed-ja-JP-windows-aarch64.zip",
                "Zed-ko-KR-windows-aarch64.exe",
                "Zed-ko-KR-windows-aarch64.zip",
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
        (dist_dir / "Zed-ko-KR-windows-x86_64.zip").write_text("portable", encoding="utf-8")

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
        self.assertEqual(manifest["assets"][1]["kind"], "portable_app")
        self.assertEqual(
            manifest["assets"][1]["download_url"],
            "https://github.com/owner/repo/releases/download/v1.2.3-i18n.5/Zed-ko-KR-windows-x86_64.zip",
        )

    def test_windows_app_source_path_uses_distribution_setup_name(self) -> None:
        config = DistributionConfig(windows_setup_name="Zed-i18n")

        self.assertEqual(
            app_source_path(self.temp_root, "windows", "x86_64", config),
            self.temp_root / "target" / "Zed-i18n-x86_64.exe",
        )

    def test_creates_windows_portable_zip_from_installer_payload(self) -> None:
        payload = self.temp_root / "inno" / "x86_64"
        for path in [
            payload / "Zed.exe",
            payload / "bin" / "zed.exe",
            payload / "bin" / "zed",
            payload / "tools" / "auto_update_helper.exe",
            payload / "appx" / "zed_explorer_command_injector.appx",
            payload / "appx" / "zed_explorer_command_injector.dll",
            payload / "x64" / "OpenConsole.exe",
            payload / "arm64" / "OpenConsole.exe",
            payload / "conpty.dll",
            payload / "amd_ags_x64.dll",
            payload / "zed.iss",
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.name, encoding="utf-8")

        destination = self.temp_root / "target" / "Zed-x86_64.zip"
        create_windows_portable_zip(self.temp_root, "x86_64", destination)

        with zipfile.ZipFile(destination) as archive:
            names = sorted(archive.namelist())

        self.assertEqual(
            names,
            [
                "Zed.exe",
                "amd_ags_x64.dll",
                "appx/zed_explorer_command_injector.appx",
                "appx/zed_explorer_command_injector.dll",
                "arm64/OpenConsole.exe",
                "bin/zed",
                "bin/zed.exe",
                "conpty.dll",
                "tools/auto_update_helper.exe",
                "x64/OpenConsole.exe",
            ],
        )

    def test_windows_portable_zip_rejects_incomplete_payload(self) -> None:
        payload = self.temp_root / "inno" / "aarch64"
        for path in [
            payload / "Zed.exe",
            payload / "bin" / "zed.exe",
            payload / "bin" / "zed",
            payload / "tools" / "auto_update_helper.exe",
            payload / "appx" / "zed_explorer_command_injector.appx",
            payload / "appx" / "zed_explorer_command_injector.dll",
            payload / "arm64" / "OpenConsole.exe",
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.name, encoding="utf-8")

        with self.assertRaisesRegex(FileNotFoundError, "conpty.dll"):
            create_windows_portable_zip(
                self.temp_root,
                "aarch64",
                self.temp_root / "target" / "Zed-aarch64.zip",
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

    def test_github_rust_cache_env_writes_linux_paths(self) -> None:
        github_env = self.temp_root / "github-env.txt"
        github_path = self.temp_root / "github-path.txt"
        github_output = self.temp_root / "github-output.txt"
        runner_temp = self.temp_root / "runner-temp"
        cargo_home = runner_temp / "cargo-home"
        cargo_home_output = str(cargo_home).replace("\\", "/")

        with patch.dict(
            "os.environ",
            {
                "GITHUB_ENV": str(github_env),
                "GITHUB_PATH": str(github_path),
                "GITHUB_OUTPUT": str(github_output),
                "GITHUB_WORKSPACE": str(self.temp_root),
                "RUNNER_TEMP": str(runner_temp),
            },
            clear=True,
        ):
            configure_github_rust_cache_env(self.temp_root, "linux")

        self.assertIn(f"CARGO_HOME={cargo_home}", github_env.read_text(encoding="utf-8"))
        self.assertIn("CARGO_NET_GIT_FETCH_WITH_CLI=true", github_env.read_text(encoding="utf-8"))
        self.assertEqual(f"{cargo_home / 'bin'}\n", github_path.read_text(encoding="utf-8"))
        self.assertEqual(f"cargo-home={cargo_home_output}\n", github_output.read_text(encoding="utf-8"))

    def test_disk_summary_entries_use_nearest_existing_path(self) -> None:
        missing_target = self.temp_root / "missing" / "target"

        entries = disk_summary_entries(
            [
                ("workspace", self.temp_root),
                ("target", missing_target),
            ]
        )

        self.assertEqual([entry.label for entry in entries], ["workspace", "target"])
        self.assertEqual(entries[1].path, self.temp_root.resolve())
        self.assertGreater(entries[0].total_bytes, 0)
        self.assertGreater(entries[0].free_bytes, 0)

    def test_release_workflow_configures_github_actions_rust_cache(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Configure Rust cache environment", workflow)
        self.assertIn('rust-cache-env --platform "${{ matrix.platform }}"', workflow)
        self.assertNotIn('rust-cache-env --platform "${{ matrix.platform }}" --arch', workflow)
        self.assertIn("Cache Rust dependencies", workflow)
        self.assertIn("uses: actions/cache@", workflow)
        self.assertIn("registry/cache", workflow)
        self.assertIn("git/db", workflow)
        self.assertNotIn("steps.rust-cache.outputs.cargo-home }}/bin", workflow)
        self.assertNotIn(".crates.toml", workflow)
        self.assertNotIn(".crates2.json", workflow)
        self.assertNotIn("registry/src", workflow)
        self.assertNotIn("git/checkouts", workflow)
        self.assertNotIn("target/sccache", workflow)
        self.assertNotIn("Configure Windows Cargo paths", workflow)
        self.assertNotIn("cargo-paths-posix", workflow)
        self.assertNotIn("cargo-paths-windows", workflow)
        self.assertIn(
            "hashFiles('.cache/zed/**/Cargo.lock', '.cache/zed/**/rust-toolchain.toml')",
            workflow,
        )
        self.assertIn(
            "key: zed-rust-deps-${{ runner.os }}-${{ matrix.platform }}-${{ matrix.arch }}-${{ hashFiles('.cache/zed/**/Cargo.lock', '.cache/zed/**/rust-toolchain.toml') }}",
            workflow,
        )
        self.assertIn(
            "zed-rust-deps-${{ runner.os }}-${{ matrix.platform }}-${{ matrix.arch }}-",
            workflow,
        )
        self.assertIn("zed-rust-deps-${{ runner.os }}-${{ matrix.platform }}-", workflow)
        self.assertNotIn(
            "zed-rust-deps-${{ runner.os }}-${{ matrix.platform }}-${{ needs.prepare.outputs.zed-version }}",
            workflow,
        )
        self.assertNotIn(
            "hashFiles('.cache/zed/**/Cargo.lock', '.cache/zed/**/rust-toolchain.toml', 'config/project.toml')",
            workflow,
        )
        self.assertNotIn("steps.rust-cache.outputs.cache-scope", workflow)
        self.assertNotIn("install-sccache", workflow)
        self.assertNotIn("github-script", workflow)
        self.assertNotIn("configure-sccache-gha", workflow)
        self.assertNotIn("SCCACHE_", workflow)
        self.assertNotIn("RUSTC_WRAPPER", workflow)
        self.assertNotIn("R2_ACCOUNT_ID", workflow)
        self.assertNotIn("R2_ACCESS_KEY_ID", workflow)

    def test_release_workflow_records_disk_space_and_cleans_linux_runners(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Record initial disk space", workflow)
        self.assertIn("disk-summary --label \"initial\"", workflow)
        self.assertIn("build-linux:", workflow)
        self.assertIn("Clean Linux runner disk", workflow)
        self.assertIn("sudo rm -rf /usr/local/lib/android", workflow)
        self.assertIn("sudo rm -rf /usr/share/dotnet", workflow)
        self.assertIn("Record disk space after Linux cleanup", workflow)
        self.assertIn("disk-summary --label \"after-linux-cleanup\"", workflow)

    def test_release_workflow_cleans_only_macos_core_simulator(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("Clean macOS CoreSimulator", workflow)
        self.assertIn("build-macos:", workflow)
        self.assertIn("sudo rm -rf /Library/Developer/CoreSimulator", workflow)
        self.assertNotIn("sudo rm -rf /opt/homebrew", workflow)
        self.assertNotIn("sudo rm -rf /Users/runner/hostedtoolcache", workflow)

    def test_release_workflow_defaults_tag_pushes_to_single_language_shards(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("SHARD_SIZE: ${{ inputs.shard_size || '1' }}", workflow)
        self.assertIn("name: Build Linux ${{ matrix.id }}", workflow)
        self.assertIn("name: Build macOS ${{ matrix.id }}", workflow)
        self.assertIn("name: Build Windows ${{ matrix.id }}", workflow)
        self.assertNotIn("SHARD_SIZE: ${{ inputs.shard_size || '4' }}", workflow)

    def test_release_workflow_splits_build_jobs_by_platform(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )
        workflow = workflow.replace("\r\n", "\n")

        self.assertIn("linux-matrix: ${{ steps.matrix.outputs.linux-matrix }}", workflow)
        self.assertIn("macos-matrix: ${{ steps.matrix.outputs.macos-matrix }}", workflow)
        self.assertIn("windows-matrix: ${{ steps.matrix.outputs.windows-matrix }}", workflow)
        self.assertIn("build-linux:", workflow)
        self.assertIn("build-macos:", workflow)
        self.assertIn("build-windows:", workflow)
        self.assertIn("matrix: ${{ fromJson(needs.prepare.outputs['linux-matrix']) }}", workflow)
        self.assertIn("matrix: ${{ fromJson(needs.prepare.outputs['macos-matrix']) }}", workflow)
        self.assertIn("matrix: ${{ fromJson(needs.prepare.outputs['windows-matrix']) }}", workflow)
        linux_job = workflow.split("\n  build-linux:\n", 1)[1].split("\n  build-macos:\n", 1)[0]
        macos_job = workflow.split("\n  build-macos:\n", 1)[1].split("\n  build-windows:\n", 1)[0]
        windows_job = workflow.split("\n  build-windows:\n", 1)[1].split("\n  package:\n", 1)[0]
        self.assertIn("max-parallel: 5", linux_job)
        self.assertIn("max-parallel: 5", macos_job)
        self.assertIn("max-parallel: 10", windows_job)
        package_job = workflow.split("\n  package:\n", 1)[1].split("\n  publish:\n", 1)[0]
        self.assertIn("- validate", package_job)
        self.assertIn("needs.validate.result == 'success'", package_job)
        self.assertIn("needs['build-linux'].result != 'failure'", workflow)
        self.assertIn("needs['build-macos'].result != 'failure'", workflow)
        self.assertIn("needs['build-windows'].result != 'failure'", workflow)
        self.assertNotIn("\n  build:\n", workflow)

    def test_release_workflow_pins_actions_to_full_commit_shas(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-release.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotRegex(workflow, r"uses:\s+[^#\n]+@v\d")
        self.assertIn("actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd", workflow)
        self.assertIn("astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b", workflow)
        self.assertIn("actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae", workflow)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", workflow)

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
