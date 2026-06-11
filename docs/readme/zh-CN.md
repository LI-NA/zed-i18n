<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>轻松将 Zed 编辑器翻译成你的语言。</strong></p>

  [![Zed v1.6.3](https://img.shields.io/badge/Zed-v1.6.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.6.3)
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
    简体中文 ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## 简介

Zed-i18n 是一个工具集，用于从 [Zed](https://zed.dev) 编辑器的发布版本中提取 UI 字符串，并应用翻译以生成多语言版本。

> Zed-i18n 是一个与 Zed Industries 无关的社区项目，未获得官方赞助或认证。

## 支持的语言

`translations/` 目录下目前包含 13 种语言的翻译。所有现有翻译均由 AI 生成，欢迎各语言的母语者参与贡献。

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## 下载

你可以从 [Releases](https://github.com/LI-NA/zed-i18n/releases) 页面获取最新的构建版本。

构建过程详见 [发布版本构建](#发布版本构建)，若想自行构建，请参考 [手动构建](#手动构建)。

### 构建可信度

- 当前发布文件尚未进行代码签名，在 Windows 或 macOS 上可能出现安全警告。
- 所有发布版本均通过 `.github/workflows/i18n-release.yml` 构建，构建日志可在 [Actions](https://github.com/LI-NA/zed-i18n/actions) 标签页查看。
- Zed 原始源码已通过 `config/project.toml` 中的 `zed_commit` SHA 固定，可以准确核实构建所基于的源代码。

请勿使用来自不可信来源的构建产物，建议尽量自行构建以缓解安全方面的顾虑。

### 在 macOS 上无法打开时

仅对你信任的文件，可在 Finder 中右键选择 `打开`，或在终端运行 `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` 命令移除隔离属性。

## 通过包管理器安装

在 macOS 上，你可以通过 Homebrew cask 安装。

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

它会自动安装与系统语言匹配的语言；若没有匹配的语言，则安装 `ko-KR`。如需指定特定语言，可使用 Homebrew 的 `--language` 选项。

```bash
brew install --cask zed-i18n --language=zh-CN
```

在 Windows 上，添加 Scoop bucket 后，再指定想要的语言进行安装。

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-zh-CN
```

通过 Scoop 安装的版本无法使用 Zed 自带的自动更新，可使用 `scoop update` 进行更新。

## 开发环境设置

需要 Python 3.12 或更高版本以及 [`uv`](https://docs.astral.sh/uv/)。

```powershell
uv sync
```

所有命令均以 `uv run zed-i18n <command>` 的形式运行。

## 使用方法

目标 Zed 版本在 `config/project.toml` 中设置。`fetch-zed` 会同时准备用于应用翻译和构建的检出目录，以及用于字符串提取与审查的干净检出目录。

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.6.3-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.6.3-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.6.3-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` 会扫描 Zed 的 Rust 源码以寻找 UI 字符串候选项，并将结果写入 `catalog/en-US.json` 和 `manifest/ui-strings.json`。翻译结果存储在 `translations/<language>.json` 中。

新发现的字符串会以 `needs_review` 状态写入 `manifest/ui-strings.json`。只有确认会在 UI 中显示的字符串，才应将其状态改为 `accepted` 并进行翻译。

## AI 翻译

如需使用 AI 进行翻译，请参照 `prompts/commands/translation-start.md`。若需比较并合并多个模型的翻译结果，请使用 `prompts/commands/translation-review.md`。

如果你只想翻译新增的键而保留现有翻译，请参考文件名中带有 `new-keys` 的文件。

若要在批次中包含 VS Code 的翻译参考，请在运行 `prepare-translation` 之前克隆以下仓库。即使缺少这些仓库，批次也能正常生成。

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

添加新语言时：

1. 在 `prompts/translation/<language>.md` 中编写翻译风格指南，并在 `prompts/translation/glossary/<lang>.md` 中编写固定词汇表。
2. 使用 `prepare-translation` 生成批次。
3. 使用 `merge-translation` 合并 AI 生成的 JSON 结果。
4. 使用 `validate` 验证结果。

各语言的翻译指南位于 `prompts/translation/<language>.md`。若该文件不存在，则默认使用 `prompts/translation/TEMPLATE.md`。

## 手动构建

在 Windows 上需要安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)、Windows SDK、CMake 以及 [Rust](https://rustup.rs/)。建议通过 `.cache/zed/target` 在各版本间共享构建缓存。示例构建命令如下：

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.6.3
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## 发布版本构建

发布版本通过 GitHub Actions 自动构建，定义在 `.github/workflows/i18n-release.yml` 中。Zed 源码已固定到 `config/project.toml` 中的 `zed_version` 标签和 `zed_commit` SHA。

发布工作流会与各语言的翻译一起应用 `config/distribution.toml`，以修补 zed-i18n 标识符、About 信息及自动更新路径，从而将自动更新路径重写为 `zed-i18n`。

> **注意：** Zed-i18n 构建会将自动更新地址从 Zed 官方服务器更改为本仓库发布产物中的 `manifest.json`。如果你不希望使用自动更新，可以在设置中将其关闭。

### 遥测

Zed-i18n 不会改变遥测行为。在默认设置下，匿名使用指标和崩溃报告可能会发送到 Zed Industries 的服务器。如需关闭遥测，请在 Zed 设置中将 `telemetry.metrics` 和 `telemetry.diagnostics` 设为 `false`。

## 已知限制

大多数 UI 字符串——菜单、按钮、工具提示、设置、操作描述——均通过直接替换处理。但是，某些在运行时由命令面板或键位映射编辑器动态生成的操作名称需要单独打补丁，目前尚未覆盖。

对于这些尚未翻译的部分，如果你知道一种可在不同 Zed 版本间可靠应用补丁的方法，欢迎贡献代码。

## 关于 AI 的使用

本项目的大部分代码借助 AI 工具编写，所有翻译均由 AI 生成。由于翻译结果未经人工直接审校，可能存在误译或品牌相关的问题。包括本文档在内，如果你认为翻译有问题，或有更好的译法，欢迎随时提交 issue 或 PR。

### 翻译流程

所有翻译均经过 [AI 翻译](#ai-翻译) 中所述的流程进行。

1. `extract` 从 Zed 源码中提取 UI 字符串候选项，结果保存到 `catalog/en-US.json` 与 `manifest/ui-strings.json`。
2. `audit-candidates` 检查哪些字符串被提取规则纳入或遗漏，并据此管理实际的翻译目标列表（`accepted`）。
3. `prepare-translation` 生成各语言的批次，并附带风格指南、词汇表，以及在可用时附带 VS Code 语言包的参考资料。
4. 由 AI 模型按批次生成翻译结果 JSON。
5. `merge-translation` 合并结果，`validate` 检查是否存在条目缺失或多余、占位符及保护令牌的一致性问题。

当前已纳入的翻译，针对每一种语言均使用 `Sonnet 4.6` 和 `GPT-5.5` 两个模型独立完成整套翻译并各自重新审校。随后，使用 `Opus 4.6` 模型对完成的两份翻译进行整体复审与合并，得到最终结果。

有关 AI 翻译流程的更多内容，可参见 `prompts\commands` 目录下的文件。

## 许可证

源自 Zed 的内容（`catalog/`、`translations/`、`manifest/` 及发布产物等）依据 [GPL-3.0](../../LICENSE) 授权。本项目分发 Zed 的修改版构建产物。`zed-i18n` 源代码及从 [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) 参考的资料依据 [MIT](../../LICENSE-MIT) 授权。

Zed 与 Zed 徽标为 Zed Industries 的资产；VS Code 及 VS Code 语言包内容的版权归 Microsoft Corporation 所有。
