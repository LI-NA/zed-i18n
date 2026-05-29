from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any


MACOS_ARCHES = ("aarch64", "x86_64")
WINDOWS_ARCHES = ("aarch64", "x86_64")
DEFAULT_LOCALE = "ko-KR"
RELEASE_TAG_PATTERN = re.compile(r"^v?(?P<base>\d+\.\d+\.\d+)-i18n\.(?P<revision>\d+)$")

HOMEBREW_LANGUAGE_ARGS = {
    "cs-CZ": '"cs"',
    "de-DE": '"de"',
    "es-ES": '"es"',
    "fr-FR": '"fr"',
    "it-IT": '"it"',
    "ja-JP": '"ja"',
    "ko-KR": '"ko", default: true',
    "pl-PL": '"pl"',
    "pt-BR": '"pt", "BR"',
    "ru-RU": '"ru"',
    "tr-TR": '"tr"',
    "zh-CN": '"zh", "CN"',
    "zh-TW": '"zh", "TW"',
}

POST_INSTALL_LINES = [
    "$cfg = Join-Path $env:APPDATA 'Zed\\global_settings.json'",
    "$dir = Split-Path -Parent $cfg",
    "if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }",
    "if ((Test-Path $cfg) -and ((Get-Item $cfg).Length -gt 0)) { $j = Get-Content $cfg -Raw | ConvertFrom-Json } else { $j = [pscustomobject]@{} }",
    "$j | Add-Member -MemberType NoteProperty -Name auto_update -Value $false -Force",
    "[System.IO.File]::WriteAllText($cfg, ($j | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding $false))",
]


