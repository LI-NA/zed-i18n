<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Traduza o editor Zed para o seu idioma com facilidade.</strong></p>

  [![Zed v1.4.4](https://img.shields.io/badge/Zed-v1.4.4-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.4.4)
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
    Português ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Introdução

Zed-i18n é uma ferramenta que extrai strings de interface das versões de lançamento do editor [Zed](https://zed.dev) e aplica traduções para gerar builds multilíngues.

> Zed-i18n é um projeto comunitário sem vínculo com a Zed Industries; não é oficialmente patrocinado nem endossado.

## Idiomas suportados

Atualmente, traduções para 13 idiomas estão disponíveis no diretório `translations/`. Todas as traduções atuais foram geradas por IA; contribuições de falantes nativos são bem-vindas.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Downloads

Os binários mais recentes estão disponíveis na página de [Releases](https://github.com/LI-NA/zed-i18n/releases).

Para mais detalhes sobre o processo de build mais recente, consulte [Builds de lançamento](#builds-de-lançamento). Se preferir compilar o projeto você mesmo, consulte [Compilação manual](#compilação-manual).

### Confiabilidade do build

- Os binários distribuídos não têm assinatura de código. Avisos de segurança podem aparecer no Windows ou no macOS.
- Todos os lançamentos são compilados via `.github/workflows/i18n-release.yml`, e os logs de build podem ser inspecionados na aba [Actions](https://github.com/LI-NA/zed-i18n/actions).
- O código-fonte original do Zed é fixado pelo SHA `zed_commit` em `config/project.toml`, de modo que é possível verificar exatamente qual fonte foi usada no build.

Evite usar builds de fontes não confiáveis; sempre que possível, compile você mesmo para reduzir preocupações de segurança.

### Abrindo no macOS

Apenas para arquivos em que você confia, clique com o botão direito no Finder e selecione `Abrir`, ou execute `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` no Terminal para remover o atributo de quarentena.

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
uv run zed-i18n extract --zed-root .cache/zed/v1.4.4-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.4.4-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.4.4-clean-extract
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
cd .cache\zed\v1.4.4
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Builds de lançamento

Os builds de lançamento são executados automaticamente por meio do GitHub Actions, conforme definido em `.github/workflows/i18n-release.yml`. O código-fonte do Zed é fixado pela tag `zed_version` e pelo SHA `zed_commit` em `config/project.toml`.

O fluxo de lançamento aplica `config/distribution.toml` junto com as traduções por idioma para ajustar o identificador do zed-i18n, as informações de About e o caminho de atualização automática. Isso redireciona o caminho de atualização automática para `zed-i18n`.

> **Nota:** Os builds do Zed-i18n alteram o endpoint de atualização automática do servidor oficial do Zed para o `manifest.json` localizado nos releases deste repositório. Se preferir, desative a atualização automática nas configurações.

### Telemetria

O Zed-i18n não altera o comportamento da telemetria. Com as configurações padrão, métricas anônimas de uso e relatórios de falhas podem ser enviados aos servidores da Zed Industries. Para desativar a telemetria, defina `telemetry.metrics` e `telemetry.diagnostics` como `false` nas configurações do Zed.

## Limitações conhecidas

A maioria das strings de interface — menus, botões, tooltips, configurações, descrições de ações — é tratada por substituição direta. No entanto, alguns nomes de ações gerados dinamicamente em tempo de execução na paleta de comandos ou no Editor de mapa de teclas exigem um patch separado e ainda não são cobertos.

Para essas partes não traduzidas, contribuições sobre como aplicar patches de maneira confiável entre versões do Zed são muito bem-vindas.

## Sobre o uso de IA

Grande parte do código deste projeto foi escrita com o auxílio de ferramentas de IA, e todas as traduções foram produzidas por IA. Como os resultados das traduções não foram revisados diretamente por humanos, podem ocorrer traduções incorretas ou problemas de branding. Se você encontrar algum problema de tradução — inclusive neste próprio documento — ou achar que uma tradução melhor é possível, sinta-se à vontade para abrir uma issue ou PR.

### Processo de tradução

Todas as traduções passaram pelo processo descrito em [Tradução com IA](#tradução-com-ia).

1. `extract` extrai os candidatos a strings de interface do código-fonte do Zed. Os resultados são salvos em `catalog/en-US.json` e `manifest/ui-strings.json`.
2. `audit-candidates` revisa quais strings foram capturadas pelas regras de extração e quais foram ignoradas, sendo usado para gerenciar a lista real de alvos de tradução (`accepted`).
3. `prepare-translation` gera lotes por idioma, agrupando guia de estilo, glossário e, quando disponíveis, referências dos pacotes de idiomas do VS Code.
4. Um modelo de IA escreve o JSON com o resultado da tradução lote por lote.
5. `merge-translation` mescla os resultados, e `validate` verifica entradas ausentes ou em excesso, placeholders e a consistência dos tokens protegidos.

As traduções atualmente registradas passaram por esse processo para cada idioma usando dois modelos — `Sonnet 4.6` e `GPT-5.5` — cada um produzindo uma tradução completa e independente, posteriormente revisada. As duas traduções finalizadas foram então revisadas novamente e mescladas no resultado final por meio do `Opus 4.6`.

Para mais detalhes sobre o processo de tradução com IA, consulte os arquivos em `prompts\commands`.

## Licença

O conteúdo derivado do código-fonte do Zed (`catalog/`, `translations/`, `manifest/`, artefatos de lançamento etc.) está licenciado sob a [GPL-3.0](../../LICENSE). Este projeto distribui builds modificados do Zed. O código-fonte do `zed-i18n` e os glossários de tradução (`prompts/translation/glossary/`) extraídos dos [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) estão licenciados sob a [MIT](../../LICENSE-MIT).

Zed e o logotipo do Zed são propriedade da Zed Industries. O conteúdo do VS Code e dos pacotes de idiomas do VS Code é protegido por direitos autorais da Microsoft Corporation.
