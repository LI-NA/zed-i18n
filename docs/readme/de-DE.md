<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Den Zed-Editor ganz einfach in die eigene Sprache übersetzen.</strong></p>

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
    Deutsch ·
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
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Einführung

Zed-i18n ist ein Toolkit, das UI-Strings aus Release-Builds des [Zed](https://zed.dev)-Editors extrahiert und Übersetzungen einsetzt, um mehrsprachige Builds zu erstellen.

## Unterstützte Sprachen

Übersetzungen für 13 Sprachen sind derzeit unter `translations/` gebündelt.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Downloads

Die aktuellen Binärdateien sind unter [Releases](https://github.com/LI-NA/zed-i18n/releases) verfügbar. Wer das Projekt lieber selbst bauen möchte, folgt den nachstehenden Schritten.

Die Release-Dateien sind derzeit nicht codesigniert. Falls macOS die App blockiert, öffnen Sie nur vertrauenswürdige Dateien im Finder per Rechtsklick und `Öffnen`, oder entfernen Sie das Quarantäne-Attribut mit `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Installation

Voraussetzungen: Python 3.12 oder neuer sowie [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Alle Befehle werden als `uv run zed-i18n <command>` ausgeführt.

## Verwendung

Die Ziel-Zed-Version wird in `config/project.toml` festgelegt. `fetch-zed` bereitet sowohl den Checkout zum Anwenden der Übersetzungen und für Builds als auch den sauberen Checkout für die String-Extraktion und -Überprüfung vor.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` durchsucht die Zed-Rust-Quellen nach UI-String-Kandidaten und schreibt sie in `catalog/en-US.json` sowie `manifest/ui-strings.json`. Übersetzungsergebnisse werden in `translations/<language>.json` gespeichert.

Neu entdeckte Strings landen in `manifest/ui-strings.json` mit dem Status `needs_review`. Nur Strings, die tatsächlich in der Benutzeroberfläche angezeigt werden, sollten auf `accepted` gesetzt und anschließend übersetzt werden.

## KI-gestützte Übersetzung

Für KI-gesteuerte Übersetzungsläufe folgt man `prompts/commands/translation-start.md`. Um Ergebnisse mehrerer Modelle zu vergleichen und zusammenzuführen, dient `prompts/commands/translation-review.md`.

Sollen ausschließlich neu hinzugefügte Schlüssel übersetzt und bestehende Übersetzungen unverändert gelassen werden, sind die Dateien mit dem Suffix `new-keys` zu verwenden.

Um Übersetzungsreferenzen aus VS Code in die Batches einzubeziehen, müssen die nachstehenden Repositories vor dem Ausführen von `prepare-translation` vorbereitet werden. Batches werden auch ohne diese Repositories normal erstellt.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Beim Hinzufügen einer neuen Sprache:

1. Einen Stilguide und ein Glossar in `prompts/translation/<language>.md` verfassen.
2. Batches mit `prepare-translation` generieren.
3. Die KI-erzeugten JSON-Ergebnisse mit `merge-translation` zusammenführen.
4. Das Ergebnis mit `validate` überprüfen.

Sprachspezifische Richtlinien befinden sich in `prompts/translation/<language>.md`. Fehlt die Datei, wird `prompts/translation/TEMPLATE.md` als Standard verwendet.

## Manueller Build

Unter Windows werden [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), das Windows SDK, CMake und [Rust](https://rustup.rs/) benötigt. Es empfiehlt sich, den Build-Cache versionsübergreifend über `.cache/zed/target` zu teilen. Ein Beispiel-Build sieht folgendermaßen aus:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Release-Builds

Release-Builds laufen automatisch über GitHub Actions, definiert in `.github/workflows/i18n-release.yml`. Die Zed-Quellen sind auf den `zed_version`-Tag und den `zed_commit`-SHA in `config/project.toml` festgeschrieben.

Der Release-Workflow wendet `config/distribution.toml` an, um die zed-i18n-Kennung, die About-Informationen und den automatischen Update-Pfad anzupassen. Dadurch wird der automatische Update-Pfad auf `zed-i18n` umgeschrieben.

## Bekannte Einschränkungen

Die meisten UI-Strings — Menüs, Schaltflächen, Tooltips, Einstellungen, Aktionsbeschreibungen — werden durch direkte Substitution behandelt. Einige Aktionsnamen, die zur Laufzeit dynamisch in der Befehlspalette oder im Tastenzuordnungs-Editor erzeugt werden, erfordern jedoch einen gesonderten Patch und sind noch nicht abgedeckt.

Wer einen Weg kennt, Patches zuverlässig über Zed-Versionen hinweg einzuspielen, ist herzlich eingeladen, einen Beitrag zu leisten.

## Hinweis zur KI-Nutzung

Ein Großteil des Codes in diesem Projekt wurde mithilfe von KI-Werkzeugen geschrieben, und jede Übersetzung wurde von KI erstellt. Wer im Code oder in den Übersetzungen etwas Unstimmiges entdeckt oder einen besseren Ansatz kennt, darf gerne einen PR eröffnen.

## Lizenz

Inhalte, die aus Zed-Quellen abgeleitet wurden (`catalog/`, `translations/`, `manifest/` sowie Release-Artefakte), stehen unter der [GPL-3.0](../../LICENSE)-Lizenz. Der `zed-i18n`-Quellcode und die Übersetzungsglossare (`prompts/translation/glossary/`), die aus [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) extrahiert wurden, stehen unter der [MIT](../../LICENSE-MIT)-Lizenz. Die Inhalte der VS Code-Sprachpakete unterliegen dem Copyright der Microsoft Corporation.