def generate_packaging_files(
    manifest_path: Path,
    cask_path: Path,
    bucket_dir: Path,
    expected_locales: Iterable[str] | None = None,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_packaging_release(manifest, expected_locales)

    cask_path.parent.mkdir(parents=True, exist_ok=True)
    cask_path.write_text(generate_homebrew_cask(manifest), encoding="utf-8")

    bucket_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in generate_scoop_manifests(manifest).items():
        (bucket_dir / filename).write_text(content, encoding="utf-8")


def generate_homebrew_cask(manifest: dict[str, Any]) -> str:
    version = cask_version(manifest)
    locales = sorted(_locales_for(manifest, platform="macos", kind="app"))
    if not locales:
        raise ValueError("release manifest has no macos app assets")

    lines = [
        'cask "zed-i18n" do',
        '  arch arm: "aarch64", intel: "x86_64"',
        f'  version "{version}"',
        "",
    ]
    for locale in locales:
        language_args = HOMEBREW_LANGUAGE_ARGS.get(locale) or _fallback_language_args(locale)
        assets = _assets_for_locale(manifest, locale=locale, platform="macos", kind="app")
        arm = _required_asset(assets, "aarch64", locale, "macos")
        intel = _required_asset(assets, "x86_64", locale, "macos")
        lines.extend(
            [
                f"  language {language_args} do",
                f'    sha256 arm: "{arm["sha256"]}", intel: "{intel["sha256"]}"',
                f'    "{locale}"',
                "  end",
            ]
        )
    lines.extend(
        [
            "",
            '  url "https://github.com/LI-NA/zed-i18n/releases/download/v#{version.csv.first}-i18n.#{version.csv.second}/Zed-i18n-#{language}-macos-#{arch}.dmg"',
            '  name "Zed i18n"',
            '  desc "Localized build of the Zed editor"',
            '  homepage "https://github.com/LI-NA/zed-i18n"',
            "",
            '  app "Zed i18n.app"',
            '  binary "#{appdir}/Zed i18n.app/Contents/MacOS/cli", target: "zed-i18n"',
            "",
            "  auto_updates true",
            "end",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_scoop_manifests(manifest: dict[str, Any]) -> dict[str, str]:
    version = scoop_version(manifest)
    locales = sorted(_locales_for(manifest, platform="windows", kind="portable_app"))
    if not locales:
        raise ValueError("release manifest has no windows portable_app assets")

    output = {}
    for locale in locales:
        assets = _assets_for_locale(
            manifest,
            locale=locale,
            platform="windows",
            kind="portable_app",
        )
        x64 = _required_asset(assets, "x86_64", locale, "windows")
        arm64 = _required_asset(assets, "aarch64", locale, "windows")
        app = {
            "version": version,
            "description": f"Localized build of the Zed editor ({locale})",
            "homepage": "https://github.com/LI-NA/zed-i18n",
            "license": "GPL-3.0",
            "architecture": {
                "64bit": {
                    "url": x64["download_url"],
                    "hash": x64["sha256"],
                },
                "arm64": {
                    "url": arm64["download_url"],
                    "hash": arm64["sha256"],
                },
            },
            "bin": [["bin\\zed.exe", "zed-i18n"]],
            "shortcuts": [["Zed.exe", f"Zed i18n ({locale})"]],
            "env_set": {
                "ZED_UPDATE_EXPLANATION": f"Run 'scoop update zed-i18n-{locale}' to update."
            },
            "post_install": POST_INSTALL_LINES,
            "checkver": {
                "url": "https://github.com/LI-NA/zed-i18n/releases/latest",
                "regex": r"/releases/tag/v([\d.]+-i18n\.\d+)",
            },
            "autoupdate": {
                "architecture": {
                    "64bit": {
                        "url": f"https://github.com/LI-NA/zed-i18n/releases/download/v$version/Zed-i18n-{locale}-windows-x86_64.zip"
                    },
                    "arm64": {
                        "url": f"https://github.com/LI-NA/zed-i18n/releases/download/v$version/Zed-i18n-{locale}-windows-aarch64.zip"
                    },
                },
                "hash": {
                    "url": "https://github.com/LI-NA/zed-i18n/releases/download/v$version/SHA256SUMS.txt"
                },
            },
        }
        output[f"zed-i18n-{locale}.json"] = json.dumps(app, indent=2, ensure_ascii=False) + "\n"
    return output


def cask_version(manifest: dict[str, Any]) -> str:
    base, revision = _release_parts(manifest)
    return f"{base},{revision}"


def scoop_version(manifest: dict[str, Any]) -> str:
    base, revision = _release_parts(manifest)
    return f"{base}-i18n.{revision}"


def _release_parts(manifest: dict[str, Any]) -> tuple[str, int]:
    release_tag = manifest.get("release_tag")
    if isinstance(release_tag, str):
        match = RELEASE_TAG_PATTERN.match(release_tag)
        if match:
            return match.group("base"), int(match.group("revision"))

    zed_version = str(manifest.get("zed_version", "")).removeprefix("v")
    revision = int(manifest.get("i18n_revision", 0))
    if not zed_version or revision <= 0:
        raise ValueError("release manifest must include release_tag or zed_version/i18n_revision")
    return zed_version, revision


def _assets_for_locale(
    manifest: dict[str, Any],
    *,
    locale: str,
    platform: str,
    kind: str,
) -> dict[str, dict[str, Any]]:
    assets = {}
    for asset in manifest.get("assets", []):
        if (
            asset.get("locale") == locale
            and asset.get("platform") == platform
            and asset.get("kind") == kind
        ):
            assets[str(asset["arch"])] = asset
    return assets


def _required_asset(
    assets: dict[str, dict[str, Any]],
    arch: str,
    locale: str,
    platform: str,
) -> dict[str, Any]:
    asset = assets.get(arch)
    if asset is None:
        raise ValueError(f"missing {platform} asset for {locale} {arch}")
    for key in ("sha256", "download_url"):
        if not asset.get(key):
            raise ValueError(f"{asset.get('name', f'{locale} {platform} {arch}')} missing {key}")
    return asset


def _locales_for(manifest: dict[str, Any], *, platform: str, kind: str) -> set[str]:
    return {
        str(asset["locale"])
        for asset in manifest.get("assets", [])
        if asset.get("platform") == platform and asset.get("kind") == kind and asset.get("locale")
    }


def _validate_packaging_release(
    manifest: dict[str, Any],
    expected_locales: Iterable[str] | None,
) -> None:
    macos_locales = _locales_for(manifest, platform="macos", kind="app")
    windows_locales = _locales_for(manifest, platform="windows", kind="portable_app")
    if not macos_locales:
        raise ValueError("release manifest has no macos app assets")
    if not windows_locales:
        raise ValueError("release manifest has no windows portable_app assets")
    if macos_locales != windows_locales:
        raise ValueError(
            "macos app locales and windows portable_app locales differ: "
            f"macos={sorted(macos_locales)}, windows={sorted(windows_locales)}"
        )

    required_locales = {locale for locale in expected_locales or () if locale}
    if required_locales:
        missing = sorted(required_locales - macos_locales)
        unexpected = sorted(macos_locales - required_locales)
        if missing or unexpected:
            details = []
            if missing:
                details.append("missing locales: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected locales: " + ", ".join(unexpected))
            raise ValueError("; ".join(details))


def _fallback_language_args(locale: str) -> str:
    language = locale.split("-", 1)[0].lower()
    args = f'"{language}"'
    if locale == DEFAULT_LOCALE:
        args += ", default: true"
    return args
