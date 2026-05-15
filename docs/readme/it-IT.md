<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Traduci l'editor Zed nella tua lingua con facilità.</strong></p>

  [![Zed v1.2.3](https://img.shields.io/badge/Zed-v1.2.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.3)
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
    Italiano ·
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

## Introduzione

zed-i18n è uno strumento che estrae le stringhe dell'interfaccia utente dalle versioni rilasciate dell'editor [Zed](https://zed.dev) e applica le traduzioni per produrre build multilingue.

## Lingue supportate

Le traduzioni per 13 lingue sono attualmente disponibili nella cartella `translations/`.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Download

È possibile scaricare i binari più recenti dalla pagina [Releases](https://github.com/LI-NA/zed-i18n/releases). Per chi preferisce compilare il progetto autonomamente, seguire i passaggi indicati di seguito.

I file distribuiti non sono ancora firmati. Se macOS blocca l'app, aprire solo file attendibili dal Finder con clic destro e `Apri`, oppure rimuovere l'attributo di quarantena con `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Installazione

Richiede Python 3.12 o versione successiva e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Tutti i comandi vengono eseguiti tramite `uv run zed-i18n <command>`.

## Utilizzo

La versione di Zed di destinazione è impostata in `config/project.toml`. Il comando `fetch-zed` prepara sia il checkout per `apply` e build sia il checkout pulito utilizzato per l'estrazione delle stringhe e la revisione.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

Il comando `extract` analizza i sorgenti Rust di Zed alla ricerca di stringhe candidate dell'interfaccia utente e le scrive in `catalog/en-US.json` e `manifest/ui-strings.json`. I risultati delle traduzioni vengono salvati in `translations/<language>.json`.

Le stringhe appena individuate vengono inserite in `manifest/ui-strings.json` con lo stato `needs_review`. Solo le stringhe effettivamente visualizzate nell'interfaccia utente devono essere impostate su `accepted` e quindi tradotte.

## Traduzione tramite AI

Per le sessioni di traduzione assistite dall'AI, seguire le istruzioni in `prompts/commands/translation-start.md`. Per confrontare e unire i risultati provenienti da più modelli, usare `prompts/commands/translation-review.md`.

Per tradurre solo le chiavi aggiunte di recente lasciando intatte le traduzioni esistenti, fare riferimento ai file con il suffisso `new-keys`.

Per includere i riferimenti di traduzione di VS Code nei batch, clonare i repository seguenti prima di eseguire `prepare-translation`. I batch vengono comunque generati normalmente anche se non sono disponibili.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Per aggiungere una nuova lingua:

1. Scrivere una guida di stile e un glossario in `prompts/translation/<language>.md`.
2. Generare i batch con `prepare-translation`.
3. Unire i risultati JSON prodotti dall'AI tramite `merge-translation`.
4. Validare il risultato con `validate`.

Le linee guida per ciascuna lingua si trovano in `prompts/translation/<language>.md`. Se il file è assente, viene utilizzato `prompts/translation/TEMPLATE.md` come predefinito.

## Build manuale

Su Windows sono necessari [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), il Windows SDK, CMake e [Rust](https://rustup.rs/). È consigliabile condividere la cache di build tra le versioni tramite `.cache/zed/target`. Un esempio di build è il seguente:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.3
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Build di rilascio

Le build di rilascio vengono eseguite automaticamente tramite GitHub Actions; il workflow è definito in `.github/workflows/i18n-release.yml`. I sorgenti di Zed sono fissati al tag `zed_version` e al SHA `zed_commit` in `config/project.toml`.

Il workflow di rilascio applica `config/distribution.toml` per aggiornare l'identificativo zed-i18n, le informazioni della schermata About e il percorso di aggiornamento automatico. In questo modo il percorso di aggiornamento automatico viene reindirizzato a `zed-i18n`.

## Limitazioni note

La maggior parte delle stringhe dell'interfaccia utente — menu, pulsanti, tooltip, impostazioni, descrizioni delle azioni — viene gestita tramite sostituzione diretta. Tuttavia, alcuni nomi di azioni generati dinamicamente a runtime nel riquadro comandi o nell'Editor mappa tasti richiedono una patch separata e non sono ancora coperti.

Se si conosce un metodo per applicare patch in modo affidabile tra le versioni di Zed, i contributi sono molto benvenuti.

## Sull'utilizzo dell'AI

La maggior parte del codice di questo progetto è stata scritta con l'aiuto di strumenti AI, e ogni traduzione è stata prodotta dall'AI. Se si riscontra qualcosa di errato nel codice o nelle traduzioni, o si ritiene che esista un approccio migliore, è possibile aprire una PR.

## Licenza

I contenuti derivati dai sorgenti di Zed (`catalog/`, `translations/`, `manifest/` e gli artefatti di rilascio) sono rilasciati sotto licenza [GPL-3.0](../../LICENSE). Il codice sorgente di `zed-i18n` e i glossari di traduzione (`prompts/translation/glossary/`) estratti dai [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) sono rilasciati sotto licenza [MIT](../../LICENSE-MIT). I contenuti dei language pack di VS Code sono di proprietà di Microsoft Corporation.
