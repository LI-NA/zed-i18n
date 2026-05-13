MODEL TO USE: [MODEL_ID]
TARGET LANGUAGE: [LOCALE]

<!--
  TARGET LANGUAGE must be a locale code that matches both:
    - prompts/translation/<code>.md  (style guide must exist)
    - the --language value accepted by `uv run zed-i18n` commands
  Examples: zh-CN, zh-TW, ja-JP, fr-FR, de-DE, es-ES
-->

# Zed i18n — Full <TARGET_LANG> Translation Run

You are running a coordinated, multi-agent translation job for the Zed editor's `<TARGET_LANG>` locale, using the model declared at the top. Read this whole prompt, then execute the phases in order. After every phase, output a single line: `✅ Phase N — <one-line result>`.

**Respond to the user in Korean throughout this task.** All status updates, phase summaries, and the final report MUST be written in Korean. Code, file paths, command lines, JSON keys/values, and CLI output stay as-is — do not translate those. (Sub-agents producing `<TARGET_LANG>` translations are a separate concern — they translate into `<TARGET_LANG>` per their batch prompt, regardless of this rule.)

**Run autonomously end-to-end.** This is a routine translation job. Once started, drive the work all the way through to the final artifact `translations/<TARGET_LANG>.<MODEL_SLUG>.json` without pausing for user confirmation between phases. Phase markers (`✅ Phase N — …`) are progress reports, NOT approval gates. The only time you stop and wait for the user is if you hit one of the **Anomaly stop conditions** at the bottom of this prompt.

---

## Phase 0 — Project discovery (do this first, no exceptions)

Before any translation work, ground yourself in the repository:

1. List the repo root; note the top-level layout, check Zed version using `config\project.toml`.
2. Read `AGENTS.md` end-to-end (if it exists).
3. Read `README.md` end-to-end.
4. Read `prompts/translation/<TARGET_LANG>.md` — the target-language style guide, glossary, and preservation rules. Every sub-agent MUST receive this file later. If this file does not exist, treat it as an anomaly stop.
5. Skim `tools/zed_i18n/translation_pipeline.py` to confirm the `prepare-translation` and `merge-translation` CLI flags match what this prompt assumes. If flags have diverged, treat it as an anomaly stop.
6. Confirm these paths exist:
   - `manifest/ui-strings.json` — accepted translation targets
   - `.cache/zed/<zed-version>-clean-extract` — clean Zed checkout used as source
7. Inventory `translations/`. List which `translations/<lang>.json` files already exist. Treat ALL of them as reference-only — never overwrite or modify any pre-existing translation file under `translations/`, regardless of language.

This run's output is ALWAYS the model-scoped file `translations/<TARGET_LANG>.<MODEL_SLUG>.json` (see Procedure step 4). If a base `translations/<TARGET_LANG>.json` happens to exist, DO NOT overwrite or merge into it — the model-scoped file is a parallel artifact for later human comparison/consolidation.

Output a 5–8 line summary of findings (in Korean) and flag any anomaly. **If no anomaly was found, proceed directly to Procedure step 1 in the same response — do not pause for confirmation.**

---

## Goals

- Produce a fresh `<TARGET_LANG>` translation using the model declared at the top of this prompt.
- Write the new translation to a model-scoped output file: `translations/<TARGET_LANG>.<MODEL_SLUG>.json`. Multiple models will run independently; quality comparison and merging happen later, outside this prompt.
- Never modify any pre-existing translation file under `translations/`, regardless of language.
- Run translation batches in parallel via sub-agents.

## Concurrency rules

- Use as many parallel sub-agents as the environment allows.
- Hard cap: **25 concurrent sub-agents**. Never exceed this.
- Ramp up gradually — start with ~5–10, observe completion and any rate-limit signals, then scale up. Do not launch everything at once.

---

## Procedure

### 1. Resolve the model slug

Take the model name from the top of this prompt and derive `<MODEL_SLUG>`: lowercase, hyphenated, filesystem-safe (e.g. `sonnet-4.6`, `gpt-5.5`, `gpt-5.3-codex`). Use this slug everywhere `<MODEL_SLUG>` appears below.

