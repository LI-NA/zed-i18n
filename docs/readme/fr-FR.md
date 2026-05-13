<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Traduisez facilement l'éditeur Zed dans votre propre langue.</strong></p>

  [![Zed v1.1.8](https://img.shields.io/badge/Zed-v1.1.8-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.1.8)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue)](../../LICENSE)
  [![MIT components](https://img.shields.io/badge/MIT-components-yellow)](../../LICENSE-MIT)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    <a href="es-ES.md">Español</a> ·
    Français ·
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

## Introduction

zed-i18n est une boîte à outils qui extrait les chaînes de l'interface utilisateur des versions publiées de l'éditeur [Zed](https://zed.dev) et applique des traductions pour produire des versions multilingues.

## Langues prises en charge

Des traductions pour 13 langues sont actuellement incluses dans le répertoire `translations/`.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Téléchargements

Vous pouvez récupérer les derniers binaires depuis la page [Releases](https://github.com/LI-NA/zed-i18n/releases). Si vous préférez compiler le projet vous-même, suivez les étapes ci-dessous.

Les fichiers distribués ne disposent pas encore de signature de code. Si macOS bloque l'application, ouvrez uniquement les fichiers de confiance depuis le Finder avec clic droit puis `Ouvrir`, ou supprimez l'attribut de quarantaine avec `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Installation

Python 3.12 ou version ultérieure et [`uv`](https://docs.astral.sh/uv/) sont requis.

```powershell
uv sync
```

Toutes les commandes s'exécutent sous la forme `uv run zed-i18n <command>`.

## Utilisation

La version cible de Zed est définie dans `config/project.toml`. La commande `fetch-zed` prépare à la fois le dépôt utilisé pour l'application des traductions et la compilation, ainsi que le dépôt propre utilisé pour l'extraction des chaînes et la révision.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

La commande `extract` analyse les sources Rust de Zed à la recherche de chaînes d'interface candidates et les écrit dans `catalog/en-US.json` et `manifest/ui-strings.json`. Les traductions sont stockées dans `translations/<language>.json`.

Les chaînes nouvellement découvertes apparaissent dans `manifest/ui-strings.json` avec le statut `needs_review`. Seules les chaînes effectivement affichées dans l'interface doivent être passées à `accepted` puis traduites.

## Traduction par IA

Pour les traductions assistées par IA, suivez le fichier `prompts/commands/translation-start.md`. Pour comparer et fusionner les résultats de plusieurs modèles, utilisez `prompts/commands/translation-review.md`.

Si vous souhaitez ne traduire que les clés nouvellement ajoutées sans modifier les traductions existantes, référez-vous aux fichiers dont le nom se termine par `new-keys`.

Pour inclure des références de traduction VS Code dans les lots, clonez les dépôts ci-dessous avant d'exécuter `prepare-translation`. Les lots sont tout de même générés normalement s'ils sont absents.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Pour ajouter une nouvelle langue :

1. Rédigez un guide de style et un glossaire dans `prompts/translation/<language>.md`.
2. Générez les lots avec `prepare-translation`.
3. Fusionnez les résultats JSON produits par l'IA avec `merge-translation`.
4. Validez le résultat avec `validate`.

Les directives propres à chaque langue se trouvent dans `prompts/translation/<language>.md`. Si le fichier est absent, `prompts/translation/TEMPLATE.md` est utilisé par défaut.

## Compilation manuelle

Sous Windows, [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), le Windows SDK, CMake et [Rust](https://rustup.rs/) sont nécessaires. Il est conseillé de partager le cache de compilation entre les versions via `.cache/zed/target`. Voici un exemple de compilation :

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.1.8
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Versions publiées

Les versions publiées sont générées automatiquement via GitHub Actions, définies dans `.github/workflows/i18n-release.yml`. Les sources de Zed sont épinglées à la balise `zed_version` et au SHA `zed_commit` dans `config/project.toml`.

Le processus de publication applique `config/distribution.toml` pour patcher l'identifiant zed-i18n, les informations About et le chemin de mise à jour automatique. Cela redirige le chemin de mise à jour automatique vers `zed-i18n`.

## Limitations connues

La plupart des chaînes de l'interface — menus, boutons, infobulles, paramètres, descriptions d'actions — sont gérées par substitution directe. Cependant, certains noms d'actions générés dynamiquement à l'exécution dans la palette de commandes ou l'Éditeur de raccourcis nécessitent un correctif séparé et ne sont pas encore pris en charge.

Si vous connaissez un moyen d'appliquer des correctifs de façon fiable entre les versions de Zed, les contributions sont les bienvenues.

## Sur l'utilisation de l'IA

La majeure partie du code de ce projet a été écrite avec l'aide d'outils d'IA, et chaque traduction a été produite par IA. Si vous remarquez quelque chose d'incorrect dans le code ou les traductions, ou si vous pensez qu'une meilleure approche existe, n'hésitez pas à ouvrir une PR.

## Licence

Le contenu dérivé des sources de Zed (`catalog/`, `translations/`, `manifest/` et les artefacts de publication) est distribué sous licence [GPL-3.0](../../LICENSE). Le code source de `zed-i18n` et les glossaires de traduction (`prompts/translation/glossary/`) extraits des [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) sont distribués sous licence [MIT](../../LICENSE-MIT). Le contenu des packs de langue VS Code est protégé par le droit d'auteur de Microsoft Corporation.
