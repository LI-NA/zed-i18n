<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Переводите редактор Zed на свой язык без лишних усилий.</strong></p>

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
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    Русский ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Введение

Zed-i18n — это инструмент, который извлекает строки пользовательского интерфейса из релизной версии редактора [Zed](https://zed.dev) и применяет переводы для создания многоязычных сборок.

## Поддерживаемые языки

В настоящее время в директории `translations/` представлены переводы для 13 языков.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Загрузка

Последние сборки можно скачать в разделе [Releases](https://github.com/LI-NA/zed-i18n/releases). Если вы хотите собрать проект вручную, следуйте инструкциям ниже.

Файлы релиза сейчас не подписаны кодом. Если macOS блокирует приложение, используйте обход только для файлов, которым доверяете: в Finder нажмите правой кнопкой и выберите `Открыть`, либо удалите атрибут карантина командой `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Установка

Требуется Python 3.12 или новее и [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Все команды запускаются в формате `uv run zed-i18n <command>`.

## Использование

Целевая версия Zed задаётся в `config/project.toml`. Команда `fetch-zed` подготавливает как рабочую копию для применения переводов и сборки, так и чистую копию для извлечения и проверки строк.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.2.6-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract` сканирует Rust-исходники Zed в поисках кандидатов на строки пользовательского интерфейса и записывает результат в `catalog/en-US.json` и `manifest/ui-strings.json`. Результаты переводов хранятся в `translations/<language>.json`.

Вновь обнаруженные строки появляются в `manifest/ui-strings.json` со статусом `needs_review`. Меняйте на `accepted` и переводите только те строки, которые действительно отображаются в пользовательском интерфейсе.

## Перевод с помощью ИИ

Для выполнения переводов с использованием ИИ следуйте инструкции в `prompts/commands/translation-start.md`. Для сравнения и слияния результатов нескольких моделей используйте `prompts/commands/translation-review.md`.

Если нужно перевести только новые ключи, не затрагивая существующие переводы, обратитесь к файлам с суффиксом `new-keys`.

Чтобы включить в пакеты справочные материалы по переводам VS Code, перед запуском `prepare-translation` склонируйте репозитории ниже. Пакеты перевода формируются в штатном режиме и без них.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

При добавлении нового языка:

1. Напишите руководство по стилю и глоссарий в `prompts/translation/<language>.md`.
2. Сгенерируйте пакеты с помощью `prepare-translation`.
3. Объедините результаты, полученные от ИИ, командой `merge-translation`.
4. Проверьте результат с помощью `validate`.

Руководства по конкретным языкам находятся в `prompts/translation/<language>.md`. Если файл отсутствует, по умолчанию используется `prompts/translation/TEMPLATE.md`.

## Ручная сборка

В Windows потребуются [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake и [Rust](https://rustup.rs/). Рекомендуется использовать `.cache/zed/target` как общий кэш сборки для разных версий. Пример сборки:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.2.6
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Релизные сборки

Релизные сборки запускаются автоматически через GitHub Actions и описаны в `.github/workflows/i18n-release.yml`. Оригинальный Zed берётся из версии, зафиксированной тегом `zed_version` и SHA `zed_commit` в `config/project.toml`.

Рабочий процесс релиза применяет `config/distribution.toml`, чтобы изменить идентификатор zed-i18n, информацию About и путь автоматического обновления. В результате путь автоматического обновления меняется на `zed-i18n`.

## Известные ограничения

Большинство строк пользовательского интерфейса — меню, кнопки, всплывающие подсказки, параметры, описания действий — заменяются напрямую. Однако некоторые имена действий, которые формируются динамически во время выполнения в Палитре команд или Редакторе раскладки клавиш, требуют отдельного патча и пока не охвачены.

Если вам известен способ надёжно применять исправления между версиями Zed — вклад в проект будет очень кстати.

## Об использовании ИИ

Большая часть кода в этом проекте написана с помощью ИИ-инструментов, и все переводы также выполнены ИИ. Если вы заметили что-то некорректное в коде или переводах, или считаете, что какой-то подход можно улучшить — открывайте PR, будем рады.

## Лицензия

Содержимое, производное от исходников Zed (`catalog/`, `translations/`, `manifest/` и артефакты релизов), распространяется по лицензии [GPL-3.0](../../LICENSE). Собственный код `zed-i18n` и глоссарии переводов (`prompts/translation/glossary/`), извлечённые из [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc), распространяются по лицензии [MIT](../../LICENSE-MIT). Авторские права на содержимое языковых пакетов VS Code принадлежат Microsoft Corporation.
