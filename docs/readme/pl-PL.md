<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Z łatwością przetłumacz edytor Zed na swój język.</strong></p>

  [![Zed v1.7.2](https://img.shields.io/badge/Zed-v1.7.2-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.7.2)
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

Zed-i18n to narzędzie, które wyodrębnia ciągi interfejsu użytkownika z wydań edytora [Zed](https://zed.dev) i stosuje tłumaczenia, aby tworzyć wielojęzyczne kompilacje.

> Zed-i18n to projekt społecznościowy niezwiązany z Zed Industries; nie jest oficjalnie sponsorowany ani autoryzowany.

## Obsługiwane języki

Obecnie w katalogu `translations/` znajdują się tłumaczenia dla 13 języków. Wszystkie obecne tłumaczenia zostały wygenerowane przez AI; wkład rodzimych użytkowników języka jest mile widziany.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Pobieranie

Najnowsze kompilacje można pobrać ze strony [Releases](https://github.com/LI-NA/zed-i18n/releases).

Szczegóły procesu kompilacji najnowszych wydań znajdują się w sekcji [Kompilacje wydaniowe](#kompilacje-wydaniowe), a jeśli chcesz zbudować Zed-i18n samodzielnie, zajrzyj do sekcji [Ręczna kompilacja](#ręczna-kompilacja).

### Wiarygodność kompilacji

- Wydawane pliki binarne nie są podpisane kodem. W systemach Windows i macOS mogą pojawiać się ostrzeżenia bezpieczeństwa.
- Wszystkie wydania są budowane przy użyciu `.github/workflows/i18n-release.yml`, a logi kompilacji można szczegółowo przejrzeć w zakładce [Actions](https://github.com/LI-NA/zed-i18n/actions).
- Źródło Zed jest przypięte do skrótu SHA `zed_commit` w pliku `config/project.toml`, dzięki czemu można zweryfikować, na podstawie jakiego dokładnie kodu źródłowego powstała kompilacja.

Unikaj kompilacji z niezaufanych źródeł; tam, gdzie to możliwe, buduj samodzielnie, aby ograniczyć zagrożenia bezpieczeństwa.

### Otwieranie w systemie macOS

W przypadku zaufanych plików w Finderze kliknij prawym przyciskiem i wybierz `Otwórz`, albo w Terminalu usuń atrybut kwarantanny poleceniem `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Instalacja przez menedżer pakietów

W systemie macOS możesz zainstalować aplikację za pomocą caska Homebrew.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

Automatycznie instalowany jest język zgodny z językiem systemu, a w razie braku dopasowania używany jest `ko-KR`. Aby wybrać konkretny język, użyj opcji `--language` w Homebrew.

```bash
brew install --cask zed-i18n --language=pl-PL
```

W systemie Windows dodaj bucket Scoopa, a następnie zainstaluj wybrany język.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-pl-PL
```

Instalacje przez Scoopa nie mogą korzystać z wbudowanej automatycznej aktualizacji Zed; aktualizuje się je poleceniem `scoop update`.

## Konfiguracja środowiska deweloperskiego

Wymagane są Python 3.12 lub nowszy oraz [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Wszystkie polecenia uruchamia się jako `uv run zed-i18n <command>`.

## Użycie

Docelowa wersja Zed jest określona w `config/project.toml`. Polecenie `fetch-zed` przygotowuje zarówno kopię do stosowania tłumaczeń i kompilacji, jak i czystą kopię używaną do wyodrębniania i przeglądu ciągów.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.7.2-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.7.2-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.7.2-clean-extract
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

1. Napisz przewodnik stylistyczny tłumaczenia w `prompts/translation/<language>.md`, a kuratorowany słownik terminów w `prompts/translation/glossary/<lang>.md`.
2. Wygeneruj partie za pomocą `prepare-translation`.
3. Scal wyniki JSON wygenerowane przez AI za pomocą `merge-translation`.
4. Zweryfikuj wynik za pomocą `validate`.

Wytyczne dla poszczególnych języków znajdują się w `prompts/translation/<language>.md`. Jeśli plik nie istnieje, domyślnie używany jest `prompts/translation/TEMPLATE.md`.

## Ręczna kompilacja

W systemie Windows wymagane są [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake oraz [Rust](https://rustup.rs/). Zaleca się współdzielenie pamięci podręcznej kompilacji między wersjami za pośrednictwem `.cache/zed/target`. Przykładowa kompilacja wygląda następująco:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.7.2
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Kompilacje wydaniowe

Kompilacje wydaniowe są wykonywane automatycznie przez GitHub Actions zgodnie z przepływem pracy zdefiniowanym w `.github/workflows/i18n-release.yml`. Kod źródłowy Zed jest przypięty do tagu `zed_version` i skrótu SHA `zed_commit` w pliku `config/project.toml`.

Przepływ pracy wydania stosuje `config/distribution.toml` wraz z tłumaczeniami dla poszczególnych języków, aby zaktualizować identyfikator `zed-i18n`, informacje w sekcji About oraz ścieżkę automatycznych aktualizacji. W tym procesie ścieżka automatycznych aktualizacji zmienia się na `zed-i18n`.

> **Uwaga:** kompilacje Zed-i18n zmieniają punkt końcowy automatycznych aktualizacji z oficjalnego serwera Zed na plik `manifest.json` w wydaniach tego repozytorium. Jeśli wolisz, możesz wyłączyć automatyczne aktualizacje w ustawieniach.

### Telemetria

Zed-i18n nie zmienia zachowania telemetrii. Przy ustawieniach domyślnych anonimowe metryki użycia oraz raporty awarii mogą być wysyłane na serwery Zed Industries. Aby wyłączyć telemetrię, w ustawieniach Zed ustaw `telemetry.metrics` oraz `telemetry.diagnostics` na `false`.

## Znane ograniczenia

Większość ciągów interfejsu użytkownika — menu, przyciski, podpowiedzi, ustawienia, opisy akcji — jest obsługiwana przez bezpośrednie podstawianie. Jednak niektóre nazwy akcji generowane dynamicznie w czasie działania programu w Palecie poleceń lub Edytorze mapy klawiszy wymagają oddzielnej poprawki i nie są jeszcze obsługiwane.

W odniesieniu do tych nieprzetłumaczonych fragmentów chętnie przyjmiemy wkład dotyczący sposobu niezawodnego stosowania poprawek w różnych wersjach Zed.

## Informacja o użyciu AI

Większość kodu w tym projekcie została napisana przy pomocy narzędzi AI, a wszystkie tłumaczenia zostały wygenerowane przez AI. Wyniki tłumaczeń nie zostały bezpośrednio zweryfikowane przez człowieka, dlatego możliwe są błędy w tłumaczeniach oraz kwestie związane z brandingiem. Jeśli zauważysz problem z tłumaczeniem — także w tym dokumencie — albo masz propozycję lepszego tłumaczenia, zapraszamy do zgłoszenia issue lub otwarcia PR-a.

### Proces tłumaczenia

Wszystkie tłumaczenia zostały przeprowadzone zgodnie z procesem opisanym w sekcji [Tłumaczenie z użyciem AI](#tłumaczenie-z-użyciem-ai).

1. `extract` pobiera kandydatów na ciągi interfejsu użytkownika ze źródeł Zed. Wyniki są zapisywane w `catalog/en-US.json` oraz `manifest/ui-strings.json`.
2. `audit-candidates` sprawdza, które ciągi reguły ekstrakcji wychwyciły, a które pominęły — służy to do zarządzania faktyczną listą tłumaczonych ciągów (`accepted`).
3. `prepare-translation` generuje partie dla poszczególnych języków, dołączając przewodnik stylistyczny, słownik terminów oraz — jeśli są dostępne — materiały referencyjne z pakietów językowych VS Code.
4. Model AI tworzy wynik tłumaczenia w formacie JSON, partia po partii.
5. `merge-translation` scala wyniki, a `validate` weryfikuje brakujące lub nadmiarowe wpisy, symbole zastępcze oraz spójność tokenów chronionych.

Obecnie zarejestrowane tłumaczenia przeszły powyższy proces dla każdego języka z użyciem dwóch modeli — `Sonnet 4.6` oraz `GPT-5.5` — z których każdy niezależnie wygenerował pełne tłumaczenie poddane następnie ponownej weryfikacji. Oba ukończone tłumaczenia zostały później ponownie zweryfikowane i scalone w wynik końcowy z wykorzystaniem modelu `Opus 4.6`.

Więcej informacji o procesie tłumaczenia z użyciem AI znajdziesz w plikach w katalogu `prompts\commands`.

## Licencja

Treści pochodzące ze źródeł Zed (`catalog/`, `translations/`, `manifest/`, artefakty wydań itp.) są objęte licencją [GPL-3.0](../../LICENSE). Projekt ten dystrybuuje zmodyfikowane kompilacje Zed. Kod źródłowy `zed-i18n` oraz materiały referencyjne z [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) są objęte licencją [MIT](../../LICENSE-MIT).

Zed oraz logo Zed są własnością Zed Industries, a prawa autorskie do zawartości VS Code oraz pakietów językowych VS Code należą do Microsoft Corporation.
