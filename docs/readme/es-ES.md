<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Traduce el editor Zed a tu propio idioma fácilmente.</strong></p>

  [![Zed v1.5.4](https://img.shields.io/badge/Zed-v1.5.4-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.5.4)
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

Zed-i18n es una herramienta que extrae cadenas de la interfaz de usuario de las versiones publicadas del editor [Zed](https://zed.dev) y aplica traducciones para producir compilaciones multilingües.

> Zed-i18n es un proyecto comunitario sin relación con Zed Industries; no cuenta con patrocinio ni respaldo oficial.

## Idiomas admitidos

Actualmente se incluyen traducciones para 13 idiomas en `translations/`. Todas las traducciones actuales han sido generadas por IA; las contribuciones de hablantes nativos son bienvenidas.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Descargas

Puedes obtener las compilaciones más recientes en [Releases](https://github.com/LI-NA/zed-i18n/releases). Encontrarás más detalles sobre el proceso de la última compilación en [Compilaciones de lanzamiento](#compilaciones-de-lanzamiento); si prefieres compilar el proyecto tú mismo, consulta [Compilación manual](#compilación-manual).

### Confianza en las compilaciones

- Los binarios publicados NO están firmados digitalmente; pueden aparecer advertencias de seguridad en Windows o macOS.
- Todas las versiones se generan a través de `.github/workflows/i18n-release.yml`; los registros de compilación pueden consultarse en la pestaña [Actions](https://github.com/LI-NA/zed-i18n/actions).
- El código fuente de Zed queda fijado por el SHA `zed_commit` en `config/project.toml`, por lo que es posible verificar la fuente exacta utilizada para la compilación.

Evita las compilaciones de fuentes no confiables; cuando sea posible, compila tú mismo para reducir las preocupaciones de seguridad.

### Apertura en macOS

Solo para archivos de confianza: en Finder, haz clic derecho y selecciona `Abrir`, o ejecuta `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` en el Terminal para eliminar el atributo de cuarentena.

## Instalación con gestor de paquetes

En macOS puedes instalarlo mediante un cask de Homebrew.

```bash
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

Esto instala automáticamente el idioma que coincide con el de tu sistema y, si no hay coincidencia, recurre a `ko-KR`. Para elegir un idioma concreto, usa la opción `--language` de Homebrew.

```bash
brew install --cask zed-i18n --language=es-ES
```

En Windows, añade el bucket de Scoop y luego instala el idioma que prefieras.

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n-es-ES
```

Las instalaciones con Scoop no pueden usar la actualización automática propia de Zed; actualízalas con `scoop update`.

## Configuración del entorno de desarrollo

Requiere Python 3.12 o posterior y [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Todos los comandos se ejecutan como `uv run zed-i18n <command>`.

## Uso

La versión objetivo de Zed se establece en `config/project.toml`. `fetch-zed` prepara tanto el checkout para aplicar traducciones y compilar como el checkout limpio que se utiliza para extraer y revisar cadenas.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.5.4-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.5.4-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.5.4-clean-extract
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
cd .cache\zed\v1.5.4
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Compilaciones de lanzamiento

Las compilaciones de lanzamiento se ejecutan automáticamente a través de GitHub Actions y están definidas en `.github/workflows/i18n-release.yml`. El código fuente de Zed queda fijado por la etiqueta `zed_version` y el SHA `zed_commit` en `config/project.toml`.

El flujo de lanzamiento aplica `config/distribution.toml` junto con las traducciones de cada idioma para parchear el identificador de zed-i18n, la información de About y la ruta de actualización automática. Esto redirige la ruta de actualización automática a `zed-i18n`.

> **Nota:** Las compilaciones de Zed-i18n cambian el destino de la actualización automática del servidor oficial de Zed al archivo `manifest.json` de las versiones de este repositorio. Si prefieres no usar la actualización automática, puedes desactivarla en la configuración.

### Telemetría

Zed-i18n no modifica el comportamiento de la telemetría. Con la configuración predeterminada, pueden enviarse métricas de uso anónimas e informes de fallos a los servidores de Zed Industries. Para desactivar la telemetría, establece `telemetry.metrics` y `telemetry.diagnostics` en `false` en la configuración de Zed.

## Limitaciones conocidas

La mayoría de las cadenas de la interfaz de usuario —menús, botones, información sobre herramientas, configuración, descripciones de acciones— se gestionan mediante sustitución directa. Sin embargo, algunos nombres de acción que se generan dinámicamente en tiempo de ejecución en la paleta de comandos o el Editor de mapa de teclas requieren un parche adicional y aún no están cubiertos.

Para estas partes sin traducir, son bienvenidas las contribuciones sobre cómo aplicar parches de manera fiable entre versiones de Zed.

## Sobre el uso de IA

La mayor parte del código de este proyecto se ha escrito con la ayuda de herramientas de IA, y todas las traducciones han sido generadas por IA. Los resultados de la traducción no han sido revisados directamente por personas, por lo que pueden existir traducciones incorrectas o problemas relacionados con la marca. Si detectas algún problema de traducción en este documento o en otras traducciones, o crees que puede haber una traducción mejor, no dudes en abrir una issue o una PR.

### Proceso de traducción

Todas las traducciones se han realizado siguiendo el proceso descrito en [Traducción con IA](#traducción-con-ia).

1. `extract` extrae las cadenas candidatas de la interfaz desde el código fuente de Zed. Los resultados se guardan en `catalog/en-US.json` y `manifest/ui-strings.json`.
2. `audit-candidates` revisa qué cadenas han recogido las reglas de extracción y cuáles se han omitido, lo que sirve para gestionar la lista real de cadenas a traducir (`accepted`).
3. `prepare-translation` genera los lotes por idioma, incluyendo la guía de estilo, el glosario y, cuando están disponibles, las referencias de los paquetes de idiomas de VS Code.
4. Un modelo de IA escribe el JSON con el resultado de la traducción lote a lote.
5. `merge-translation` fusiona los resultados, y `validate` comprueba si hay entradas faltantes o sobrantes, así como la coherencia de los marcadores de posición y de los tokens protegidos.

Las traducciones registradas actualmente han pasado por este proceso para todos los idiomas utilizando dos modelos —`Sonnet 4.6` y `GPT-5.5`—, cada uno de los cuales produjo una traducción completa e independiente que fue revisada de nuevo. Las dos traducciones finalizadas se revisaron una vez más y se fusionaron en el resultado final mediante `Opus 4.6`.

Para obtener más información sobre el proceso de traducción con IA, consulta los archivos en `prompts\commands`.

## Licencia

El contenido derivado del código fuente de Zed (`catalog/`, `translations/`, `manifest/`, los artefactos de lanzamiento, etc.) está bajo la licencia [GPL-3.0](../../LICENSE). Este proyecto distribuye compilaciones modificadas de Zed. El código propio de `zed-i18n` y los glosarios de traducción (`prompts/translation/glossary/`) extraídos de [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) están bajo la licencia [MIT](../../LICENSE-MIT).

Zed y el logotipo de Zed son propiedad de Zed Industries. El contenido de VS Code y de los paquetes de idiomas de VS Code es propiedad de Microsoft Corporation.
