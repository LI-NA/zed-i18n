<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Traduza o editor Zed para o seu idioma com facilidade.</strong></p>

  [![Zed v1.1.8](https://img.shields.io/badge/Zed-v1.1.8-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.1.8)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue)](../../LICENSE)
  [![MIT components](https://img.shields.io/badge/MIT-components-yellow)](../../LICENSE-MIT)

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
    Português ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Introdução

zed-i18n é uma ferramenta que extrai strings de interface das versões de lançamento do editor [Zed](https://zed.dev) e aplica traduções para gerar builds multilíngues.

## Idiomas suportados

Atualmente, traduções para 13 idiomas estão disponíveis no diretório `translations/`.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Downloads

Os binários mais recentes estão disponíveis na página de [Releases](https://github.com/LI-NA/zed-i18n/releases). Se preferir compilar o projeto você mesmo, siga os passos abaixo.

Os arquivos distribuídos ainda não têm assinatura de código. Se o macOS bloquear o app, faça isso apenas com arquivos em que você confia: abra pelo Finder com botão direito e `Abrir`, ou remova o atributo de quarentena com `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app`.

## Instalação

Requer Python 3.12 ou superior e [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Todos os comandos são executados como `uv run zed-i18n <command>`.

## Uso

A versão alvo do Zed é definida em `config/project.toml`. O comando `fetch-zed` prepara tanto o checkout usado para aplicação/compilação quanto o checkout limpo utilizado para extração de strings e revisão.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

O comando `extract` percorre o código-fonte Rust do Zed em busca de candidatos a strings de interface e os grava em `catalog/en-US.json` e `manifest/ui-strings.json`. Os resultados das traduções são armazenados em `translations/<language>.json`.

As strings recém-descobertas são adicionadas a `manifest/ui-strings.json` com o status `needs_review`. Somente as strings que são de fato exibidas na interface devem ter o status alterado para `accepted` e, em seguida, traduzidas.

## Tradução com IA

Para executar traduções com auxílio de IA, siga o arquivo `prompts/commands/translation-start.md`. Para comparar e mesclar resultados de múltiplos modelos, use `prompts/commands/translation-review.md`.

Se quiser traduzir apenas as chaves recém-adicionadas sem alterar as traduções existentes, consulte os arquivos com o sufixo `new-keys`.

Para incluir referências de tradução do VS Code nos lotes, clone os repositórios abaixo antes de executar `prepare-translation`. Os lotes ainda são gerados normalmente caso esses repositórios estejam ausentes.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Ao adicionar um novo idioma:

1. Escreva um guia de estilo e glossário em `prompts/translation/<language>.md`.
2. Gere os lotes com `prepare-translation`.
3. Mescle os resultados JSON produzidos pela IA usando `merge-translation`.
4. Valide o resultado com `validate`.

As diretrizes por idioma ficam em `prompts/translation/<language>.md`. Se o arquivo não existir, `prompts/translation/TEMPLATE.md` é usado como padrão.

## Compilação manual

No Windows, você precisará do [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), do Windows SDK, do CMake e do [Rust](https://rustup.rs/). É recomendável compartilhar o cache de compilação entre versões por meio de `.cache/zed/target`. Um exemplo de compilação:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.1.8
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Builds de lançamento

Os builds de lançamento são executados automaticamente por meio do GitHub Actions, conforme definido em `.github/workflows/i18n-release.yml`. O código-fonte do Zed é fixado pela tag `zed_version` e pelo SHA `zed_commit` em `config/project.toml`.

O fluxo de lançamento aplica `config/distribution.toml` para ajustar o identificador do zed-i18n, as informações de About e o caminho de atualização automática. Isso redireciona o caminho de atualização automática para `zed-i18n`.

## Limitações conhecidas

A maioria das strings de interface — menus, botões, tooltips, configurações, descrições de ações — é tratada por substituição direta. No entanto, alguns nomes de ações gerados dinamicamente em tempo de execução na paleta de comandos ou no Editor de mapa de teclas exigem um patch separado e ainda não são cobertos.

Se você conhecer uma forma de aplicar patches de maneira confiável entre versões do Zed, contribuições são muito bem-vindas.

## Sobre o uso de IA

Grande parte do código deste projeto foi escrita com o auxílio de ferramentas de IA, e todas as traduções foram produzidas por IA. Se você encontrar algo incorreto no código ou nas traduções, ou tiver uma abordagem melhor, sinta-se à vontade para abrir um PR.

## Licença

O conteúdo derivado do código-fonte do Zed (`catalog/`, `translations/`, `manifest/` e artefatos de lançamento) está licenciado sob a [GPL-3.0](../../LICENSE). O código-fonte do `zed-i18n` e os glossários de tradução (`prompts/translation/glossary/`) extraídos dos [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) estão licenciados sob a [MIT](../../LICENSE-MIT). O conteúdo dos pacotes de idiomas do VS Code é protegido por direitos autorais da Microsoft Corporation.
