<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Zed 에디터를 손쉽게 자신의 언어로 번역해 보세요.</strong></p>

  [![Zed v1.3.6](https://img.shields.io/badge/Zed-v1.3.6-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.3.6)
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

> Zed-i18n은 Zed Industries와 무관한 커뮤니티 프로젝트로, 공식적인 후원이나 인증을 받지 않았습니다.

## 지원 언어

현재 13개 언어의 번역이 `translations/`에 포함되어 있습니다. 모든 번역은 AI로 진행된 상태이며, 각각의 언어에 대해 원어민의 기여를 환영합니다.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## 다운로드

[Releases](https://github.com/LI-NA/zed-i18n/releases)에서 최신 빌드를 다운로드받을 수 있습니다.

최신 빌드 과정은 [릴리즈 빌드](#릴리즈-빌드)에서 더 자세히 확인하실 수 있으며, 직접 빌드하려면 [수동 빌드](#수동-빌드)를 참고해 주세요.

### 빌드 신뢰성

- 현재 배포 파일에는 코드 서명이 적용되어 있지 않습니다. Windows나 macOS에서 보안 경고가 있을 수 있습니다.
- 모든 릴리즈는 `.github/workflows/i18n-release.yml`을 통해 빌드되며, 빌드 로그를 [Actions](https://github.com/LI-NA/zed-i18n/actions) 탭에서 자세히 확인할 수 있습니다.
- Zed 원본은 `config/project.toml`의 `zed_commit` SHA로 고정되어 있어, 정확히 어느 소스를 기준으로 빌드하는지 확인할 수 있습니다.

신뢰할 수 없는 출처의 빌드는 사용하지 마시고, 가능한 경우 직접 빌드하여 사용하시면 보안 문제를 완화할 수 있습니다.

### macOS에서 열리지 않을 때

신뢰하는 파일에 한해 Finder에서 우클릭 후 `열기`를 선택하거나, 터미널에서 `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`처럼 앱 경로를 지정해 격리 속성을 제거할 수 있습니다.

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
uv run zed-i18n extract --zed-root .cache/zed/v1.3.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.3.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.3.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract`는 Zed Rust 소스에서 UI 문자열 후보를 찾아 `catalog/en-US.json`과 `manifest/ui-strings.json`에 기록합니다. 번역 결과는 `translations/<language>.json`에 저장됩니다.

새로 발견된 문자열은 `manifest/ui-strings.json`에 `needs_review` 상태로 들어갑니다. 실제 UI에 노출되는 문자열만 `accepted`로 바꾸고 번역을 진행합니다.

## AI 번역

AI 번역 작업은 `prompts/commands/translation-start.md`를 참고해 진행합니다. 여러 모델의 결과를 비교·병합하려면 `prompts/commands/translation-review.md`를 사용합니다.

만약 기존 번역은 그대로 두고 새로운 키만 번역하고 싶은 경우 `new-keys`가 붙은 파일을 참고하세요.

VS Code 번역 참고 자료를 배치에 포함하려면 아래 저장소를 준비한 뒤 `prepare-translation`을 실행합니다. 없어도 번역 배치는 정상 생성됩니다.

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
cd .cache\zed\v1.3.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## 릴리즈 빌드

릴리즈 빌드는 GitHub Actions를 통해 자동으로 이루어지며, `.github/workflows/i18n-release.yml`에 정의되어 있습니다. Zed 원본은 `config/project.toml`의 `zed_version` 태그와 `zed_commit` SHA로 고정한 버전을 사용합니다.

릴리즈 workflow는 언어별 번역과 함께 `config/distribution.toml`을 적용해 zed-i18n 식별자, About 정보, 자동 업데이트 경로를 패치합니다. 이 과정에서 자동 업데이트 경로가 `zed-i18n`으로 변경됩니다.

> **주의 사항:** Zed-i18n 빌드는 자동 업데이트 경로를 Zed 공식 서버에서 본 저장소 릴리즈의 `manifest.json` 파일로 변경합니다. 자동 업데이트를 원하지 않으신다면 설정에서 비활성화할 수 있습니다.

### 텔레메트리

Zed-i18n은 텔레메트리 동작을 변경하지 않습니다. 기본 설정에서는 익명 사용 지표와 크래시 보고서가 Zed Industries의 서버로 전송될 수 있습니다. 텔레메트리를 끄려면 Zed 설정에서 `telemetry.metrics`·`telemetry.diagnostics`를 `false`로 설정하세요.

## 알려진 한계

메뉴, 버튼, 툴팁, 설정, 액션 설명 등 대부분의 UI 문자열은 직접 치환으로 처리됩니다. 다만 명령 팔레트나 키맵 편집기에서 런타임에 동적 생성되는 일부 action 이름은 별도 패치가 필요하므로 현재 다루고 있지 않습니다.

미번역된 부분에 대해 Zed 버전이 달라져도 안정적으로 패치를 할 수 있는 방법이 있다면 기여해 주시면 고맙겠습니다.

## AI 활용 안내

이 프로젝트에서 대부분의 코드는 AI 도구를 활용해 작성되었으며, 모든 번역 또한 AI로 이루어졌습니다. 번역 결과를 사람이 직접 검수하지 못했기 때문에 잘못된 번역이나 브랜딩 문제가 있을 수 있습니다. 이 문서를 포함하여 번역에 문제가 있다고 생각되시거나, 더 나은 번역이 가능하다면 언제든지 이슈나 PR을 남겨주세요.

### 번역 과정

모든 번역은 [AI 번역](#ai-번역)에서 설명한 과정을 거쳐 진행되었습니다.

1. `extract`로 Zed 소스에서 UI 문자열 후보를 추출합니다. 결과는 `catalog/en-US.json`, `manifest/ui-strings.json`에 저장됩니다.
2. `audit-candidates`로 추출 규칙에 포함된 문자열과 빠진 후보를 점검하고, 이를 바탕으로 실제 번역 대상(`accepted`)을 관리합니다.
3. `prepare-translation`으로 언어별 배치를 생성합니다. 스타일 가이드, 용어집, 가능한 경우 VS Code 언어팩 참조가 함께 포함됩니다.
4. AI 모델이 배치 단위로 번역 결과 JSON을 작성합니다.
5. `merge-translation`으로 결과를 병합하고, `validate`로 누락·추가 항목, 플레이스홀더, 보호 토큰 일치 여부를 검증합니다.

현재 등록된 번역은 모든 언어에 대해 위 과정을 반복하여, `Sonnet 4.6`과 `GPT-5.5` 두 가지 모델로 각각 독립적인 전체 번역과 재검수를 거친 결과입니다. 이후 완성된 두 번역 파일을 `Opus 4.6` 모델로 전체 재검수·병합해 최종 결과를 만들었습니다.

AI 번역 과정은 `prompts\commands` 아래에서 더 자세히 확인해 보실 수 있습니다.

## 라이선스

Zed 소스에서 파생된 콘텐츠(`catalog/`, `translations/`, `manifest/`, 릴리즈 파일 등)는 [GPL-3.0](../../LICENSE)을 따릅니다. 본 프로젝트는 Zed의 수정된 빌드를 배포합니다. `zed-i18n` 자체 코드와 [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc)에서 추출한 번역 사전(`prompts/translation/glossary/`)은 [MIT](../../LICENSE-MIT) 라이선스를 따릅니다.

Zed와 Zed 로고는 Zed Industries의 자산이며, VS Code 및 VS Code 언어팩 콘텐츠의 저작권은 Microsoft Corporation에 있습니다.
