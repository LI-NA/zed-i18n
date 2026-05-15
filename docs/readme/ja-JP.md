<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Zed エディターを手軽にお使いの言語へ翻訳できます。</strong></p>

  [![Zed v1.2.5](https://img.shields.io/badge/Zed-v1.2.5-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.5)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Source: MIT](https://img.shields.io/badge/Source-MIT-brightgreen)](../../LICENSE-MIT)
  [![Release: GPL-3.0](https://img.shields.io/badge/Release-GPL--3.0-orange)](../../LICENSE)
  <br>
  [![Release build](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml/badge.svg)](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml)
  [![Latest release](https://img.shields.io/github/v/release/LI-NA/zed-i18n?include_prereleases&label=latest)](https://github.com/LI-NA/zed-i18n/releases/latest)
  [![Downloads](https://img.shields.io/github/downloads/LI-NA/zed-i18n/total)](https://github.com/LI-NA/zed-i18n/releases)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    <a href="es-ES.md">Español</a> ·
    <a href="fr-FR.md">Français</a> ·
    <a href="it-IT.md">Italiano</a> ·
    日本語 ·
    <a href="ko-KR.md">한국어</a> ·
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## はじめに

zed-i18n は、[Zed](https://zed.dev) エディターのリリース版から UI 文字列を抽出し、翻訳を適用して多言語ビルドを生成するツールです。

## 対応言語

現在、`translations/` 以下に 13 言語の翻訳が収録されています。

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## ダウンロード

最新ビルドは [Releases](https://github.com/LI-NA/zed-i18n/releases) から入手できます。自分でビルドする場合は、以下の手順に従ってください。

現在の配布ファイルにはコード署名が適用されていません。macOS で開けない場合は、信頼できるファイルに限り Finder で右クリックして `開く` を選ぶか、ターミナルで `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` を実行して隔離属性を削除してください。

## インストール

Python 3.12 以降と [`uv`](https://docs.astral.sh/uv/) が必要です。

```powershell
uv sync
```

すべてのコマンドは `uv run zed-i18n <command>` の形式で実行します。

## 使い方

対象の Zed バージョンは `config/project.toml` で指定します。`fetch-zed` を実行すると、翻訳適用・ビルド用のチェックアウトと、文字列抽出・レビュー用のクリーンチェックアウトの両方が準備されます。

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.5-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.5-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.5-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` は Zed の Rust ソースをスキャンして UI 文字列の候補を抽出し、`catalog/en-US.json` と `manifest/ui-strings.json` に書き出します。翻訳結果は `translations/<language>.json` に保存されます。

新たに発見された文字列は `needs_review` ステータスで `manifest/ui-strings.json` に追加されます。実際に UI に表示される文字列のみ `accepted` に変更してから翻訳してください。

## AI 翻訳

AI を使った翻訳作業を行う場合は、`prompts/commands/translation-start.md` の手順に従ってください。複数モデルの結果を比較・マージするには、`prompts/commands/translation-review.md` を使用します。

既存の翻訳を維持しながら新規追加されたキーのみを翻訳したい場合は、`new-keys` サフィックスの付いたファイルを参照してください。

VS Code の翻訳参考資料をバッチに含めるには、`prepare-translation` を実行する前に以下のリポジトリをあらかじめ準備してください。これらがない場合でも、バッチは通常通り生成されます。

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

新しい言語を追加する場合：

1. `prompts/translation/<language>.md` にスタイルガイドと用語集を作成します。
2. `prepare-translation` でバッチを生成します。
3. `merge-translation` で AI が生成した JSON 結果をマージします。
4. `validate` で結果を検証します。

言語ごとのガイドラインは `prompts/translation/<language>.md` に記述します。ファイルが存在しない場合は、`prompts/translation/TEMPLATE.md` がデフォルトとして使用されます。

## 手動ビルド

Windows では [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)、Windows SDK、CMake、および [Rust](https://rustup.rs/) が必要です。`.cache/zed/target` を使ってバージョン間でビルドキャッシュを共有することをお勧めします。ビルドの例を以下に示します。

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.5
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## リリースビルド

リリースビルドは `.github/workflows/i18n-release.yml` で定義された GitHub Actions を通じて自動的に実行されます。Zed のソースは `config/project.toml` 内の `zed_version` タグと `zed_commit` SHA に固定されています。

リリースワークフローは `config/distribution.toml` を適用して、zed-i18n の識別子、About 情報、および自動更新パスにパッチを当てます。これにより、自動更新パスが `zed-i18n` に書き換えられます。

## 既知の制限事項

メニュー、ボタン、ツールチップ、設定、アクション説明など、ほとんどの UI 文字列は直接置換で対応しています。ただし、コマンドパレットやキーマップエディターでランタイムに動的生成されるアクション名の一部は、別途パッチが必要なため現時点では対応していません。

Zed のバージョン間でパッチを安定して適用する方法をご存知の方は、ぜひ貢献をお待ちしています。

## AI の活用について

このプロジェクトのコードの大部分は AI ツールの支援を受けて作成されており、すべての翻訳も AI によって生成されています。コードや翻訳に問題を見つけた場合、またはより良いアプローチがあると思われる場合は、お気軽に PR を開いてください。

## ライセンス

Zed のソースから派生したコンテンツ（`catalog/`、`translations/`、`manifest/`、およびリリース成果物）は [GPL-3.0](../../LICENSE) のもとでライセンスされています。`zed-i18n` のソースコードおよび [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) から抽出された翻訳用語集（`prompts/translation/glossary/`）は [MIT](../../LICENSE-MIT) のもとでライセンスされています。VS Code 言語パックのコンテンツは Microsoft Corporation の著作物です。
