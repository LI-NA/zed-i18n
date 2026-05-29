<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Translate the Zed editor into your own language with ease.</strong></p>

  [![Zed v1.4.4](https://img.shields.io/badge/Zed-v1.4.4-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.4.4)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Source: MIT](https://img.shields.io/badge/Source-MIT-brightgreen)](LICENSE-MIT)
  [![Release: GPL-3.0](https://img.shields.io/badge/Release-GPL--3.0-orange)](LICENSE)
  <br>
  [![Release build](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml/badge.svg)](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml)
  [![Latest release](https://img.shields.io/github/v/release/LI-NA/zed-i18n?include_prereleases&label=latest)](https://github.com/LI-NA/zed-i18n/releases/latest)
  [![Downloads](https://img.shields.io/github/downloads/LI-NA/zed-i18n/total)](https://github.com/LI-NA/zed-i18n/releases)

  <p>
    <a href="docs/readme/cs-CZ.md">Čeština</a> ·
    <a href="docs/readme/de-DE.md">Deutsch</a> ·
    English ·
    <a href="docs/readme/es-ES.md">Español</a> ·
    <a href="docs/readme/fr-FR.md">Français</a> ·
    <a href="docs/readme/it-IT.md">Italiano</a> ·
    <a href="docs/readme/ja-JP.md">日本語</a> ·
    <a href="docs/readme/ko-KR.md">한국어</a> ·
    <a href="docs/readme/pl-PL.md">Polski</a> ·
    <a href="docs/readme/pt-BR.md">Português</a> ·
    <a href="docs/readme/ru-RU.md">Русский</a> ·
    <a href="docs/readme/tr-TR.md">Türkçe</a> ·
    <a href="docs/readme/zh-CN.md">简体中文</a> ·
    <a href="docs/readme/zh-TW.md">繁體中文</a>
  </p>
</div>

## Introduction

Zed-i18n is a tool that extracts UI strings from release versions of the [Zed](https://zed.dev) editor and applies translations to create multilingual builds.

> Zed-i18n is a community project unaffiliated with Zed Industries and is not officially endorsed or certified by Zed Industries.

## Supported Languages

Translations for 13 languages are currently bundled under `translations/`. All current translations are AI-generated; contributions from native speakers are welcome.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Downloads

You can download the latest builds from [Releases](https://github.com/LI-NA/zed-i18n/releases).

See [Release Builds](#release-builds) for details on how builds are produced, or [Manual Build](#manual-build) if you would rather build them yourself.

### Build Trust

- Distributed binaries are not code-signed, so you may see security warnings on Windows or macOS.
- All releases are built through `.github/workflows/i18n-release.yml`; build logs are available in the [Actions](https://github.com/LI-NA/zed-i18n/actions) tab.
- The upstream Zed source is pinned by the `zed_commit` SHA in `config/project.toml`, so you can verify exactly which source the build came from.

Avoid using builds from untrusted sources; building from source can reduce that risk.

### Opening on macOS

For files you trust, right-click the app in Finder and choose `Open`, or remove the quarantine attribute from Terminal with `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Install via Package Manager

On macOS, you can install it with a Homebrew cask.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

This automatically installs the language matching your system locale, falling back to `ko-KR` when there is no match. To pick a specific language, use Homebrew's `--language` option.

```bash
brew install --cask zed-i18n --language=ko-KR
```

On Windows, add the Scoop bucket and then install the language you want.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-ko-KR
```

Scoop installs cannot use Zed's built-in auto-update; update them with `scoop update` instead.

## Development Setup

Requires Python 3.12 or later and [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

All commands are run as `uv run zed-i18n <command>`.

## Usage

The target Zed version is set in `config/project.toml`. `fetch-zed` prepares both the checkout used for applying translations and building, and the clean checkout used for string extraction and review.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.4.4-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.4.4-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.4.4-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` scans the Zed Rust sources for UI string candidates and writes them to `catalog/en-US.json` and `manifest/ui-strings.json`. Translation results are stored in `translations/<language>.json`.

Newly discovered strings are added to `manifest/ui-strings.json` with the `needs_review` status. Mark only strings that are actually shown in the UI as `accepted`, then translate them.

## AI Translation

For AI-driven translation runs, follow `prompts/commands/translation-start.md`. To compare and merge results from multiple models, use `prompts/commands/translation-review.md`.

If you want to translate only newly added keys while leaving existing translations intact, refer to the files with `new-keys` in their names.

To include VS Code translation references in the batches, prepare the repositories below before running `prepare-translation`. Translation batches are still generated normally if these repositories are not present.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

When adding a new language:

1. Write a style guide and glossary in `prompts/translation/<language>.md`.
2. Generate batches with `prepare-translation`.
3. Merge the AI-produced JSON results using `merge-translation`.
4. Validate the result with `validate`.

Per-language guidelines live in `prompts/translation/<language>.md`. If the file is missing, `prompts/translation/TEMPLATE.md` is used as the default.

## Manual Build

On Windows, you need [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), the Windows SDK, CMake, and [Rust](https://rustup.rs/). Sharing the build cache across versions via `.cache/zed/target` is recommended. A sample build looks like this:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.4.4
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Release Builds

Release builds run automatically through GitHub Actions, defined in `.github/workflows/i18n-release.yml`. The Zed source is pinned to the `zed_version` tag and `zed_commit` SHA in `config/project.toml`.

The release workflow applies `config/distribution.toml` alongside per-language translations to patch the zed-i18n identifier, About information, and automatic updates. This redirects update checks to `zed-i18n`.

> **Note:** Zed-i18n builds change the auto-update endpoint from Zed's official server to this repository's release `manifest.json`. You can disable auto-update in settings if you prefer.

### Telemetry

Zed-i18n does not alter telemetry behavior. With default settings, anonymous usage metrics and crash reports may be sent to Zed Industries' servers. To disable telemetry, set `telemetry.metrics` and `telemetry.diagnostics` to `false` in Zed settings.

## Known Limitations

Most UI strings — menus, buttons, tooltips, settings, action descriptions — are handled through direct substitution. However, some action names that are generated dynamically at runtime in the Command Palette or Keymap Editor require a separate patch and are not yet covered.

If you know a way to patch these untranslated areas reliably across Zed versions, contributions are very welcome.

## On AI Usage

Most of the code in this project was written with the help of AI tools, and every translation was produced by AI. Because the translation results were not reviewed by a human, mistranslations or branding issues may exist. If you see a problem with any translation — including this document — or think there is a better rendering, please open an issue or PR.

### Translation Process

All translations went through the process described in [AI Translation](#ai-translation).

1. `extract` pulls UI string candidates from the Zed source. Results land in `catalog/en-US.json` and `manifest/ui-strings.json`.
2. `audit-candidates` reviews which strings the extraction rules captured and which candidates they missed, then uses that to manage the actual translation targets (`accepted`).
3. `prepare-translation` generates per-language batches, bundling the style guide, glossary, and (when available) VS Code language-pack references.
4. An AI model writes the translation result JSON one batch at a time.
5. `merge-translation` combines the batches, then `validate` checks for missing/extra entries, placeholder integrity, and protected-token consistency.

The currently registered translations went through the above process for every language using two models — `Sonnet 4.6` and `GPT-5.5`. Each model produced a full independent translation, which was reviewed separately. The two completed translation files were then re-reviewed and merged into the final output using the `Opus 4.6` model.

For more on the AI translation process, see the files under `prompts\commands`.

## License

Content derived from Zed sources (`catalog/`, `translations/`, `manifest/`, release artifacts, etc.) is licensed under [GPL-3.0](LICENSE). This project distributes modified builds of Zed. The `zed-i18n` source code and the translation glossaries (`prompts/translation/glossary/`) extracted from [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) are licensed under [MIT](LICENSE-MIT).

Zed and the Zed logo are the property of Zed Industries. VS Code and the VS Code language pack content are copyrighted by Microsoft Corporation.
