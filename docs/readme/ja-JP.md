<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Zed エディターを手軽にお使いの言語へ翻訳できます。</strong></p>

  [![Zed v1.4.3](https://img.shields.io/badge/Zed-v1.4.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.4.3)
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

Zed-i18n は、[Zed](https://zed.dev) エディターのリリース版から UI 文字列を抽出し、翻訳を適用して多言語ビルドを生成するツールです。

> Zed-i18n は Zed Industries とは無関係のコミュニティプロジェクトであり、公式の後援や承認を受けていません。

## 対応言語

現在、`translations/` 以下に 13 言語の翻訳が収録されています。すべての翻訳は AI によって生成されており、各言語のネイティブスピーカーによる貢献を歓迎します。

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## ダウンロード

最新ビルドは [Releases](https://github.com/LI-NA/zed-i18n/releases) から入手できます。

最新ビルドの仕組みについては [リリースビルド](#リリースビルド) で詳しく確認でき、自分でビルドしたい場合は [手動ビルド](#手動ビルド) を参照してください。

### ビルドの信頼性

- 現在の配布バイナリにはコード署名が適用されていません。Windows や macOS でセキュリティ警告が表示されることがあります。
- すべてのリリースは `.github/workflows/i18n-release.yml` を通じてビルドされており、ビルドログは [Actions](https://github.com/LI-NA/zed-i18n/actions) タブで確認できます。
- Zed の元ソースは `config/project.toml` の `zed_commit` SHA で固定されているため、ビルドに使用された正確なソースを検証できます。

信頼できないソースのビルドは使用せず、可能であれば自分でビルドすることでセキュリティ上の懸念を軽減できます。

### macOS で開けないとき

信頼できるファイルに限り、Finder で右クリックして `開く` を選択するか、ターミナルで `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` コマンドを実行して隔離属性を削除してください。

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
uv run zed-i18n extract --zed-root .cache/zed/v1.4.3-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.4.3-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.4.3-clean-extract
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
cd .cache\zed\v1.4.3
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## リリースビルド

リリースビルドは `.github/workflows/i18n-release.yml` で定義された GitHub Actions を通じて自動的に実行されます。Zed のソースは `config/project.toml` 内の `zed_version` タグと `zed_commit` SHA に固定されています。

リリースワークフローは言語ごとの翻訳とともに `config/distribution.toml` を適用して、zed-i18n の識別子、About 情報、および自動更新パスにパッチを当てます。これにより、自動更新パスが `zed-i18n` に書き換えられます。

> **注意:** Zed-i18n のビルドは、自動更新エンドポイントを Zed の公式サーバーから本リポジトリのリリースにある `manifest.json` に変更します。自動更新が不要な場合は、設定で無効化してください。

### テレメトリ

Zed-i18n はテレメトリの動作を変更しません。デフォルト設定では、匿名の使用状況メトリクスやクラッシュレポートが Zed Industries のサーバーに送信されることがあります。テレメトリを無効化するには、Zed の設定で `telemetry.metrics` と `telemetry.diagnostics` を `false` に設定してください。

## 既知の制限事項

メニュー、ボタン、ツールチップ、設定、アクション説明など、ほとんどの UI 文字列は直接置換で対応しています。ただし、コマンドパレットやキーマップエディターでランタイムに動的生成されるアクション名の一部は、別途パッチが必要なため現時点では対応していません。

これらの未翻訳部分について、Zed のバージョンが変わっても安定してパッチを適用できる方法をご存知の方からの貢献を歓迎します。

## AI の活用について

このプロジェクトのコードの大部分は AI ツールの支援を受けて作成されており、すべての翻訳も AI によって生成されています。翻訳結果は人による直接的なレビューを経ていないため、誤訳やブランディング上の問題が含まれている可能性があります。本ドキュメントを含め、翻訳に問題があると思われる場合や、より良い翻訳が可能だと感じられた場合は、いつでもイシューや PR を投稿してください。

### 翻訳プロセス

すべての翻訳は [AI 翻訳](#ai-翻訳) で説明したプロセスを経て行われました。

1. `extract` で Zed のソースから UI 文字列の候補を抽出します。結果は `catalog/en-US.json` と `manifest/ui-strings.json` に保存されます。
2. `audit-candidates` で抽出ルールが捕捉した文字列と漏れた候補を点検し、これをもとに実際の翻訳対象（`accepted`）を管理します。
3. `prepare-translation` で言語ごとのバッチを生成します。スタイルガイド、用語集、可能な場合は VS Code 言語パックの参照が同梱されます。
4. AI モデルがバッチ単位で翻訳結果の JSON を作成します。
5. `merge-translation` で結果をマージし、`validate` で欠落・余分な項目、プレースホルダー、保護トークンの一致を検証します。

現在登録されている翻訳は、すべての言語について上記のプロセスを `Sonnet 4.6` と `GPT-5.5` の 2 つのモデルで繰り返し、それぞれが個別に全体を翻訳して再レビューを行いました。その後、完成した 2 種類の翻訳ファイルを `Opus 4.6` モデルで再レビュー・マージして最終的な成果物としています。

AI 翻訳のプロセスについては、`prompts\commands` 配下のファイルで詳しく確認できます。

## ライセンス

Zed のソースから派生したコンテンツ（`catalog/`、`translations/`、`manifest/`、リリース成果物など）は [GPL-3.0](../../LICENSE) のもとでライセンスされています。本プロジェクトは Zed の改変版ビルドを配布しています。`zed-i18n` のソースコードおよび [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) から抽出された翻訳用語集（`prompts/translation/glossary/`）は [MIT](../../LICENSE-MIT) のもとでライセンスされています。

Zed および Zed のロゴは Zed Industries の資産であり、VS Code および VS Code 言語パックのコンテンツの著作権は Microsoft Corporation に帰属します。
