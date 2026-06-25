<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Traduci l'editor Zed nella tua lingua con facilità.</strong></p>

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

Zed-i18n è uno strumento che estrae le stringhe dell'interfaccia utente dalle versioni rilasciate dell'editor [Zed](https://zed.dev) e applica le traduzioni per produrre build multilingue.

> Zed-i18n è un progetto della community non affiliato con Zed Industries; non è ufficialmente sponsorizzato né approvato.

## Lingue supportate

Le traduzioni per 13 lingue sono attualmente disponibili nella cartella `translations/`. Tutte le traduzioni attuali sono generate dall'AI; i contributi dei madrelingua sono benvenuti.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Download

È possibile scaricare i binari più recenti dalla pagina [Releases](https://github.com/LI-NA/zed-i18n/releases).

Per maggiori dettagli sul processo di build più recente, consultare [Build di rilascio](#build-di-rilascio); per compilare autonomamente, fare riferimento a [Build manuale](#build-manuale).

### Affidabilità della build

- I binari rilasciati NON sono firmati digitalmente; su Windows o macOS possono comparire avvisi di sicurezza.
- Tutte le release vengono compilate tramite `.github/workflows/i18n-release.yml`; i log di build sono consultabili nella scheda [Actions](https://github.com/LI-NA/zed-i18n/actions).
- I sorgenti originali di Zed sono fissati tramite il SHA `zed_commit` in `config/project.toml`, in modo da poter verificare con precisione quale codice sorgente sia stato utilizzato per la build.

Evitare le build provenienti da fonti non attendibili; quando possibile, compilare in autonomia per ridurre i rischi di sicurezza.

### Apertura su macOS

Per i file ritenuti attendibili, fare clic destro nel Finder e selezionare `Apri`, oppure rimuovere l'attributo di quarantena tramite Terminale con il comando `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Installazione tramite gestore di pacchetti

Su macOS è possibile installarlo tramite un cask di Homebrew.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

Viene installata automaticamente la lingua corrispondente a quella del sistema; in assenza di corrispondenza viene usata `ko-KR`. Per scegliere una lingua specifica, usare l'opzione `--language` di Homebrew.

```bash
brew install --cask zed-i18n --language=it-IT
```

Su Windows, aggiungere il bucket di Scoop e installare la lingua desiderata.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-it-IT
```

Le installazioni tramite Scoop non possono usare l'aggiornamento automatico integrato di Zed; vanno aggiornate con `scoop update`.

## Configurazione dell'ambiente di sviluppo

Richiede Python 3.12 o versione successiva e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Tutti i comandi vengono eseguiti tramite `uv run zed-i18n <command>`.

## Utilizzo

La versione di Zed di destinazione è impostata in `config/project.toml`. Il comando `fetch-zed` prepara sia il checkout per `apply` e build sia il checkout pulito utilizzato per l'estrazione delle stringhe e la revisione.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.8.2-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.8.2-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.8.2-clean-extract
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

1. Scrivere la guida di stile per la traduzione in `prompts/translation/<language>.md` e il glossario curato in `prompts/translation/glossary/<lang>.md`.
2. Generare i batch con `prepare-translation`.
3. Unire i risultati JSON prodotti dall'AI tramite `merge-translation`.
4. Validare il risultato con `validate`.

Le linee guida per ciascuna lingua si trovano in `prompts/translation/<language>.md`. Se il file è assente, viene utilizzato `prompts/translation/TEMPLATE.md` come predefinito.

## Build manuale

Su Windows sono necessari [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), il Windows SDK, CMake e [Rust](https://rustup.rs/). È consigliabile condividere la cache di build tra le versioni tramite `.cache/zed/target`. Un esempio di build è il seguente:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.8.2
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Build di rilascio

Le build di rilascio vengono eseguite automaticamente tramite GitHub Actions; il workflow è definito in `.github/workflows/i18n-release.yml`. I sorgenti di Zed sono fissati al tag `zed_version` e al SHA `zed_commit` in `config/project.toml`.

Il workflow di rilascio applica `config/distribution.toml`, insieme alle traduzioni di ciascuna lingua, per aggiornare l'identificativo zed-i18n, le informazioni della schermata About e il percorso di aggiornamento automatico. In questo modo il percorso di aggiornamento automatico viene reindirizzato a `zed-i18n`.

> **Nota:** le build di Zed-i18n modificano l'endpoint di aggiornamento automatico, sostituendo il server ufficiale di Zed con il file `manifest.json` presente nelle release di questo repository. Per chi preferisce, è possibile disattivare l'aggiornamento automatico nelle impostazioni.

### Telemetria

Zed-i18n non modifica il comportamento della telemetria. Con le impostazioni predefinite, metriche d'uso anonime e segnalazioni di crash possono essere inviate ai server di Zed Industries. Per disattivare la telemetria, impostare `telemetry.metrics` e `telemetry.diagnostics` su `false` nelle impostazioni di Zed.

## Limitazioni note

La maggior parte delle stringhe dell'interfaccia utente — menu, pulsanti, tooltip, impostazioni, descrizioni delle azioni — viene gestita tramite sostituzione diretta. Tuttavia, alcuni nomi di azioni generati dinamicamente a runtime nel riquadro comandi o nell'Editor mappa tasti richiedono una patch separata e non sono ancora coperti.

Per queste parti non tradotte, sono benvenuti i contributi su come applicare patch in modo affidabile tra le versioni di Zed.

## Sull'utilizzo dell'AI

La maggior parte del codice di questo progetto è stata scritta con l'aiuto di strumenti AI, e ogni traduzione è stata prodotta dall'AI. Poiché i risultati delle traduzioni non sono stati revisionati direttamente da persone, potrebbero esserci traduzioni errate o problemi di branding. Se si riscontra un problema di traduzione, anche in questo documento, o si ritiene che sia possibile una traduzione migliore, è possibile aprire una issue o una PR in qualsiasi momento.

### Processo di traduzione

Tutte le traduzioni sono state realizzate seguendo il processo descritto in [Traduzione tramite AI](#traduzione-tramite-ai).

1. `extract` estrae le stringhe candidate dell'interfaccia utente dai sorgenti di Zed. I risultati vengono salvati in `catalog/en-US.json` e `manifest/ui-strings.json`.
2. `audit-candidates` verifica quali stringhe sono state catturate dalle regole di estrazione e quali sono state escluse, ed è utilizzato per gestire l'elenco effettivo dei target di traduzione (`accepted`).
3. `prepare-translation` genera i batch per ciascuna lingua, includendo guida di stile, glossario e, ove disponibili, i riferimenti dei language pack di VS Code.
4. Un modello AI redige il JSON con il risultato della traduzione un batch alla volta.
5. `merge-translation` unisce i risultati, e `validate` verifica voci mancanti o aggiuntive, placeholder e coerenza dei token protetti.

Le traduzioni attualmente registrate sono state realizzate seguendo questo processo per ogni lingua usando due modelli — `Sonnet 4.6` e `GPT-5.5` — ciascuno dei quali ha prodotto una traduzione completa e indipendente che è stata poi sottoposta a una nuova revisione. Le due traduzioni finite sono state quindi revisionate nuovamente e unite nell'output finale tramite `Opus 4.6`.

Per maggiori dettagli sul processo di traduzione tramite AI, consultare i file presenti in `prompts\commands`.

## Licenza

I contenuti derivati dai sorgenti di Zed (`catalog/`, `translations/`, `manifest/`, gli artefatti di rilascio, ecc.) sono rilasciati sotto licenza [GPL-3.0](../../LICENSE). Questo progetto distribuisce build modificate di Zed. Il codice sorgente di `zed-i18n` e il materiale di riferimento dai [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) sono rilasciati sotto licenza [MIT](../../LICENSE-MIT).

Zed e il logo Zed sono di proprietà di Zed Industries. I contenuti di VS Code e dei language pack di VS Code sono di proprietà di Microsoft Corporation.
