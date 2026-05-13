MODEL TO USE: [MODEL_ID]
LANGUAGE SCOPE: ALL FINAL TRANSLATION FILES

<!--
  This orchestration prompt translates only newly accepted strings that are
  missing from existing final translation files under translations/<locale>.json.

  The output for each language is a review artifact:
    translations/<locale>.<model-slug>.json

  That file MUST contain only the newly translated keys from this run.
  It MUST NOT contain pre-existing translations from translations/<locale>.json.
-->

# Zed i18n — All-Language New-Key Translation Orchestration

You are orchestrating an incremental translation job for every existing final Zed locale. This prompt is only for newly accepted strings that do not yet exist in each `translations/<LANG>.json` file. It is not a full retranslation run and it must not update the final translation files.

Read this whole prompt, then execute the phases in order. After every phase, output a single line: `✅ Phase N — <one-line result>`.

**Respond to the user in Korean throughout this task.** All status updates, phase summaries, and the final report MUST be written in Korean. Code, file paths, command lines, JSON keys/values, and CLI output stay as-is — do not translate those. Translation results themselves must be written into each target language according to that locale's batch prompt, style guide, glossary, and existing translations.

**Run autonomously end-to-end.** This is a routine all-language incremental translation job. Once started, drive the work through discovery, missing-only preparation, per-language translation, new-key-only artifact creation, partial validation, per-language validation review, fixes, and final reporting without pausing for user confirmation between phases. Phase markers (`✅ Phase N — …`) are progress reports, NOT approval gates. The only time you stop and wait for the user is if you hit one of the **Anomaly stop conditions** at the bottom of this prompt.

---

## Phase 0 — Project Discovery

Before any translation work, ground yourself in the repository:

1. List the repo root; note the top-level layout, check Zed version using `config\project.toml`.
2. Read `AGENTS.md` end-to-end (if it exists).
3. Read `README.md` end-to-end.
4. Skim `tools/zed_i18n/translation_pipeline.py` to confirm:
   - `prepare-translation` defaults to missing-only.
   - `--all` is the opt-in full-run flag and must not be used here.
   - `merge-translation` reads `translations/<LANG>.json` and writes a full merged translation file, so it MUST NOT be used for this review artifact.
5. Confirm these paths exist:
   - `manifest/ui-strings.json` — accepted translation targets
   - `.cache/zed/<zed-version>-clean-extract` — clean Zed checkout used as source
   - `prompts/translation/` — target-language style guides and glossary material
   - `translations/` — existing final translation files
6. Discover target languages from `translations/*.json`.
   - Include final locale files such as `ko-KR.json`, `ja-JP.json`, `zh-CN.json`.
   - Exclude model-scoped or comparison artifacts such as `ko-KR.gpt-5.5.json`.
   - Exclude backup, temporary, or generated scratch files.
7. For every target language, confirm `prompts/translation/<LANG>.md` exists. If a style guide is missing for any target language, treat it as an anomaly stop.
8. Confirm that this run will translate only manifest entries where `status == "accepted"` and the source string is absent from that language's `translations/<LANG>.json`.

Output a 5–8 line summary of findings (in Korean): detected target languages, Zed version, clean checkout path, and any anomaly. **If no anomaly was found, proceed directly to Procedure step 1 in the same response — do not pause for confirmation.**

---

## Goals

- Translate only newly accepted strings missing from each existing final `translations/<LANG>.json`.
- Preserve every existing final translation file exactly. Treat `translations/<LANG>.json` as read-only reference material.
- Save each language's new translations to `translations/<LANG>.<MODEL_SLUG>.json`.
- Ensure `translations/<LANG>.<MODEL_SLUG>.json` contains only new keys from this run, never pre-existing translations.
- For each language, use one translation sub-agent for that language's batches.
- For each language, use a separate validation sub-agent after the new-key-only artifact is created, so translation generation and review do not contaminate each other.
- The validation sub-agent must review with the language style guide, translation glossary/dictionary material, and existing translations as references.
- Never use `--all`. This run must stay missing-only for every language.
- Never use `merge-translation` for the final review artifact, because it produces full merged files rather than new-key-only files.

