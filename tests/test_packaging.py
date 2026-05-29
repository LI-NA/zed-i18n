import json
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.packaging import (
    generate_homebrew_cask,
    generate_packaging_files,
    generate_scoop_manifests,
)


def release_asset(
    name: str,
    kind: str,
    locale: str,
    platform: str,
    arch: str,
    sha256: str,
) -> dict[str, object]:
    return {
        "name": name,
        "kind": kind,
        "locale": locale,
        "platform": platform,
        "arch": arch,
        "size": 123,
        "sha256": sha256,
        "download_url": f"https://github.com/LI-NA/zed-i18n/releases/download/v1.4.4-i18n.2/{name}",
    }


def sample_manifest(locales: tuple[str, ...] = ("ja-JP", "ko-KR")) -> dict[str, object]:
    assets: list[dict[str, object]] = []
    for locale in locales:
        assets.extend(
            [
                release_asset(
                    f"Zed-i18n-{locale}-macos-aarch64.dmg",
                    "app",
                    locale,
                    "macos",
                    "aarch64",
                    f"mac-arm-{locale}",
                ),
                release_asset(
                    f"Zed-i18n-{locale}-macos-x86_64.dmg",
                    "app",
                    locale,
                    "macos",
                    "x86_64",
                    f"mac-intel-{locale}",
                ),
                release_asset(
                    f"Zed-i18n-{locale}-windows-aarch64.zip",
                    "portable_app",
                    locale,
                    "windows",
                    "aarch64",
                    f"win-arm-{locale}",
                ),
                release_asset(
                    f"Zed-i18n-{locale}-windows-x86_64.zip",
                    "portable_app",
                    locale,
                    "windows",
                    "x86_64",
                    f"win-x64-{locale}",
                ),
            ]
        )
    return {
        "schema": 2,
        "zed_version": "v1.4.4",
        "i18n_revision": 2,
        "release_tag": "v1.4.4-i18n.2",
        "repository": "LI-NA/zed-i18n",
        "asset_count": len(assets),
        "assets": assets,
    }


class PackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generates_homebrew_cask_with_csv_version_and_language_assets(self) -> None:
        cask = generate_homebrew_cask(sample_manifest())

        self.assertIn('version "1.4.4,2"', cask)
        self.assertIn("v#{version.csv.first}-i18n.#{version.csv.second}", cask)
        self.assertIn('language "ko", default: true do', cask)
        self.assertIn('language "ja" do', cask)
        self.assertIn('sha256 arm: "mac-arm-ko-KR", intel: "mac-intel-ko-KR"', cask)
        self.assertIn('binary "#{appdir}/Zed i18n.app/Contents/MacOS/cli", target: "zed-i18n"', cask)
        self.assertIn("auto_updates true", cask)
        self.assertTrue(cask.endswith("\n"))

    def test_homebrew_uses_region_aware_language_args(self) -> None:
        cask = generate_homebrew_cask(sample_manifest(("pt-BR", "zh-CN", "zh-TW")))

        self.assertIn('language "pt", "BR" do', cask)
        self.assertIn('language "zh", "CN" do', cask)
        self.assertIn('language "zh", "TW" do', cask)

    def test_generates_scoop_manifests_with_alias_and_no_pre_uninstall(self) -> None:
        manifests = generate_scoop_manifests(sample_manifest())

        self.assertEqual(sorted(manifests), ["zed-i18n-ja-JP.json", "zed-i18n-ko-KR.json"])
        ko_manifest = json.loads(manifests["zed-i18n-ko-KR.json"])
        self.assertEqual(ko_manifest["version"], "1.4.4-i18n.2")
        self.assertEqual(ko_manifest["bin"], [["bin\\zed.exe", "zed-i18n"]])
        self.assertNotIn("pre_uninstall", ko_manifest)
        self.assertIn("post_install", ko_manifest)
        self.assertTrue(
            all("? (Get-Content" not in line for line in ko_manifest["post_install"]),
            "post_install should use Windows PowerShell 5.1-compatible syntax",
        )
        post_install = "\n".join(ko_manifest["post_install"])
        self.assertNotIn("Set-Content $cfg -Encoding UTF8", post_install)
        self.assertIn(
            "[System.IO.File]::WriteAllText($cfg, ($j | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding $false))",
            post_install,
        )
        self.assertEqual(
            ko_manifest["checkver"],
            {
                "url": "https://github.com/LI-NA/zed-i18n/releases/latest",
                "regex": "/releases/tag/v([\\d.]+-i18n\\.\\d+)",
            },
        )
        self.assertEqual(
            ko_manifest["architecture"]["64bit"]["url"],
            "https://github.com/LI-NA/zed-i18n/releases/download/v1.4.4-i18n.2/Zed-i18n-ko-KR-windows-x86_64.zip",
        )

    def test_generate_packaging_files_writes_cask_and_bucket_files(self) -> None:
        manifest_path = self.tmp / "manifest.json"
        cask_path = self.tmp / "homebrew" / "Casks" / "zed-i18n.rb"
        bucket_path = self.tmp / "scoop" / "bucket"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(sample_manifest()), encoding="utf-8")

        generate_packaging_files(manifest_path, cask_path, bucket_path)

        self.assertIn('cask "zed-i18n"', cask_path.read_text(encoding="utf-8"))
        self.assertTrue((bucket_path / "zed-i18n-ja-JP.json").exists())
        self.assertTrue((bucket_path / "zed-i18n-ko-KR.json").exists())

    def test_generate_packaging_files_rejects_partial_release_when_expected_locales_are_set(
        self,
    ) -> None:
        manifest_path = self.tmp / "manifest.json"
        cask_path = self.tmp / "homebrew" / "Casks" / "zed-i18n.rb"
        bucket_path = self.tmp / "scoop" / "bucket"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(sample_manifest(("ko-KR",))), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing locales: ja-JP"):
            generate_packaging_files(
                manifest_path,
                cask_path,
                bucket_path,
                expected_locales={"ja-JP", "ko-KR"},
            )

        self.assertFalse(cask_path.exists())
        self.assertFalse(bucket_path.exists())

    def test_missing_required_architecture_fails(self) -> None:
        manifest = sample_manifest(("ko-KR",))
        manifest["assets"] = [
            asset
            for asset in manifest["assets"]
            if not (asset["platform"] == "macos" and asset["arch"] == "x86_64")
        ]

        with self.assertRaisesRegex(ValueError, "missing macos asset"):
            generate_homebrew_cask(manifest)


class PackagingWorkflowTests(unittest.TestCase):
    def test_update_packaging_workflow_runs_when_release_is_published(self) -> None:
        workflow = (Path.cwd() / ".github" / "workflows" / "i18n-update-packaging.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("release:", workflow)
        self.assertIn("types: [published]", workflow)
        self.assertIn(
            "uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2",
            workflow,
        )
        first_checkout = workflow.split("- name: Checkout zed-i18n", 1)[1].split(
            "- name: Setup uv",
            1,
        )[0]
        self.assertIn("persist-credentials: false", first_checkout)
        self.assertIn(
            "uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0",
            workflow,
        )
        self.assertIn("PACKAGING_REPOS_TOKEN", workflow)
        self.assertIn("gh release download", workflow)
        self.assertIn("Published release is not the repository latest release", workflow)
        self.assertIn("manifest.json", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn("uv run zed-i18n generate-packaging", workflow)
        self.assertIn("--require-all-translations", workflow)
        self.assertIn("LI-NA/homebrew-zed-i18n", workflow)
        self.assertIn("LI-NA/scoop-zed-i18n", workflow)
        self.assertIn("diff --cached --quiet", workflow)
