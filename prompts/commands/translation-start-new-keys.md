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

Read this whole prompt, then execute the steps in order. After every step, output a single line: `✅ Step N — <one-line result>`.

**Respond to the user in Korean throughout this task.** All status updates, step summaries, and the final report MUST be written in Korean. Code, file paths, command lines, JSON keys/values, and CLI output stay as-is. Translation results must use each locale's generated batch prompt, style guide, glossary, and existing translations.

**Run autonomously end-to-end.** Drive discovery, missing-only preparation, translation, new-key-only artifact creation, partial validation, independent review, fixes, and final reporting without pausing between steps. Step markers are progress reports, not approval gates. Stop only for an anomaly listed at the end.

---

## Step 0 — Project Discovery

1. List the repository root and read the target Zed version from `config/project.toml`.
2. Read `AGENTS.md` and `README.md` end-to-end when present.
3. Skim `tools/zed_i18n/translation_pipeline.py` to confirm that `prepare-translation` defaults to missing-only, `--all` opts into a full run, and `merge-translation` produces a full merged file.
4. Confirm these required paths:
   - `manifest/ui-strings.json`
   - `.cache/zed/<zed-version>-clean-extract`
   - `prompts/translation/`
   - `translations/`
5. Discover final locales from direct `translations/<LANG>.json` files. Exclude model-scoped, comparison, backup, temporary, and scratch files.
6. Confirm `prompts/translation/<LANG>.md` exists for every locale.
7. Confirm that this run targets only manifest entries with `status == "accepted"` that are absent from the locale's final translation file.

Output a short Korean discovery summary, then continue directly to Step 1 when no anomaly exists.

---

## Goals

- Translate only newly accepted strings missing from each final `translations/<LANG>.json`.
- Treat every final translation file as read-only reference material.
- The only file under `translations/` that this workflow may write is `translations/<LANG>.<MODEL_SLUG>.json`; it contains only keys planned for this run.
- Use one translation sub-agent per generated batch and one separate validation sub-agent per locale.
- Never use `--all` or `merge-translation` in this workflow.

---

## Procedure

### Step 1 — Resolve The Model Slug

Derive `<MODEL_SLUG>` from the model name at the top: lowercase, hyphenated, and filesystem-safe, such as `sonnet-4.6`, `gpt-5.5`, or `gpt-5.3-codex`.

Each locale's review artifact is:

```text
translations/<LANG>.<MODEL_SLUG>.json
```

### Step 2 — Prepare Missing-Only Batches

For each `<LANG>`, run:

```text
uv run zed-i18n prepare-translation \
  --language <LANG> \
  --zed-root .cache/zed/<zed-version>-clean-extract \
  --batch-size 75 \
  --output-dir reports/translation-runs/<LANG>/<MODEL_SLUG>
```

Do not pass `--all`. If `.cache/vscode-loc` exists, preparation may add `vscode_references`; `.cache/vscode-upstream` may improve their English source context. Both checkouts are optional.

The CLI also writes `reports/translation/<LANG>/prepare-summary.json`, even when
`--output-dir` is supplied. This preparation summary is an explicitly allowed
exception to the model-scoped report workspace restriction and requires no
additional confirmation. Other generated run files must stay in the specified
`reports/translation-runs/<LANG>/<MODEL_SLUG>/` workspace.

`prepare-translation` automatically includes locale-specific `previous_version_references` in generated batch entries when a usable current-version report is available. These are optional historical translation hints and do not guarantee equivalent meaning. Translation and validation agents must follow the interpretation rule in the generated batch: decide whether to reuse, adapt, or ignore a hint using current source context, context groups, the style guide, and glossary; current placeholders and protected tokens win, and only the current source key may be output. No historical reference is required for normal translation.

Generated entries may also contain `context_group` siblings for settings, connected lines, or composed prompts. These siblings and their translations are read-only context, not additional output keys. For short settings enum labels, `source_comment` may clarify the Rust enum variant.

Read each generated `plan.json` and confirm:

- `missing_only` is `true`;
- `source_count` matches the new-key target count;
- every listed batch has a matching generated prompt.

If `source_count` is `0`, mark the locale complete and do not create or modify its model artifact.

### Step 3 — Dispatch Translation Sub-Agents

For every locale with work, spawn exactly one translation sub-agent per generated batch. Give it:

- exactly one generated `prompts/batch-XXX.md`;
- `prompts/translation/<LANG>.md`;
- the relevant curated glossary under `prompts/translation/glossary/`, when present;
- `translations/<LANG>.json` as read-only terminology and style reference.

Tell each agent to follow the assigned batch prompt verbatim, including its historical-reference interpretation rule and output path. It must output only the exact current source keys assigned by the batch, use `context_group` only as context, and touch only its declared `results/batch-XXX.json`.