---

## Procedure

### 1. Resolve The Model Slug

Take the model name from the top of this prompt and derive `<MODEL_SLUG>`: lowercase, hyphenated, filesystem-safe (for example `sonnet-4.6`, `gpt-5.5`, `gpt-5.3-codex`). Use this slug everywhere `<MODEL_SLUG>` appears below.

Each language's final review artifact is:

```
translations/<LANG>.<MODEL_SLUG>.json
```

### 2. Prepare Missing-Only Batches For Every Language

For each target language `<LANG>`, run `prepare-translation` without `--all`. The default behavior is missing-only: accepted strings already present in `translations/<LANG>.json` are excluded.

```
uv run zed-i18n prepare-translation \
  --language <LANG> \
  --zed-root .cache/zed/<zed-version>-clean-extract \
  --batch-size 75 \
  --output-dir reports/translation-runs/<LANG>/<MODEL_SLUG>
```

If `.cache/vscode-loc` exists, `prepare-translation` automatically adds optional `vscode_references` translation-memory hints to matching entries. `.cache/vscode-upstream` improves English source recovery for those hints. Missing VS Code reference checkouts are normal and are NOT an anomaly.

After each preparation step, read `reports/translation-runs/<LANG>/<MODEL_SLUG>/plan.json` and confirm:

- `missing_only` is `true`
- `source_count` is the number of new keys to translate for that language
- every batch listed under `batches` has a matching prompt file under `reports/translation-runs/<LANG>/<MODEL_SLUG>/prompts/`

If `source_count` is `0` for a language, mark that language as complete with no new work and do not create or modify `translations/<LANG>.<MODEL_SLUG>.json` for that language.

### 3. Dispatch One Translation Sub-Agent Per Language

For every language with `source_count > 0`, spawn exactly one translation sub-agent for that language.

Give that translation sub-agent:

- every generated `reports/translation-runs/<LANG>/<MODEL_SLUG>/prompts/batch-XXX.md`
- `prompts/translation/<LANG>.md`
- relevant glossary/dictionary references under `prompts/translation/glossary/` if they exist
- the existing `translations/<LANG>.json` as translation-memory and style reference only

Tell it:

- You are translating only newly accepted, missing keys for `<LANG>`.
- Process this language's batch prompts sequentially.
- Follow each batch prompt verbatim.
- Use the style guide, glossary/dictionary references, and existing translations to keep terminology and tone consistent.
- Write each result JSON only to the `output.result_file` path declared inside that batch prompt.
- Do not touch anything else.
- Do not modify `translations/<LANG>.json`, `translations/<LANG>.<MODEL_SLUG>.json`, the manifest, prompt files, or batch files.

You may run the per-language translation sub-agents in parallel if the environment can handle it. Keep each language isolated: one translation sub-agent owns one language.

If a result file is missing or invalid, re-use that language's existing translation sub-agent when possible and ask it to fix only the failed batch. Do not spawn extra translation sub-agents for the same language unless the existing one is unavailable or failed irrecoverably.

### 4. Create New-Key-Only Review Artifacts

Do NOT run `merge-translation`.

For each language with completed result files, collect that language's result JSON files into:

```
translations/<LANG>.<MODEL_SLUG>.json
```

The output file must contain only valid translations for source strings listed in that language's generated batches. It must not include any key already present in `translations/<LANG>.json`.

When collecting results:

