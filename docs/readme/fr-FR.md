<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Traduisez facilement l'éditeur Zed dans votre propre langue.</strong></p>

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

Zed-i18n est une boîte à outils qui extrait les chaînes de l'interface utilisateur des versions publiées de l'éditeur [Zed](https://zed.dev) et applique des traductions pour produire des versions multilingues.

> Zed-i18n est un projet communautaire indépendant, sans aucun lien avec Zed Industries ; il ne bénéficie d'aucun parrainage ni d'aucune certification officielle.

## Langues prises en charge

Des traductions pour 13 langues sont actuellement incluses dans le répertoire `translations/`. Toutes les traductions actuelles sont générées par IA ; les contributions de locuteurs natifs sont les bienvenues.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Téléchargements

Vous pouvez récupérer les derniers binaires depuis la page [Releases](https://github.com/LI-NA/zed-i18n/releases).

Pour en savoir plus sur le processus de compilation des dernières versions, consultez la section [Versions publiées](#versions-publiées) ; pour compiler vous-même, reportez-vous à [Compilation manuelle](#compilation-manuelle).

### Fiabilité des compilations

- Les binaires publiés ne sont pas signés ; des avertissements de sécurité peuvent apparaître sous Windows ou macOS.
- Toutes les versions sont compilées via `.github/workflows/i18n-release.yml`, et les journaux de compilation sont consultables dans l'onglet [Actions](https://github.com/LI-NA/zed-i18n/actions).
- Les sources de Zed sont épinglées par le SHA `zed_commit` dans `config/project.toml`, ce qui permet de vérifier exactement quelle source a été utilisée pour la compilation.

Évitez les compilations provenant de sources non fiables et, dans la mesure du possible, compilez vous-même pour réduire les préoccupations de sécurité.

### Ouverture sous macOS

Pour les fichiers de confiance, effectuez un clic droit dans le Finder puis sélectionnez `Ouvrir`, ou exécutez la commande `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` dans le Terminal pour supprimer l'attribut de quarantaine.

## Installation via un gestionnaire de paquets

Sous macOS, vous pouvez l'installer via un cask Homebrew.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

La langue correspondant à celle de votre système est installée automatiquement ; à défaut de correspondance, `ko-KR` est utilisé. Pour choisir une langue précise, utilisez l'option `--language` de Homebrew.

```bash
brew install --cask zed-i18n --language=fr-FR
```

Sous Windows, ajoutez le bucket Scoop puis installez la langue de votre choix.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-fr-FR
```

Les installations via Scoop ne peuvent pas utiliser la mise à jour automatique intégrée de Zed ; mettez-les à jour avec `scoop update`.

## Configuration de l'environnement de développement

Python 3.12 ou version ultérieure et [`uv`](https://docs.astral.sh/uv/) sont requis.

```powershell
uv sync
```

Toutes les commandes s'exécutent sous la forme `uv run zed-i18n <command>`.

## Utilisation

La version cible de Zed est définie dans `config/project.toml`. La commande `fetch-zed` prépare à la fois le dépôt utilisé pour l'application des traductions et la compilation, ainsi que le dépôt propre utilisé pour l'extraction des chaînes et la révision.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.7.2-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.7.2-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.7.2-clean-extract
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

1. Rédigez le guide de style de traduction dans `prompts/translation/<language>.md` et le glossaire organisé dans `prompts/translation/glossary/<lang>.md`.
2. Générez les lots avec `prepare-translation`.
3. Fusionnez les résultats JSON produits par l'IA avec `merge-translation`.
4. Validez le résultat avec `validate`.

Les directives propres à chaque langue se trouvent dans `prompts/translation/<language>.md`. Si le fichier est absent, `prompts/translation/TEMPLATE.md` est utilisé par défaut.

## Compilation manuelle

Sous Windows, [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), le Windows SDK, CMake et [Rust](https://rustup.rs/) sont nécessaires. Il est conseillé de partager le cache de compilation entre les versions via `.cache/zed/target`. Voici un exemple de compilation :

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.7.2
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Versions publiées

Les versions publiées sont générées automatiquement via GitHub Actions, définies dans `.github/workflows/i18n-release.yml`. Les sources de Zed sont épinglées à la balise `zed_version` et au SHA `zed_commit` dans `config/project.toml`.

Le processus de publication applique `config/distribution.toml`, en plus des traductions propres à chaque langue, pour patcher l'identifiant zed-i18n, les informations About et le chemin de mise à jour automatique. Cela redirige le chemin de mise à jour automatique vers `zed-i18n`.

> **Remarque :** les compilations Zed-i18n modifient le point de terminaison de mise à jour automatique en remplaçant le serveur officiel de Zed par le fichier `manifest.json` des publications de ce dépôt. Désactivez la mise à jour automatique dans les paramètres si vous le préférez.

### Télémétrie

Zed-i18n ne modifie pas le comportement de télémétrie. Avec les paramètres par défaut, des métriques d'utilisation anonymes et des rapports d'incident peuvent être envoyés aux serveurs de Zed Industries. Pour désactiver la télémétrie, définissez `telemetry.metrics` et `telemetry.diagnostics` sur `false` dans les paramètres de Zed.

## Limitations connues

La plupart des chaînes de l'interface — menus, boutons, infobulles, paramètres, descriptions d'actions — sont gérées par substitution directe. Cependant, certains noms d'actions générés dynamiquement à l'exécution dans la palette de commandes ou l'Éditeur de raccourcis nécessitent un correctif séparé et ne sont pas encore pris en charge.

Pour ces parties non traduites, les contributions sur la manière d'appliquer des correctifs de façon fiable entre les versions de Zed sont les bienvenues.

## Sur l'utilisation de l'IA

La majeure partie du code de ce projet a été écrite avec l'aide d'outils d'IA, et chaque traduction a été produite par IA. Les résultats de traduction n'ont pas été directement vérifiés par un humain, des erreurs de traduction et des problèmes de branding restent donc possibles. Si vous remarquez un problème de traduction dans ce document ou ailleurs, ou si vous pensez qu'une meilleure traduction est possible, n'hésitez pas à ouvrir une issue ou une PR.

### Processus de traduction

Toutes les traductions ont suivi le processus décrit dans [Traduction par IA](#traduction-par-ia).

1. `extract` extrait les chaînes d'interface candidates des sources de Zed. Les résultats sont enregistrés dans `catalog/en-US.json` et `manifest/ui-strings.json`.
2. `audit-candidates` examine quelles chaînes ont été capturées par les règles d'extraction par rapport à celles qui ont été omises, ce qui permet de gérer la liste réelle des cibles de traduction (`accepted`).
3. `prepare-translation` génère des lots propres à chaque langue, en y incluant le guide de style, le glossaire et, lorsqu'elles sont disponibles, les références des packs de langue VS Code.
4. Un modèle d'IA rédige le JSON résultat lot par lot.
5. `merge-translation` fusionne les résultats, et `validate` vérifie les entrées manquantes ou superflues, les placeholders et la cohérence des tokens protégés.

Les traductions actuellement enregistrées ont suivi ce processus pour chaque langue avec deux modèles — `Sonnet 4.6` et `GPT-5.5` — chacun produisant indépendamment une traduction complète qui a été revérifiée. Les deux traductions finalisées ont ensuite été revérifiées et fusionnées en un résultat final via `Opus 4.6`.

Pour plus de détails sur le processus de traduction par IA, consultez les fichiers du répertoire `prompts\commands`.

## Licence

Le contenu dérivé des sources de Zed (`catalog/`, `translations/`, `manifest/`, les artefacts de publication, etc.) est distribué sous licence [GPL-3.0](../../LICENSE). Ce projet distribue des compilations modifiées de Zed. Le code source de `zed-i18n` et le matériel référencé depuis les [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) sont distribués sous licence [MIT](../../LICENSE-MIT).

Zed et le logo Zed sont la propriété de Zed Industries. Le contenu de VS Code et des packs de langue VS Code est protégé par le droit d'auteur de Microsoft Corporation.
