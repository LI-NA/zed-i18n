<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Den Zed-Editor ganz einfach in die eigene Sprache übersetzen.</strong></p>

  [![Zed v1.15.0](https://img.shields.io/badge/Zed-v1.15.0-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.15.0)
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

> Zed-i18n ist ein Community-Projekt ohne Verbindung zu Zed Industries und wird weder offiziell gesponsert noch unterstützt.

## Unterstützte Sprachen

Übersetzungen für 13 Sprachen sind derzeit unter `translations/` gebündelt. Alle aktuellen Übersetzungen wurden mit KI erstellt; Beiträge von Muttersprachlern sind willkommen.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Downloads

Die aktuellen Builds können über die Tabelle unten oder unter [Releases](https://github.com/LI-NA/zed-i18n/releases) heruntergeladen werden.

> [!IMPORTANT]
> Ab `v1.15.0-i18n.2` sind alle Sprachen in einem einzigen Build zusammengefasst. Im kombinierten Build erscheint die Benutzeroberfläche beim ersten Start in der Systemsprache; über die Einstellung `Display Language` (`ui_locale` in `settings.json`) lässt sie sich ändern. Bestehende sprachspezifische Builds werden durch das Auto-Update auf den kombinierten Build umgestellt; bei Bedarf ändert man die Sprache in den Einstellungen. Außerdem funktionieren bei einer Installation über Scoop die früheren sprachspezifischen Manifeste (etwa `zed-i18n-de-DE`) weiterhin, installieren jetzt aber für jede Sprache denselben Build.

| Plattform | aarch64 (arm64) | x86_64 (x64) |
| --- | --- | --- |
| Linux | [tar.gz](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-aarch64.tar.gz) / [deb](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-aarch64.deb) | [tar.gz](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-x86_64.tar.gz) / [deb](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-x86_64.deb) |
| macOS | [dmg](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-macos-aarch64.dmg) | [dmg](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-macos-x86_64.dmg) |
| Windows | [exe](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-aarch64.exe) / [zip](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-aarch64.zip) | [exe](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-x86_64.exe) / [zip](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-x86_64.zip) |

Details zum aktuellen Build-Prozess finden sich unter [Release-Builds](#release-builds); zum Selbstbauen siehe [Manueller Build](#manueller-build).

### Vertrauenswürdigkeit der Builds

- Die veröffentlichten Binärdateien sind nicht codesigniert; unter Windows oder macOS können Sicherheitswarnungen erscheinen.
- Alle Releases werden über `.github/workflows/i18n-release.yml` gebaut; die Build-Logs sind im [Actions](https://github.com/LI-NA/zed-i18n/actions)-Tab einsehbar.
- Die Zed-Quellen sind über den `zed_commit` SHA in `config/project.toml` festgeschrieben, sodass sich der exakt verwendete Quellstand für den Build verifizieren lässt.

Builds aus nicht vertrauenswürdigen Quellen sind zu vermeiden; wo möglich, sollte selbst gebaut werden, um Sicherheitsbedenken zu reduzieren.

### Öffnen unter macOS

Bei vertrauenswürdigen Dateien lässt sich die App im Finder per Rechtsklick und `Öffnen` starten, oder das Quarantäne-Attribut kann im Terminal mit `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` entfernt werden.

## Installation über einen Paketmanager

Unter macOS lässt sich die App über einen Homebrew-Cask installieren.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

Unter Windows fügt man das Scoop-Bucket hinzu und installiert die App anschließend.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n
```

Über Scoop installierte Builds können die integrierte Auto-Update-Funktion von Zed nicht nutzen; sie werden stattdessen mit `scoop update` aktualisiert.

## Entwicklungsumgebung einrichten

Voraussetzungen: Python 3.12 oder neuer sowie [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Alle Befehle werden als `uv run zed-i18n <command>` ausgeführt.

## Verwendung

Die Ziel-Zed-Version wird in `config/project.toml` festgelegt. `fetch-zed` bereitet sowohl den Checkout zum Anwenden der Übersetzungen und für Builds als auch den sauberen Checkout für die String-Extraktion und -Überprüfung vor.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/<version>-clean-extract
# Nur bei einer Versionsaktualisierung
uv run zed-i18n generate-version-diff
uv run zed-i18n audit-candidates --zed-root .cache/zed/<version>-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/<version>-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` durchsucht die Zed-Rust-Quellen nach UI-String-Kandidaten und schreibt sie in `catalog/en-US.json` sowie `manifest/ui-strings.json`. Übersetzungsergebnisse werden in `translations/<language>.json` gespeichert.

Beim Aktualisieren der Version schreibt `generate-version-diff` die Schlüsseländerungen gegenüber der vorherigen Version in `key-changes.json` unter `reports/version-diff/`; `prepare-translation` liest den Bericht automatisch und nimmt frühere Übersetzungen ähnlicher Schlüssel als Referenz in die Batches auf. Batches werden auch ohne diesen Bericht normal erstellt.

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

1. Den Übersetzungs-Stilguide in `prompts/translation/<language>.md` und das kuratierte Glossar in `prompts/translation/glossary/<lang>.md` verfassen.
2. Batches mit `prepare-translation` generieren.
3. Die KI-erzeugten JSON-Ergebnisse mit `merge-translation` zusammenführen.
4. Das Ergebnis mit `validate` überprüfen.

Sprachspezifische Richtlinien befinden sich in `prompts/translation/<language>.md`. Fehlt die Datei, wird `prompts/translation/TEMPLATE.md` als Standard verwendet.

## Manueller Build

Unter Windows werden [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), das Windows SDK, CMake und [Rust](https://rustup.rs/) benötigt. Es empfiehlt sich, den Build-Cache versionsübergreifend über `.cache/zed/target` zu teilen. Ein Beispiel-Build sieht folgendermaßen aus:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.15.0
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Release-Builds

Release-Builds laufen automatisch über GitHub Actions, definiert in `.github/workflows/i18n-release.yml`. Die Zed-Quellen sind auf den `zed_version`-Tag und den `zed_commit`-SHA in `config/project.toml` festgeschrieben.

Der Release-Workflow wendet `config/distribution.toml` an, um die zed-i18n-Kennung, die About-Informationen und die automatischen Updates anzupassen. Dadurch werden Update-Prüfungen auf `zed-i18n` umgeleitet.

> **Hinweis:** Zed-i18n-Builds ändern den Auto-Update-Endpunkt vom offiziellen Zed-Server auf die `manifest.json` in den Releases dieses Repositorys. Wer kein automatisches Update wünscht, kann dieses in den Einstellungen deaktivieren.

### Telemetrie

Zed-i18n ändert das Telemetrieverhalten nicht. Mit den Standardeinstellungen können anonyme Nutzungsmetriken und Crash-Berichte an die Server von Zed Industries gesendet werden. Um die Telemetrie zu deaktivieren, setzen Sie `telemetry.metrics` und `telemetry.diagnostics` in den Zed-Einstellungen auf `false`.

## Bekannte Einschränkungen

Die meisten UI-Strings — Menüs, Schaltflächen, Tooltips, Einstellungen, Aktionsbeschreibungen — werden durch Hilfsfunktionen ersetzt, die die Lokalisierung anwenden. Einige Aktionsnamen, die zur Laufzeit dynamisch in der Befehlspalette oder im Tastenzuordnungs-Editor erzeugt werden, erfordern jedoch einen gesonderten Patch und sind noch nicht abgedeckt.

Für diese nicht übersetzten Teile sind Beiträge willkommen, die zeigen, wie sich Patches zuverlässig über Zed-Versionen hinweg einspielen lassen.

## Hinweis zur KI-Nutzung

Ein Großteil des Codes in diesem Projekt wurde mithilfe von KI-Werkzeugen geschrieben, und jede Übersetzung wurde von KI erstellt. Die Übersetzungsergebnisse wurden nicht direkt von Menschen geprüft, weshalb fehlerhafte Übersetzungen oder Probleme beim Branding möglich sind. Wer in den Übersetzungen — auch in diesem Dokument — ein Problem entdeckt oder eine bessere Übersetzung vorschlagen möchte, kann jederzeit ein Issue oder einen PR eröffnen.

### Übersetzungsprozess

Alle Übersetzungen haben den unter [KI-gestützte Übersetzung](#ki-gestützte-übersetzung) beschriebenen Prozess durchlaufen.

1. `extract` ermittelt UI-String-Kandidaten aus den Zed-Quellen. Die Ergebnisse werden in `catalog/en-US.json` und `manifest/ui-strings.json` gespeichert.
2. `audit-candidates` prüft, welche Strings von den Extraktionsregeln erfasst und welche übersehen wurden, und dient dazu, die tatsächliche Liste der Übersetzungsziele (`accepted`) zu verwalten.
3. `prepare-translation` erzeugt sprachspezifische Batches und bündelt darin den Stilguide, das Glossar und – sofern verfügbar – Referenzen aus VS Code-Sprachpaketen.
4. Ein KI-Modell schreibt das Übersetzungsergebnis als JSON Batch für Batch.
5. `merge-translation` führt die Ergebnisse zusammen, und `validate` prüft auf fehlende oder zusätzliche Einträge, Platzhalter sowie die Konsistenz geschützter Tokens.

Die anfänglichen Übersetzungen durchliefen diesen Prozess für jede Sprache mit zwei Modellen — `Sonnet 4.6` und `GPT-5.5` —, die jeweils eine vollständige eigenständige Übersetzung erzeugten, die anschließend erneut überprüft wurde. Die beiden fertiggestellten Übersetzungsdateien wurden anschließend mit `Opus 4.6` nochmals geprüft und zur finalen Ausgabe zusammengeführt.

Seitdem werden beim Hinzufügen und Verbessern von Übersetzungen aktiv die neuesten Modelle eingesetzt; derzeit sind `Sonnet 5`, `Opus 5` und `GPT-5.6 Sol` die primären Modelle.

Weitere Details zum KI-Übersetzungsprozess finden sich in den Dateien unter `prompts/commands`.

## Lizenz

Inhalte, die aus Zed-Quellen abgeleitet wurden (`catalog/`, `translations/`, `manifest/`, Release-Artefakte usw.), stehen unter der [GPL-3.0](../../LICENSE)-Lizenz. Dieses Projekt verteilt modifizierte Builds von Zed. Der `zed-i18n`-Quellcode und das aus den [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) referenzierte Material stehen unter der [MIT](../../LICENSE-MIT)-Lizenz.

Zed und das Zed-Logo sind Eigentum von Zed Industries. Die Inhalte von VS Code und den VS Code-Sprachpaketen unterliegen dem Copyright der Microsoft Corporation.
