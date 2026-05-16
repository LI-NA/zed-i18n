<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Z łatwością przetłumacz edytor Zed na swój język.</strong></p>

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
    <a href="ko-KR.md">한국어</a> ·
    Polski ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Wprowadzenie

zed-i18n to narzędzie, które wyodrębnia ciągi interfejsu użytkownika z wydań edytora [Zed](https://zed.dev) i stosuje tłumaczenia, aby tworzyć wielojęzyczne kompilacje.

## Obsługiwane języki

Obecnie w katalogu `translations/` znajdują się tłumaczenia dla 13 języków.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Pobieranie

Najnowsze kompilacje można pobrać ze strony [Releases](https://github.com/LI-NA/zed-i18n/releases). Jeśli wolisz zbudować je samodzielnie, wykonaj poniższe kroki.

Pliki dystrybucyjne nie są obecnie podpisane kodem. Jeśli macOS je zablokuje, otwieraj w ten sposób tylko zaufane pliki: w Finderze kliknij prawym przyciskiem i wybierz `Otwórz`, albo usuń atrybut kwarantanny poleceniem `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Instalacja

Wymagane są Python 3.12 lub nowszy oraz [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Wszystkie polecenia uruchamia się jako `uv run zed-i18n <command>`.

## Użycie

Docelowa wersja Zed jest określona w `config/project.toml`. Polecenie `fetch-zed` przygotowuje zarówno kopię do stosowania tłumaczeń i kompilacji, jak i czystą kopię używaną do wyodrębniania i przeglądu ciągów.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

Polecenie `extract` przeszukuje źródła Rust edytora Zed w poszukiwaniu kandydatów na ciągi interfejsu użytkownika i zapisuje je do `catalog/en-US.json` oraz `manifest/ui-strings.json`. Wyniki tłumaczeń są przechowywane w `translations/<language>.json`.

Nowo odkryte ciągi trafiają do `manifest/ui-strings.json` ze statusem `needs_review`. Tylko ciągi faktycznie wyświetlane w interfejsie użytkownika powinny zostać oznaczone jako `accepted`, a następnie przetłumaczone.

## Tłumaczenie z użyciem AI

Aby przeprowadzić tłumaczenie przy użyciu AI, postępuj zgodnie z instrukcjami w `prompts/commands/translation-start.md`. Do porównywania i scalania wyników z wielu modeli służy plik `prompts/commands/translation-review.md`.

Jeśli chcesz przetłumaczyć tylko nowo dodane klucze, nie naruszając istniejących tłumaczeń, skorzystaj z plików z sufiksem `new-keys`.

Aby uwzględnić w partiach materiały referencyjne z tłumaczeń VS Code, przed uruchomieniem `prepare-translation` przygotuj poniższe repozytoria. Partie zostaną wygenerowane poprawnie także bez nich.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Podczas dodawania nowego języka:

1. Napisz przewodnik stylistyczny i słownik terminów w `prompts/translation/<language>.md`.
2. Wygeneruj partie za pomocą `prepare-translation`.
3. Scal wyniki JSON wygenerowane przez AI za pomocą `merge-translation`.
4. Zweryfikuj wynik za pomocą `validate`.

Wytyczne dla poszczególnych języków znajdują się w `prompts/translation/<language>.md`. Jeśli plik nie istnieje, domyślnie używany jest `prompts/translation/TEMPLATE.md`.

## Ręczna kompilacja

W systemie Windows wymagane są [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake oraz [Rust](https://rustup.rs/). Zaleca się współdzielenie pamięci podręcznej kompilacji między wersjami za pośrednictwem `.cache/zed/target`. Przykładowa kompilacja wygląda następująco:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Kompilacje wydaniowe

Kompilacje wydaniowe są wykonywane automatycznie przez GitHub Actions zgodnie z przepływem pracy zdefiniowanym w `.github/workflows/i18n-release.yml`. Kod źródłowy Zed jest przypięty do tagu `zed_version` i skrótu SHA `zed_commit` w pliku `config/project.toml`.

Przepływ pracy wydania stosuje `config/distribution.toml`, aby zaktualizować identyfikator `zed-i18n`, informacje w sekcji About oraz ścieżkę automatycznych aktualizacji. W tym procesie ścieżka automatycznych aktualizacji zmienia się na `zed-i18n`.

## Znane ograniczenia

Większość ciągów interfejsu użytkownika — menu, przyciski, podpowiedzi, ustawienia, opisy akcji — jest obsługiwana przez bezpośrednie podstawianie. Jednak niektóre nazwy akcji generowane dynamicznie w czasie działania programu w Palecie poleceń lub Edytorze mapy klawiszy wymagają oddzielnej poprawki i nie są jeszcze obsługiwane.

Jeśli znasz sposób na niezawodne stosowanie poprawek w różnych wersjach Zed, będziemy wdzięczni za wkład.

## Informacja o użyciu AI

Większość kodu w tym projekcie została napisana przy pomocy narzędzi AI, a wszystkie tłumaczenia zostały wygenerowane przez AI. Jeśli zauważysz coś nieprawidłowego w kodzie lub tłumaczeniach bądź uważasz, że istnieje lepsze podejście, zapraszamy do otwarcia PR-a.

## Licencja

Treści pochodzące ze źródeł Zed (`catalog/`, `translations/`, `manifest/` oraz artefakty wydań) są objęte licencją [GPL-3.0](../../LICENSE). Kod źródłowy `zed-i18n` oraz słowniki tłumaczeń (`prompts/translation/glossary/`) wyodrębnione z [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) są objęte licencją [MIT](../../LICENSE-MIT). Prawa autorskie do zawartości pakietów językowych VS Code należą do Microsoft Corporation.
