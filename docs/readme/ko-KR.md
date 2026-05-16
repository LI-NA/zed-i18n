<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Zed 에디터를 손쉽게 자신의 언어로 번역해보세요.</strong></p>

  [![Zed v1.2.6](https://img.shields.io/badge/Zed-v1.2.6-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.6)
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
    한국어 ·
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## 프로젝트 소개

Zed-i18n은 [Zed](https://zed.dev) 에디터의 릴리즈 버전에서 UI 문자열을 추출하고, 번역을 적용해 다국어 빌드를 만드는 도구입니다.

## 지원 언어

현재 13개 언어의 번역이 `translations/`에 포함되어 있습니다.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## 다운로드

[Releases](https://github.com/LI-NA/zed-i18n/releases)에서 최신 빌드를 다운로드받을 수 있습니다. 수동으로 빌드를 하고 싶으시다면, 아래 절차로 직접 빌드할 수 있습니다.

현재 배포 파일은 코드 서명이 적용되어 있지 않습니다. macOS에서 열리지 않으면 신뢰하는 파일에 한해 Finder에서 우클릭 후 `열기`를 선택하거나, 터미널에서 `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`를 실행해 격리 속성을 제거해야 할 수 있습니다.

## 설치

Python 3.12 이상, [`uv`](https://docs.astral.sh/uv/) 필요.

```powershell
uv sync
```

모든 명령은 `uv run zed-i18n <command>` 형태로 실행합니다.

## 사용법

대상 Zed 버전은 `config/project.toml`에서 지정합니다. `fetch-zed`는 번역 적용·빌드용 checkout과 문자열 추출·검토용 clean checkout을 함께 준비합니다.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract`는 Zed Rust 소스에서 UI 문자열 후보를 찾아 `catalog/en-US.json`과 `manifest/ui-strings.json`에 기록합니다. 번역 결과는 `translations/<language>.json`에 저장됩니다.

새로 발견된 문자열은 `manifest/ui-strings.json`에 `needs_review` 상태로 들어갑니다. 실제 UI에 노출되는 문자열만 `accepted`로 바꾸고 번역을 진행합니다.

## AI 번역

AI 번역 작업은 `prompts/commands/translation-start.md`를 참고해 진행합니다. 여러 모델의 결과를 비교·병합하려면 `prompts/commands/translation-review.md`를 사용합니다.

만약 기존 번역은 그대로 두고 새로운 키만 번역하고 싶은 경우 `new-keys`가 붙은 파일을 참고하세요.

VS Code 번역 참고자료를 배치에 포함하려면 아래 저장소를 준비한 뒤 `prepare-translation`을 실행합니다. 없어도 번역 배치는 정상 생성됩니다.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

새 언어를 추가할 때:

1. `prompts/translation/<language>.md`에 번역 스타일과 용어집을 작성합니다.
2. `prepare-translation`으로 배치를 생성합니다.
3. AI가 만든 JSON 결과를 `merge-translation`으로 병합합니다.
4. `validate`로 결과를 검증합니다.

언어별 번역 지침은 `prompts/translation/<language>.md`에 둡니다. 파일이 없으면 `prompts/translation/TEMPLATE.md`를 기본으로 씁니다.

## 수동 빌드

Windows에서는 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake, [Rust](https://rustup.rs/)가 필요합니다. 빌드 캐시는 `.cache/zed/target`을 버전 간 공유하는 게 좋습니다. 예시 빌드 방법은 다음을 참고하세요.

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## 릴리즈 빌드

릴리즈 빌드는 GitHub Actions를 통해 자동으로 이루어지며, `.github/workflows/i18n-release.yml`에 정의되어 있습니다. Zed 원본은 `config/project.toml`의 `zed_version` 태그와 `zed_commit` SHA로 고정한 버전을 사용합니다.

릴리즈 workflow는 `config/distribution.toml`을 적용해 zed-i18n 식별자, About 정보, 자동 업데이트 경로를 패치합니다. 이 과정에서 자동 업데이트 경로가 `zed-i18n`으로 변경됩니다.

## 알려진 한계

메뉴, 버튼, 툴팁, 설정, 액션 설명 등 대부분의 UI 문자열은 직접 치환으로 처리됩니다. 다만 명령 팔레트나 키맵 편집기에서 런타임에 동적 생성되는 일부 action 이름은 별도 패치가 필요하므로 현재 다루고 있지 않습니다.

Zed 버전이 달라져도 안정적으로 패치를 할 수 있는 방법이 있다면 기여해주시면 고맙겠습니다.

## AI 활용 안내

이 프로젝트에서 대부분의 코드는 AI 도구를 활용해 작성되었으며, 모든 번역 또한 AI로 이루어졌습니다. 만약 코드나 번역에 이상한 부분이 있거나, 더 나은 방법이 있다고 생각하신다면 언제든지 PR을 열어주세요.

## 라이선스

Zed 소스에서 파생된 콘텐츠(`catalog/`, `translations/`, `manifest/`, 릴리즈 파일)는 [GPL-3.0](../../LICENSE)을 따릅니다. `zed-i18n` 자체 코드와 [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc)에서 추출한 번역 사전(`prompts/translation/glossary/`)은 [MIT](../../LICENSE-MIT) 라이선스를 따릅니다. VS Code 언어팩 콘텐츠의 저작권은 Microsoft Corporation에 있습니다.