If `kind` is `settings_enum_variant_label` or `settings_enum_discriminant_label`, treat the source as a visible settings option label. Use setting siblings and any `source_comment`; do not apply a glossary row solely because an English token matches.

Run independent batches in parallel when practical. Reuse the same sub-agent to repair a missing or invalid result when possible.

### Step 4 — Create New-Key-Only Review Artifacts

Do not run `merge-translation`. For each locale, combine completed result files into:

```text
translations/<LANG>.<MODEL_SLUG>.json
```

Read the planned keys from `batches/batch-XXX.json` and translations from `results/batch-XXX.json`. Keep only planned keys, drop and count `null` values, reject non-string or unknown values, stop on conflicting duplicates, and sort keys according to repository JSON style.

Write `reports/translation-runs/<LANG>/<MODEL_SLUG>/new-key-summary.json` with:

- `language`
- `model_slug`
- `planned`
- `written`
- `null_values`
- `unknown_sources`
- `invalid_values`
- `duplicate_conflicts`
- `output`

### Step 5 — Run Partial Mechanical Validation

Do not use the full-file `validate --language` command on a partial model artifact. For each artifact, verify that every key is accepted, absent from the final translation file, and present in the generated batch plan. Also verify placeholders and protected tokens with:

- `tools.zed_i18n.rust_strings.rust_format_placeholders`
- `tools.zed_i18n.translation_checks.protected_tokens_match`

Write results to `reports/translation-runs/<LANG>/<MODEL_SLUG>/partial-validation.json`. Fix only affected entries and rerun this validation until it passes.

### Step 6 — Dispatch One Validation Sub-Agent Per Locale

After mechanical validation passes, spawn one fresh validation sub-agent per locale. Give it the locale's `plan.json`, batch and result JSON files, summary, partial validation report, model artifact, final translation file, style guide, and glossary.

Tell the reviewer to:

- review only this run's new-key artifact;
- use batch source context, `context_group`, and `previous_version_references` according to the batch interpretation rule;
- treat short settings enum strings as visible option labels and inspect siblings and `source_comment`;
- check terminology, tone, UI brevity, placeholders, protected tokens, code spans, URLs, paths, config keys, action IDs, and capitalization;
- report issues by severity with exact current source strings and suggested replacements;
- confirm that no pre-existing key appears in the model artifact;
- avoid editing files until given a narrow correction task.

### Step 7 — Apply Review Fixes

Apply only clear, actionable findings to `translations/<LANG>.<MODEL_SLUG>.json`. Do not edit the final translation file or unrelated entries. Rerun partial validation after every correction. Keep the existing translation when a review offers only subjective alternatives.

### Step 8 — Optional Integration Sanity Check

When useful, validate an in-memory combination of the final translation dictionary and the new-key-only artifact. Do not write the combined dictionary back to the final locale file. Any report belongs at `reports/translation-runs/<LANG>/<MODEL_SLUG>/integration-validation.json`.

### Step 9 — Final Report

Report in Korean:

- target locale count;
- per-locale planned and written counts;
- per-locale `null`, unknown-source, invalid-value, and duplicate-conflict counts;
- per-locale placeholder and protected-token mismatch counts;
- important fixes raised by validation sub-agents;
- 5–10 samples worth human review;
- a brief overall quality assessment.

---

## Hard Constraints

- Never pass `--all`, perform a full retranslation, or run `merge-translation`.
- Never update `translations/<LANG>.json`.
- Model artifacts contain only newly planned current keys from this run.
- Translation sub-agents write only their assigned result file and never modify batch files, prompts, manifests, or translation artifacts.
- Validation sub-agents do not edit files without a narrowly scoped correction request.
- Result and model-artifact keys equal planned source strings byte-for-byte; do not normalize them.
- `context_group` siblings are context, not permission to add keys.
- Return `null` for internal IDs or code enum values when context is insufficient, except visible `settings_enum_variant_label` and `settings_enum_discriminant_label` values should be translated using their settings context.
- Preserve placeholders, code spans, URLs, file paths, config keys, and action IDs verbatim.
- Keep translation generation and translation review in separate agents.

---

## Anomaly Stop Conditions

Stop and wait for the user only when:

- no final locale can be discovered;
- a locale style guide is missing;
- the translation CLI behavior has diverged from this prompt;
- preparation is not missing-only;
- a process attempts to write outside the approved report workspace or model artifact, except for the CLI's `reports/translation/<LANG>/prepare-summary.json` allowed in Step 2;
- a process attempts to write or merge into a final locale file;
- a model artifact would include pre-existing keys;
- generated batches are unavailable or repeatedly fail;
- mechanical validation finds a systemic problem;
- reviewers find widespread violations that require human terminology decisions.

Handle routine single-batch retries and transient failures without pausing.

Begin Step 0 now.
