<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Traduce el editor Zed a tu propio idioma fácilmente.</strong></p>

  [![Zed v1.2.3](https://img.shields.io/badge/Zed-v1.2.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.2.3)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue)](../../LICENSE)
  [![MIT components](https://img.shields.io/badge/MIT-components-yellow)](../../LICENSE-MIT)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    Español ·
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

## Introducción

zed-i18n es una herramienta que extrae cadenas de la interfaz de usuario de las versiones publicadas del editor [Zed](https://zed.dev) y aplica traducciones para producir compilaciones multilingües.

## Idiomas admitidos

Actualmente se incluyen traducciones para 13 idiomas en `translations/`.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Descargas

Puedes obtener las compilaciones más recientes en [Releases](https://github.com/LI-NA/zed-i18n/releases). Si prefieres compilar el proyecto tú mismo, sigue los pasos que se indican a continuación.

Los archivos distribuidos todavía no tienen firma de código. Si macOS bloquea la app, hazlo solo con archivos de confianza: ábrela desde Finder con clic derecho y `Abrir`, o elimina el atributo de cuarentena con `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Instalación

Requiere Python 3.12 o posterior y [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Todos los comandos se ejecutan como `uv run zed-i18n <command>`.

## Uso

La versión objetivo de Zed se establece en `config/project.toml`. `fetch-zed` prepara tanto el checkout para aplicar traducciones y compilar como el checkout limpio que se utiliza para extraer y revisar cadenas.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.3-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` analiza el código fuente en Rust de Zed en busca de cadenas de interfaz de usuario candidatas y las escribe en `catalog/en-US.json` y `manifest/ui-strings.json`. Los resultados de traducción se almacenan en `translations/<language>.json`.

Las cadenas recién descubiertas aparecen en `manifest/ui-strings.json` con el estado `needs_review`. Solo las cadenas que se muestran realmente en la interfaz deben marcarse como `accepted` y traducirse.

## Traducción con IA

Para realizar traducciones asistidas por IA, consulta `prompts/commands/translation-start.md`. Para comparar y fusionar resultados de varios modelos, utiliza `prompts/commands/translation-review.md`.

Si deseas traducir únicamente las claves recién añadidas sin modificar las traducciones existentes, consulta los archivos con el sufijo `new-keys`.

Para incluir referencias de traducción de VS Code en los lotes, prepara los repositorios siguientes antes de ejecutar `prepare-translation`. Los lotes se generan igualmente aunque falten.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Al añadir un nuevo idioma:

1. Escribe una guía de estilo y un glosario en `prompts/translation/<language>.md`.
2. Genera los lotes con `prepare-translation`.
3. Fusiona los resultados JSON producidos por la IA usando `merge-translation`.
4. Valida el resultado con `validate`.

Las directrices por idioma se encuentran en `prompts/translation/<language>.md`. Si el archivo no existe, se utiliza `prompts/translation/TEMPLATE.md` como plantilla predeterminada.

## Compilación manual

En Windows se necesitan [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), el Windows SDK, CMake y [Rust](https://rustup.rs/). Se recomienda compartir la caché de compilación entre versiones mediante `.cache/zed/target`. Un ejemplo de compilación sería el siguiente:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.3
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Compilaciones de lanzamiento

Las compilaciones de lanzamiento se ejecutan automáticamente a través de GitHub Actions y están definidas en `.github/workflows/i18n-release.yml`. El código fuente de Zed queda fijado por la etiqueta `zed_version` y el SHA `zed_commit` en `config/project.toml`.

El flujo de lanzamiento aplica `config/distribution.toml` para parchear el identificador de zed-i18n, la información de About y la ruta de actualización automática. Esto redirige la ruta de actualización automática a `zed-i18n`.

## Limitaciones conocidas

La mayoría de las cadenas de la interfaz de usuario —menús, botones, información sobre herramientas, configuración, descripciones de acciones— se gestionan mediante sustitución directa. Sin embargo, algunos nombres de acción que se generan dinámicamente en tiempo de ejecución en la paleta de comandos o el Editor de mapa de teclas requieren un parche adicional y aún no están cubiertos.

Si conoces alguna forma de aplicar parches de manera fiable entre versiones de Zed, las contribuciones son muy bienvenidas.

## Sobre el uso de IA

La mayor parte del código de este proyecto se ha escrito con la ayuda de herramientas de IA, y todas las traducciones han sido generadas por IA. Si detectas algo incorrecto en el código o en las traducciones, o crees que existe un enfoque mejor, no dudes en abrir una PR.

## Licencia

El contenido derivado del código fuente de Zed (`catalog/`, `translations/`, `manifest/` y los artefactos de lanzamiento) está bajo la licencia [GPL-3.0](../../LICENSE). El código propio de `zed-i18n` y los glosarios de traducción (`prompts/translation/glossary/`) extraídos de [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) están bajo la licencia [MIT](../../LICENSE-MIT). El contenido de los paquetes de idiomas de VS Code es propiedad de Microsoft Corporation.