### 2. Prepare batches

```
uv run zed-i18n prepare-translation \
  --language <TARGET_LANG> \
  --zed-root .cache/zed/<zed-version>-clean-extract \
  --all \
  --batch-size 75 \
  --output-dir reports/translation-runs/<TARGET_LANG>/<MODEL_SLUG>
```

If `.cache/vscode-loc` exists, `prepare-translation` automatically adds optional `vscode_references` translation-memory hints to matching entries. `.cache/vscode-upstream` improves English source recovery for those hints. Missing VS Code reference checkouts are normal and are NOT an anomaly.

### 3. Dispatch sub-agents

For each generated `reports/translation-runs/<TARGET_LANG>/<MODEL_SLUG>/prompts/batch-XXX.md`:

- Spawn one sub-agent (respecting the 25-cap and ramp-up rule).
- Give it the single batch prompt file AND `prompts/translation/<TARGET_LANG>.md`.
- Tell it: follow the batch prompt verbatim, and write its result JSON ONLY to the `output.result_file` path declared inside that batch prompt. It must not touch anything else.

Re-dispatch any sub-agent whose batch fails or produces an invalid result file. Continue until every batch has a valid result on disk.

### 4. Merge

Once every batch result is on disk:

```
uv run zed-i18n merge-translation \
  --language <TARGET_LANG> \
  --results-dir reports/translation-runs/<TARGET_LANG>/<MODEL_SLUG>/results \
  --output translations/<TARGET_LANG>.<MODEL_SLUG>.json
```

This produces the model-scoped output file. Cross-model comparison and final consolidation are out of scope for this run.

### 5. Validate the merged output

Spot-check that the following are preserved verbatim from source:
- Placeholders (`{0}`, `{name}`, `%s`, etc.)
- Backtick-wrapped code/identifiers
- URLs and file paths
- Configuration keys
- Action IDs

### 6. Final report (in Korean)

Output a summary block for this model:
- 병합 성공 문자열 수
- `null` 반환 수
- unknown source 수
- invalid value 수
- placeholder mismatch 수
- protected token mismatch 수
- 사람이 검토하면 좋을 샘플 5–10개 (긴 문자열 / 짧은 문자열 / 기술 용어 / 일반 문구를 섞어서)
- 전반적인 번역 품질 인상 (2–4문장)

---

## Hard constraints (restate the relevant ones to every sub-agent)

- Never modify any pre-existing translation file under `translations/`, regardless of language. The only translation file this run produces is `translations/<TARGET_LANG>.<MODEL_SLUG>.json`.
- Sub-agents MUST NOT modify batch files, prompt files, the manifest, or any existing translation file.
- Sub-agents MUST write only their assigned `results/batch-XXX.json`.
- JSON keys in result files MUST equal the source string byte-for-byte — no whitespace fixes, no Unicode folding, no normalization.
- If a string is ambiguous, looks like an internal ID/enum, or cannot be confidently translated, return `null`. Do not guess.
- Preserve all placeholders, code spans, URLs, file paths, config keys, and action IDs verbatim.

---

## Anomaly stop conditions

The happy path runs end-to-end without check-ins. Stop, report what happened in Korean, and wait for the user ONLY in these cases:

- `prompts/translation/<TARGET_LANG>.md` does not exist.
- `tools/zed_i18n/translation_pipeline.py` CLI flags have diverged from what this prompt assumes.
- A scoped action would touch anything outside `reports/translation/<TARGET_LANG>/prepare-summary.json`, `reports/translation-runs/<TARGET_LANG>/<MODEL_SLUG>/` or `translations/<TARGET_LANG>.<MODEL_SLUG>.json`.
- Fewer batches available than the prepare step generated, or a batch keeps failing after several re-dispatches.
- Validation reveals a systemic problem (e.g. widespread placeholder corruption) that cannot be attributed to a single bad batch.

Routine retries (single failed sub-agent, transient rate limit) are NOT anomaly conditions — handle them and keep going.

Begin Phase 0 now.
