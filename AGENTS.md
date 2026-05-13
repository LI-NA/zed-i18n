# AGENTS.md

## CLI Commands

All commands run via `uv run zed-i18n <command>`. Target Zed version is in `config/project.toml`.
Use the global `--root <path>` flag only when running from outside the repository root.
If `uv` cannot launch on Windows, fall back to `.\.venv\Scripts\python.exe -m tools.zed_i18n.cli <command>`.

| Command | Purpose |
|---|---|
| `fetch-zed` | Clone the Zed release configured in `config/project.toml` to `.cache/zed/<version>` and `.cache/zed/<version>-clean-extract` |
| `extract --zed-root <path>` | Parse Rust sources and write `catalog/en-US.json` + `manifest/ui-strings.json` |
| `audit-candidates --zed-root <path>` | Audit string candidates against extraction rules; report to `reports/` |
| `prepare-translation --language <lang>` | Generate translation batch prompts under `reports/translation/<lang>/` |
| `merge-translation --language <lang>` | Merge agent result JSONs into `translations/<lang>.json` |
| `validate --language <lang>` | Validate translations against manifest; on success cleans the workspace unless `--no-cleanup` is passed |
| `apply --language <lang>` | Patch translated strings into the Zed checkout |
| `generate-vscode-glossary --language <lang>` | Generate VS Code terminology references to `reports/vscode-glossary/` and `prompts/translation/glossary/` |

Key flags for `prepare-translation`: `--zed-root`, `--batch-size` (default 40), `--context-lines` (default 12), `--missing-only` (explicit default), `--all` (include already-translated strings), `--output-dir`, `--prompt`, `--vscode-loc-root`, `--vscode-source-root`, `--vscode-reference-count` (default 3).
Key flags for `validate`: `--no-cleanup` (preserve `reports/translation/<lang>` after successful validation).

Key flags for `merge-translation`: `--results-dir` (agent JSON results), `--output` (write to a custom path instead of `translations/<lang>.json`).

Key flags for `generate-vscode-glossary`: `--vscode-loc-root`, `--vscode-source-root`, `--prompt`, `--output`, `--prompt-glossary-output-dir`; `--language all` processes every non-pseudo VS Code locale.

## Pipeline Sequence

```
fetch-zed
  → extract  (on clean checkout)
  → audit-candidates  (on clean checkout)
  → prepare-translation
  → [AI agents write batch results]
  → merge-translation
  → validate
  → apply  (on build checkout, not the clean one)
```

## Zed Checkouts

- `.cache/zed/<version>-clean-extract` — for `extract`, `audit-candidates`, `prepare-translation` source context. Never apply translations to this checkout.
- `.cache/zed/<version>` — for `apply` and local builds.
- Do not delete `.cache/zed` or run `cargo clean` unless the user explicitly asks.
- When bumping the Zed version in `config/project.toml`, manually review the `distribution.py` patch targets against the fetched Zed checkout before release work.

## Translation Workflow

- Language-specific style guides live in `prompts/translation/<language>.md`; fallback is `prompts/translation/TEMPLATE.md`.
- Auto-generated VS Code glossaries are in `prompts/translation/glossary/`.
- `prepare-translation` writes batch prompts to `reports/translation/<language>/` (default) or a custom `--output-dir`.
- Each translation sub-agent writes only its assigned `results/batch-###.json`.
- After merging into the final `translations/<language>.json`, always run `validate --language <language>`. Success removes the temporary `reports/translation/<language>` workspace unless `--no-cleanup` is passed.

### Model-scoped translation runs

When comparing models, use `--output-dir` and `--output` to keep runs separate:

```
uv run zed-i18n prepare-translation --language ko-KR --all --output-dir reports/translation-runs/ko-KR/<model-slug>
uv run zed-i18n merge-translation --language ko-KR --results-dir reports/translation-runs/ko-KR/<model-slug>/results --output translations/ko-KR.<model-slug>.json
```

The final `translations/<lang>.json` is produced by reviewing model outputs — see the orchestration prompts below. Use the full-run prompts for complete model comparisons; use the `new-keys` prompts for incremental missing-only accepted strings.

### Orchestration prompts (in `prompts/commands/`)

| File | Purpose |
|---|---|
| `translation-start.md` | End-to-end autonomous translation run for one language and model. Drives `prepare-translation` → parallel sub-agents → `merge-translation`. Fill in `MODEL_ID` and `LOCALE` at the top. |
| `translation-review.md` | Merge two model-scoped translation files into the final `translations/<lang>.json`. Fill in `LOCALE`, `MODEL_A`, `MODEL_B`. |
| `translation-start-new-keys.md` | All-language incremental run for accepted strings missing from existing final translations. Writes new-key-only model artifacts and must not run `merge-translation`. Fill in `MODEL_ID`. |
| `translation-review-new-keys.md` | Compare two new-key-only model artifacts for every final locale, apply selected entries into `translations/<lang>.json`, then validate. Fill in `MODEL_A`, `MODEL_B`, `REVIEW_AGENT_MODEL`. |

## Build Notes

- Zed Windows builds should run outside the sandbox.
- Use `.cache/zed/target` as the shared local Cargo cache via `CARGO_TARGET_DIR`.
- Start local Windows release builds with `-j 8`; increase only if CPU and memory headroom are comfortable.

## Generated Files

- `reports/*` is generated output except `reports/README.md`.
- `reports/translation-runs/` stores per-model translation batch data, preserved across runs.
- `reports/translation-review/` stores generated review workspaces for new-key model comparisons.
- `.cache/non_translated_result` contains user review material and should be preserved unless the user says otherwise.

## Key Paths

```
catalog/en-US.json            — extracted English source strings
manifest/ui-strings.json      — string metadata with status (needs_review / accepted / ignored)
translations/<lang>.json      — final translation files (one per language)
translations/<lang>.<model>.json — model-scoped translation outputs for comparison
prompts/translation/          — language style guides and glossaries
prompts/commands/             — orchestration prompts for AI-driven runs
reports/                      — generated reports (gitignored except README.md)
config/project.toml           — target Zed version and repo settings
config/distribution.toml      — release-only branding/updater overlay used by CI builds, not normal `apply`
```
