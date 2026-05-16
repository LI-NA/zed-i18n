<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Snadno přeložte editor Zed do svého jazyka.</strong></p>

  [![Zed v1.2.6](https://img.shields.io/badge/Zed-v1.2.6-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.6)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Source: MIT](https://img.shields.io/badge/Source-MIT-brightgreen)](../../LICENSE-MIT)
  [![Release: GPL-3.0](https://img.shields.io/badge/Release-GPL--3.0-orange)](../../LICENSE)
  <br>
  [![Release build](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml/badge.svg)](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml)
  [![Latest release](https://img.shields.io/github/v/release/LI-NA/zed-i18n?include_prereleases&label=latest)](https://github.com/LI-NA/zed-i18n/releases/latest)
  [![Downloads](https://img.shields.io/github/downloads/LI-NA/zed-i18n/total)](https://github.com/LI-NA/zed-i18n/releases)

  <p>
    Čeština ·
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
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Úvod

Zed-i18n je sada nástrojů, která extrahuje UI řetězce z vydaných verzí editoru [Zed](https://zed.dev) a aplikuje překlady, aby bylo možné vytvářet vícejazyčné buildy.

## Podporované jazyky

V adresáři `translations/` jsou aktuálně zahrnuty překlady pro 13 jazyků.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Stažení

Nejnovější binární soubory jsou k dispozici v sekci [Releases](https://github.com/LI-NA/zed-i18n/releases). Pokud dáváte přednost vlastnímu sestavení projektu, postupujte podle níže uvedených kroků.

Distribuované soubory zatím nejsou podepsané kódem. Pokud macOS aplikaci zablokuje, u souborů, kterým důvěřujete, ji otevřete ve Finderu přes pravé kliknutí a `Otevřít`, případně odstraňte karanténní atribut příkazem `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Instalace

Vyžaduje Python 3.12 nebo novější a [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Všechny příkazy se spouštějí jako `uv run zed-i18n <command>`.

## Použití

Cílová verze Zed je nastavena v `config/project.toml`. Příkaz `fetch-zed` připraví checkout pro aplikování překladů a sestavení i čistý checkout používaný pro extrakci a kontrolu řetězců.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

Příkaz `extract` prohledá zdrojové kódy Zed (Rust) a vyhledá kandidáty na UI řetězce, které zapíše do `catalog/en-US.json` a `manifest/ui-strings.json`. Výsledky překladů se ukládají do `translations/<language>.json`.

Nově nalezené řetězce jsou zapsány do `manifest/ui-strings.json` se stavem `needs_review`. Pouze řetězce, které se skutečně zobrazují v UI, by měly být přepnuty na `accepted` a poté přeloženy.

## Překlad pomocí AI

Při překladech řízených AI postupujte podle `prompts/commands/translation-start.md`. Chcete-li porovnat a sloučit výsledky z více modelů, použijte `prompts/commands/translation-review.md`.

Pokud chcete přeložit pouze nově přidané klíče a stávající překlady ponechat beze změny, přečtěte si soubory s příponou `new-keys`.

Chcete-li do překladových dávek zahrnout reference z překladů VS Code, naklonujte níže uvedená úložiště před spuštěním `prepare-translation`. Dávky se vytvoří normálně i bez nich.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Při přidávání nového jazyka:

1. Napište překladový styl a glosář do `prompts/translation/<language>.md`.
2. Vygenerujte dávky příkazem `prepare-translation`.
3. Výsledky JSON vytvořené AI slučte pomocí `merge-translation`.
4. Výsledek ověřte příkazem `validate`.

Pokyny pro jednotlivé jazyky jsou v `prompts/translation/<language>.md`. Pokud soubor neexistuje, použije se jako výchozí šablona `prompts/translation/TEMPLATE.md`.

## Ruční sestavení

Ve Windows jsou potřeba [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake a [Rust](https://rustup.rs/). Doporučuje se sdílet cache sestavení napříč verzemi prostřednictvím `.cache/zed/target`. Ukázkové sestavení vypadá takto:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Release buildy

Release buildy se vytvářejí automaticky přes GitHub Actions podle definice v `.github/workflows/i18n-release.yml`. Zdrojový kód Zed je připnutý na tag `zed_version` a SHA `zed_commit` v `config/project.toml`.

Workflow pro vydání aplikuje `config/distribution.toml`, aby upravil identifikátor zed-i18n, informace v dialogu About a cestu automatických aktualizací. Tím se cesta automatických aktualizací přepíše na `zed-i18n`.

## Známá omezení

Většina UI řetězců — nabídky, tlačítka, tooltipy, nastavení, popisky akcí — je zpracována přímým nahrazením. Některé názvy akcí generované dynamicky za běhu v Paletě příkazů nebo Editoru mapy kláves však vyžadují samostatný patch, a proto zatím nejsou pokryty.

Pokud znáte způsob, jak spolehlivě aplikovat patche napříč verzemi Zed, příspěvky jsou velmi vítány.

## Poznámka k použití AI

Většina kódu v tomto projektu byla napsána s pomocí AI nástrojů a každý překlad byl vytvořen AI. Pokud si všimnete čehokoli nesprávného v kódu nebo překladech, nebo si myslíte, že existuje lepší přístup, neváhejte otevřít PR.

## Licence

Obsah odvozený ze zdrojů Zed (`catalog/`, `translations/`, `manifest/` a artefakty vydání) je licencován pod [GPL-3.0](../../LICENSE). Zdrojový kód `zed-i18n` a překladové glosáře (`prompts/translation/glossary/`) extrahované z [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) jsou licencovány pod [MIT](../../LICENSE-MIT). Obsah jazykových balíčků VS Code je chráněn autorskými právy společnosti Microsoft Corporation.
