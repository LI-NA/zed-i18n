<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>輕鬆將 Zed 編輯器翻譯成你的語言。</strong></p>

  [![Zed v1.8.2](https://img.shields.io/badge/Zed-v1.8.2-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.8.2)
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

Zed-i18n 是一套工具組，可從 [Zed](https://zed.dev) 編輯器的發行版本中擷取 UI 字串，並套用翻譯以產生多語言版本。

> Zed-i18n 是與 Zed Industries 無關的社群專案，未獲得官方贊助或認證。

## 支援語言

目前 `translations/` 目錄下包含 13 種語言的翻譯。所有翻譯皆由 AI 產生，歡迎各語言的母語人士參與貢獻。

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## 下載

你可以從 [Releases](https://github.com/LI-NA/zed-i18n/releases) 下載最新建置。

最新建置的流程可在[正式版建置](#正式版建置)中進一步了解，若想自行建置，請參考[手動建置](#手動建置)。

### 建置可信度

- 目前發布檔案尚未套用程式碼簽署，在 Windows 或 macOS 上可能會出現安全性警告。
- 所有發布版本皆透過 `.github/workflows/i18n-release.yml` 建置，建置紀錄可在 [Actions](https://github.com/LI-NA/zed-i18n/actions) 分頁中檢視。
- Zed 原始碼以 `config/project.toml` 中的 `zed_commit` SHA 固定，可確認建置所使用的原始碼版本。

請避免使用來自不明來源的建置；若情況允許，請自行建置以降低安全疑慮。

### 在 macOS 上無法開啟時

針對你信任的檔案，可在 Finder 中按右鍵選擇 `開啟`，或在終端機執行 `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` 移除隔離屬性。

## 透過套件管理器安裝

在 macOS 上，你可以透過 Homebrew cask 安裝。

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

它會自動安裝與系統語言相符的語言；若沒有相符的語言，則會安裝 `ko-KR`。若要指定特定語言，可使用 Homebrew 的 `--language` 選項。

```bash
brew install --cask zed-i18n --language=zh-TW
```

在 Windows 上，新增 Scoop bucket 後，再指定想要的語言進行安裝。

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-zh-TW
```

透過 Scoop 安裝的版本無法使用 Zed 內建的自動更新，可使用 `scoop update` 進行更新。

## 開發環境設定

需要 Python 3.12 以上版本及 [`uv`](https://docs.astral.sh/uv/)。

```powershell
uv sync
```

所有指令均以 `uv run zed-i18n <command>` 的形式執行。

## 使用方式

目標 Zed 版本設定於 `config/project.toml`。`fetch-zed` 會同時準備用於套用翻譯與建置的簽出目錄，以及用於字串擷取與審查的乾淨簽出目錄。

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.8.2-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.8.2-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.8.2-clean-extract
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

1. 在 `prompts/translation/<language>.md` 撰寫翻譯風格指南，並在 `prompts/translation/glossary/<lang>.md` 撰寫固定詞彙表。
2. 使用 `prepare-translation` 產生批次。
3. 以 `merge-translation` 合併 AI 產生的 JSON 結果。
4. 以 `validate` 驗證結果。

各語言的翻譯指南位於 `prompts/translation/<language>.md`。若該檔案不存在，則以 `prompts/translation/TEMPLATE.md` 作為預設範本。

## 手動建置

在 Windows 上，你需要安裝 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)、Windows SDK、CMake 以及 [Rust](https://rustup.rs/)。建議透過 `.cache/zed/target` 在不同版本間共用建置快取。以下為建置範例：

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.8.2
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## 正式版建置

正式版建置會透過 GitHub Actions 自動執行，定義於 `.github/workflows/i18n-release.yml`。Zed 原始碼固定於 `config/project.toml` 中的 `zed_version` 標籤與 `zed_commit` SHA。

發布工作流程會連同各語言的翻譯套用 `config/distribution.toml`，以修補 zed-i18n 識別碼、About 資訊及自動更新路徑，將自動更新路徑改寫為 `zed-i18n`。

> **注意事項：** Zed-i18n 建置會將自動更新路徑從 Zed 官方伺服器改為本儲存庫發布的 `manifest.json` 檔案。若不希望啟用自動更新，可在設定中停用。

### 遙測

Zed-i18n 不會變更遙測行為。在預設設定下，匿名使用指標與當機報告可能會傳送至 Zed Industries 的伺服器。若要關閉遙測，請在 Zed 設定中將 `telemetry.metrics` 與 `telemetry.diagnostics` 設為 `false`。

## 已知限制

大多數 UI 字串——選單、按鈕、工具提示、設定、動作說明——均透過直接替換來處理。然而，部分在執行時由命令選擇區或鍵盤對應編輯器動態產生的動作名稱，需要另行修補，目前尚未涵蓋。

針對這些尚未翻譯的部分，若你知道如何可靠地跨 Zed 版本套用修補，非常歡迎貢獻。

## 關於 AI 的使用

本專案的大部分程式碼是在 AI 工具的協助下撰寫的，所有翻譯也均由 AI 產生。由於翻譯結果未經人工直接審閱，可能存在誤譯或品牌標示上的問題。若你認為翻譯（包含本文件在內）有問題，或有更好的譯法，歡迎隨時提出 issue 或 PR。

### 翻譯流程

所有翻譯皆依照 [AI 翻譯](#ai-翻譯)中說明的流程進行。

1. `extract` 會從 Zed 原始碼中擷取 UI 字串候選項，結果儲存於 `catalog/en-US.json` 與 `manifest/ui-strings.json`。
2. `audit-candidates` 會檢視哪些字串已被擷取規則納入、哪些尚未涵蓋，並據此管理實際的翻譯對象清單（`accepted`）。
3. `prepare-translation` 會產生各語言的批次，並一併附上風格指南、詞彙表，以及在可用時的 VS Code 語言套件參考資料。
4. AI 模型以批次為單位撰寫翻譯結果 JSON。
5. `merge-translation` 會合併結果，`validate` 則會檢查是否有遺漏或多餘的項目、佔位符與保護 Token 的一致性。

目前所登錄的翻譯，皆針對每種語言以 `Sonnet 4.6` 與 `GPT-5.5` 兩款模型分別重複上述流程，各自獨立完成整份翻譯並再次檢閱。隨後，完成的兩份翻譯再透過 `Opus 4.6` 重新檢閱並合併為最終結果。

關於 AI 翻譯流程的更多細節，可在 `prompts\commands` 目錄下進一步了解。

## 授權條款

衍生自 Zed 原始碼的內容（`catalog/`、`translations/`、`manifest/` 及發布產物等）依 [GPL-3.0](../../LICENSE) 授權。本專案發布的是 Zed 的修改版建置。`zed-i18n` 原始碼及從 [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) 中參照的資料依 [MIT](../../LICENSE-MIT) 授權。

Zed 及 Zed 標誌為 Zed Industries 的資產；VS Code 及 VS Code 語言套件內容的版權歸 Microsoft Corporation 所有。