- Read the planned source strings from `reports/translation-runs/<LANG>/<MODEL_SLUG>/batches/batch-XXX.json`.
- Read translations from `reports/translation-runs/<LANG>/<MODEL_SLUG>/results/batch-XXX.json`.
- Keep only keys that are in the planned source set.
- Drop `null` values from the output artifact and count them in the summary.
- Treat non-string values as invalid and do not write them.
- Treat unknown source keys as invalid and do not write them.
- If the same source appears more than once with different translations, stop for that language and inspect before writing.
- Sort output keys consistently with the repo's JSON style.
- Write a summary to `reports/translation-runs/<LANG>/<MODEL_SLUG>/new-key-summary.json`.

The summary should include:

- `language`
- `model_slug`
- `planned`
- `written`
- `null_values`
- `unknown_sources`
- `invalid_values`
- `duplicate_conflicts`
- `output`

### 5. Run Partial Mechanical Validation

Do not run `uv run zed-i18n validate --language <LANG>` as the main validation for `translations/<LANG>.<MODEL_SLUG>.json`; that CLI validates the full final file, while this artifact is intentionally partial.

For each new-key-only artifact, run a partial validation against only the newly translated keys:

- Every output key must be an accepted manifest source.
- Every output key must be absent from `translations/<LANG>.json`.
- Every output key must appear in the generated batch source set.
- Placeholders must match the source.
- Protected tokens must match the source.
- The output file must contain no pre-existing translation keys.

Use the same helper logic as the pipeline where applicable:

- `tools.zed_i18n.rust_strings.rust_format_placeholders`
- `tools.zed_i18n.translation_checks.protected_tokens_match`

Write the partial validation report to:

```
reports/translation-runs/<LANG>/<MODEL_SLUG>/partial-validation.json
```

If partial validation reports placeholder or protected-token mismatches, fix only the affected entries in `translations/<LANG>.<MODEL_SLUG>.json` and rerun the partial validation.

### 6. Dispatch One Validation Sub-Agent Per Language

After partial mechanical validation passes for `<LANG>`, spawn exactly one separate validation sub-agent for that language. This must be a new sub-agent that did not perform the translation.

Give that validation sub-agent:

- `reports/translation-runs/<LANG>/<MODEL_SLUG>/plan.json`
- every generated `reports/translation-runs/<LANG>/<MODEL_SLUG>/batches/batch-XXX.json`
- every generated `reports/translation-runs/<LANG>/<MODEL_SLUG>/results/batch-XXX.json`
- `reports/translation-runs/<LANG>/<MODEL_SLUG>/new-key-summary.json`
- `reports/translation-runs/<LANG>/<MODEL_SLUG>/partial-validation.json`
- `translations/<LANG>.<MODEL_SLUG>.json`
- `translations/<LANG>.json`
- `prompts/translation/<LANG>.md`
- relevant glossary/dictionary references under `prompts/translation/glossary/` if they exist

Tell it:

- You are reviewing only the new-key-only artifact from this run.
- Use the batch files to identify source strings and source context.
- Use `translations/<LANG>.<MODEL_SLUG>.json` to inspect the proposed new translations.
- Use `translations/<LANG>.json` only as existing translation memory and style reference.
- Use `prompts/translation/<LANG>.md` as the primary translation prompt and style guide.
- Use glossary/dictionary references and existing translations as terminology and tone references.
- Check placeholder preservation, code spans, URLs, file paths, configuration keys, action IDs, capitalization conventions, UI brevity, and consistency with existing translations.
- Confirm that `translations/<LANG>.<MODEL_SLUG>.json` contains only newly translated keys and no pre-existing keys.
- Report issues by severity and include exact source strings and suggested replacements.
- Do not edit files unless explicitly instructed by the orchestrator after review.

The validation sub-agent's job is quality review, not translation generation. Keep this role separate to reduce prompt contamination.

### 7. Apply Review Fixes To New-Key Artifacts Only

For each language, review the validation sub-agent's findings.

- Apply only clear, actionable fixes to `translations/<LANG>.<MODEL_SLUG>.json`.
- Do not rewrite unrelated entries in the new-key artifact.
- Do not edit `translations/<LANG>.json`.
- If the review raises subjective alternatives, keep the current translation unless the issue is clearly harmful or inconsistent with the language guide.
- After any fix, rerun partial mechanical validation for that language.
- If a fix affects terminology likely shared across multiple languages, inspect the same source string in other newly translated model artifacts before finalizing.

