<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>輕鬆將 Zed 編輯器翻譯成你的語言。</strong></p>

  [![Zed v1.2.3](https://img.shields.io/badge/Zed-v1.2.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.3)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue)](../../LICENSE)
  [![MIT components](https://img.shields.io/badge/MIT-components-yellow)](../../LICENSE-MIT)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    <a href="es-ES.md">Español</a> ·
    <a href="fr-FR.md">Français</a> ·
    <a href="it-IT.md">Italiano</a> ·
    <a href="ja-JP.md">日本語</a> ·
    <a href="ko-KR.md">한국어</a> ·
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    繁體中文
  </p>
</div>

## 簡介

zed-i18n 是一套工具組，可從 [Zed](https://zed.dev) 編輯器的發行版本中擷取 UI 字串，並套用翻譯以產生多語言版本。

## 支援語言

目前 `translations/` 目錄下包含 13 種語言的翻譯。

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## 下載

你可以從 [Releases](https://github.com/LI-NA/zed-i18n/releases) 下載最新建置。若想自行建置，請依照下列步驟進行。

目前發布檔案尚未套用程式碼簽署。如果 macOS 阻擋開啟，請僅對你信任的檔案在 Finder 中按右鍵選擇 `打開`，或在終端機執行 `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` 移除隔離屬性。

## 安裝

需要 Python 3.12 以上版本及 [`uv`](https://docs.astral.sh/uv/)。

```powershell
uv sync
```

所有指令均以 `uv run zed-i18n <command>` 的形式執行。

## 使用方式

目標 Zed 版本設定於 `config/project.toml`。`fetch-zed` 會同時準備用於套用翻譯與建置的簽出目錄，以及用於字串擷取與審查的乾淨簽出目錄。

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` 會掃描 Zed 的 Rust 原始碼以尋找 UI 字串候選項，並將結果寫入 `catalog/en-US.json` 與 `manifest/ui-strings.json`。翻譯結果會儲存於 `translations/<language>.json`。

新發現的字串會以 `needs_review` 狀態加入 `manifest/ui-strings.json`。只有確實顯示於 UI 中的字串，才應將狀態改為 `accepted` 並進行翻譯。

## AI 翻譯

若要使用 AI 進行翻譯，請參考 `prompts/commands/translation-start.md`。若要比較並合併多個模型的翻譯結果，請使用 `prompts/commands/translation-review.md`。

若只想翻譯新增的鍵值而保留既有翻譯不變，請參考名稱含有 `new-keys` 後綴的檔案。

若要在批次中加入 VS Code 翻譯參考，請在執行 `prepare-translation` 前先準備以下儲存庫。即使這些儲存庫不存在，批次仍會正常產生。

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

新增語言時：

1. 在 `prompts/translation/<language>.md` 撰寫風格指南與詞彙表。
2. 使用 `prepare-translation` 產生批次。
3. 以 `merge-translation` 合併 AI 產生的 JSON 結果。
4. 以 `validate` 驗證結果。

各語言的翻譯指南位於 `prompts/translation/<language>.md`。若該檔案不存在，則以 `prompts/translation/TEMPLATE.md` 作為預設範本。

## 手動建置

在 Windows 上，你需要安裝 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)、Windows SDK、CMake 以及 [Rust](https://rustup.rs/)。建議透過 `.cache/zed/target` 在不同版本間共用建置快取。以下為建置範例：

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.3
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## 正式版建置

正式版建置會透過 GitHub Actions 自動執行，定義於 `.github/workflows/i18n-release.yml`。Zed 原始碼固定於 `config/project.toml` 中的 `zed_version` 標籤與 `zed_commit` SHA。

發布工作流程會套用 `config/distribution.toml`，以修補 zed-i18n 識別碼、About 資訊及自動更新路徑，將自動更新路徑改寫為 `zed-i18n`。

## 已知限制

大多數 UI 字串——選單、按鈕、工具提示、設定、動作說明——均透過直接替換來處理。然而，部分在執行時由命令選擇區或鍵盤對應編輯器動態產生的動作名稱，需要另行修補，目前尚未涵蓋。

若你知道如何可靠地跨 Zed 版本套用修補，非常歡迎貢獻。

## 關於 AI 的使用

本專案的大部分程式碼是在 AI 工具的協助下撰寫的，所有翻譯也均由 AI 產生。若你發現程式碼或翻譯有任何問題，或認為有更好的做法，歡迎開啟 PR。

## 授權條款

衍生自 Zed 原始碼的內容（`catalog/`、`translations/`、`manifest/` 及發布產物）依 [GPL-3.0](../../LICENSE) 授權。`zed-i18n` 原始碼及從 [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) 中擷取的翻譯詞彙表（`prompts/translation/glossary/`）依 [MIT](../../LICENSE-MIT) 授權。VS Code 語言套件的內容版權歸 Microsoft Corporation 所有。