### 8. Optional Full Integration Sanity Check

If you want an extra safety check, create an in-memory combined dictionary from:

- existing `translations/<LANG>.json`
- new-key-only `translations/<LANG>.<MODEL_SLUG>.json`

Then run the repository's validation helper against that combined dictionary without writing it back to `translations/<LANG>.json`. If you need a temporary report, write it under:

```
reports/translation-runs/<LANG>/<MODEL_SLUG>/integration-validation.json
```

This step is only a sanity check. It must not produce or overwrite a full merged translation file.

### 9. Final Report

Output a summary block in Korean:

- 대상 언어 수
- 언어별 신규 번역 대상 수
- 언어별 `translations/<LANG>.<MODEL_SLUG>.json` 작성 문자열 수
- 언어별 `null` 반환 수
- 언어별 unknown source 수
- 언어별 invalid value 수
- 언어별 duplicate conflict 수
- 언어별 placeholder mismatch 수
- 언어별 protected token mismatch 수
- 검증 서브 에이전트가 제기한 주요 수정 사항
- 사람이 추가로 보면 좋을 샘플 5–10개
- 전반적인 신규 번역 품질 인상 (2–4문장)

---

## Hard Constraints

- Never run `prepare-translation` with `--all` in this prompt.
- Do not perform a full retranslation.
- Do not run `merge-translation` for this prompt's output artifact.
- Do not update final locale files `translations/<LANG>.json`.
- The only translation artifacts this run may write are `translations/<LANG>.<MODEL_SLUG>.json`, and each must contain only new keys from this run.
- Never write pre-existing `translations/<LANG>.json` entries into `translations/<LANG>.<MODEL_SLUG>.json`.
- Translation sub-agents MUST NOT modify batch files, prompt files, the manifest, or any translation file.
- Validation sub-agents MUST NOT modify files unless the orchestrator explicitly asks for a narrowly scoped correction.
- Each translation sub-agent MUST write only assigned `results/batch-XXX.json` files for its own language.
- JSON keys in result files and model artifacts MUST equal the source string byte-for-byte — no whitespace fixes, no Unicode folding, no normalization.
- If a string is ambiguous, looks like an internal ID/enum, or cannot be confidently translated, return `null`. Do not guess.
- Preserve all placeholders, code spans, URLs, file paths, config keys, and action IDs verbatim.
- Keep translation generation and translation review in separate sub-agents.

---

## Anomaly Stop Conditions

The happy path runs end-to-end without check-ins. Stop, report what happened in Korean, and wait for the user ONLY in these cases:

- No final target languages can be discovered under `translations/*.json`.
- `prompts/translation/<LANG>.md` does not exist for one or more target languages.
- `tools/zed_i18n/translation_pipeline.py` CLI flags have diverged from what this prompt assumes.
- Any prepare step is not missing-only, or `plan.json` shows `missing_only` is not `true`.
- A scoped action would touch anything outside `reports/translation-runs/<LANG>/<MODEL_SLUG>/` or `translations/<LANG>.<MODEL_SLUG>.json`.
- A process attempts to write, overwrite, or merge into `translations/<LANG>.json`.
- A process attempts to create `translations/<LANG>.<MODEL_SLUG>.json` with pre-existing translations included.
- Fewer batches are available than the prepare step generated, or a batch keeps failing after several retry attempts.
- Partial mechanical validation reveals a systemic problem that cannot be attributed to a single bad batch or clear translation mistake.
- Validation sub-agents identify widespread style-guide violations for a language that require human terminology decisions.

Routine retries (single failed result file, transient rate limit, one bad translation batch) are NOT anomaly conditions — handle them and keep going.

Begin Phase 0 now.
