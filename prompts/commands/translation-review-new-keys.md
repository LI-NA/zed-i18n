MODEL_A: [MODEL_A]
MODEL_B: [MODEL_B]
REVIEW_AGENT_MODEL: [REVIEW_AGENT_MODEL]
LANGUAGE SCOPE: ALL FINAL TRANSLATION FILES

<!--
  This orchestration prompt reviews two model-generated new-key artifacts
  for every final locale and applies the selected translations into the
  final translations/<locale>.json files.

  Expected model artifacts:
    translations/<locale>.<model-a-slug>.json
    translations/<locale>.<model-b-slug>.json

  Those model artifacts should contain only newly translated keys.

  REVIEW_AGENT_MODEL controls which model to use for per-language review
  sub-agents. Use a concrete model id such as gpt-5.5, or use
  same-as-orchestrator to inherit the orchestrator's model.
-->

# Zed i18n — All-Language Two-Model Translation Review

You are orchestrating final review for newly translated Zed UI strings across every existing final locale. For each language, compare two model-generated new-key artifacts, choose the better translation per source key, correct entries when both models are flawed, and apply only the accepted new keys into `translations/<LANG>.json`.

Read this whole prompt, then execute the phases in order. After every phase, output a single line: `✅ Phase N — <one-line result>`.

**Respond to the user in Korean throughout this task.** All status updates, phase summaries, and the final report MUST be written in Korean. Code, file paths, command lines, JSON keys/values, and CLI output stay as-is — do not translate those. Translation choices themselves must be in each target language.

**Run autonomously end-to-end.** This is a routine review-and-merge job. Once started, drive the work through discovery, per-language review, final-file update, validation, fixes, and final reporting without pausing for user confirmation between phases. Phase markers (`✅ Phase N — …`) are progress reports, NOT approval gates. The only time you stop and wait for the user is if you hit one of the **Anomaly stop conditions** at the bottom of this prompt.

---

## Phase 0 — Project Discovery

Before any review work, ground yourself in the repository:

1. List the repo root; note the top-level layout, check Zed version using `config\project.toml`.
2. Read `AGENTS.md` end-to-end (if it exists).
3. Read `README.md` end-to-end.
4. Read `tools/zed_i18n/validate.py`, `tools/zed_i18n/rust_strings.py`, and `tools/zed_i18n/translation_checks.py` so you know what validation protects.
5. Confirm these paths exist:
   - `manifest/ui-strings.json`
   - `translations/`
   - `prompts/translation/`
   - `.cache/zed/<zed-version>-clean-extract`
6. Discover final target languages from `translations/*.json`.
   - Include final locale files such as `ko-KR.json`, `ja-JP.json`, `zh-CN.json`.
   - Exclude model artifacts such as `ko-KR.gpt-5.5.json`, `ko-KR.sonnet-4.6.json`, backup files, temporary files, and scratch files.
7. Derive `<MODEL_A_SLUG>` and `<MODEL_B_SLUG>` from the model names at the top: lowercase, hyphenated, filesystem-safe, matching the slugs used by `translation-start-new-keys.md`.
8. Resolve `<REVIEW_AGENT_MODEL>` from the top of this prompt.
   - If it is `same-as-orchestrator`, spawn review sub-agents without a model override so they inherit the orchestrator model.
   - If it is a concrete model id, use that model for every per-language review sub-agent.
   - `MODEL_A` and `MODEL_B` identify artifact files only; do not treat them as the review sub-agent model unless `REVIEW_AGENT_MODEL` explicitly says so.
9. For each target language, confirm these files exist when there is new-key work to review:
   - `translations/<LANG>.<MODEL_A_SLUG>.json`
   - `translations/<LANG>.<MODEL_B_SLUG>.json`
   - `prompts/translation/<LANG>.md`
   - `reports/context-groups/<LANG>/` if it already exists (optional review context, not required)
10. Inspect each model artifact before dispatch:
   - It should be much smaller than the final `translations/<LANG>.json`.
   - Its keys should be absent from the final `translations/<LANG>.json`.
   - Its keys should be accepted sources in `manifest/ui-strings.json`.
   - If it looks like a full final translation file, treat it as an anomaly stop.

If both model artifacts are missing for a language, only skip that language after confirming from available `reports/translation-runs/<LANG>/<MODEL_SLUG>/plan.json` files that `source_count` was `0`. If exactly one model artifact is missing for a language with new-key work, treat it as an anomaly stop.

Output a 5–8 line summary of findings (in Korean): detected languages, model slugs, artifact coverage, clean checkout path, and any anomaly. **If no anomaly was found, proceed directly to Procedure step 1 in the same response — do not pause for confirmation.**

---

## Goals

- Compare the two model artifacts for every language with new-key work.
- Produce a reviewed per-language selection artifact under `reports/translation-review/`.
- Apply selected translations into the final `translations/<LANG>.json`.
- Preserve all existing final translations unless the same key was still missing before this review.
- Use one review sub-agent per language, called with `REVIEW_AGENT_MODEL`, to compare candidates with the language prompt, glossary/dictionary, source context, and existing translations.
- Use generated batch `context_group` data, and `reports/context-groups/<LANG>/` when already present, to review setting title/description pairs, connected multi-line strings, and prompt-component strings together.
- Validate every updated final language file with `uv run zed-i18n validate --language <LANG> --no-cleanup`.
- Never modify the model artifacts.
- Never add keys that are absent from both model artifacts.

---

## Procedure

### 1. Prepare Review Workspaces

For each language `<LANG>` with both model artifacts, create a review workspace:

```
reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/
```

Within that workspace, the review sub-agent will write:

- `selected.json` — final chosen translations for new keys only
- `review-summary.json` — structured review notes and counts

Do not modify either model artifact.

### 2. Dispatch One Review Sub-Agent Per Language

For every language with both model artifacts, spawn exactly one review sub-agent for that language.

Model selection:

- If `REVIEW_AGENT_MODEL` is `same-as-orchestrator`, omit the model override when spawning the sub-agent.
- Otherwise, spawn the sub-agent with model `<REVIEW_AGENT_MODEL>`.
- Do not use `<MODEL_A>` or `<MODEL_B>` as the sub-agent model unless one of those exact values was also provided as `REVIEW_AGENT_MODEL`.

Give that sub-agent:

- `translations/<LANG>.<MODEL_A_SLUG>.json`
- `translations/<LANG>.<MODEL_B_SLUG>.json`
- `translations/<LANG>.json`
- `prompts/translation/<LANG>.md`
- relevant glossary/dictionary files under `prompts/translation/glossary/` if they exist
- `manifest/ui-strings.json`
- relevant `reports/translation-runs/<LANG>/<MODEL_A_SLUG>/` and `reports/translation-runs/<LANG>/<MODEL_B_SLUG>/` plan/batch/summary/partial-validation files if they exist
- `reports/context-groups/<LANG>/` if it already exists
- source files under `.cache/zed/<zed-version>-clean-extract` only when needed to resolve ambiguity from manifest occurrences

Tell it:

- You are reviewing `<LANG>` only.
- Compare the two model artifacts key-by-key.
- Use `translations/<LANG>.json` as translation memory and style reference.
- Use `prompts/translation/<LANG>.md` as the primary style guide.
- Use glossary/dictionary files as terminology references.
- Use manifest occurrences, `kind`, `call`, and source context to disambiguate short or ambiguous UI strings.
- Use `context_group` data in batch files and optional context-group reports to judge setting title/description siblings, connected multi-line strings, and prompt-component strings as one UI unit.
- For short settings enum labels, first inspect `kind`, sibling enum variants, setting title/description context, any `source_comment`, and source occurrences. Do not apply a glossary row just because the English token matches; verify whether the token is an option value, action, display mode, Git term, or adjective.
- Choose the better candidate when one model is clearly better.
- If both models are flawed but the intended UI meaning is clear, write a corrected translation.
- If a source is ambiguous, internal-ID-shaped, or unsafe to translate, omit it from `selected.json` and record the reason in `review-summary.json`.
- Preserve placeholders, protected tokens, code spans, URLs, file paths, config keys, command IDs, action IDs, keybindings, product names, and escape sequences.
- Do not edit `translations/<LANG>.json` or either model artifact.
- Write only:
  - `reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/selected.json`
  - `reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/review-summary.json`

The selected file must:

- Contain only source keys present in at least one of the two model artifacts.
- Contain only source keys absent from the current `translations/<LANG>.json`.
- Contain only string translations, no `null` values.
- Sort keys lexicographically.
- Be valid UTF-8 JSON matching the repo's pretty JSON style.

You may run per-language review sub-agents in parallel if the environment can handle it. Keep each language isolated.

### 3. Mechanical Review Of Selection Artifacts

For each language, inspect `selected.json` before applying it.

Reject or fix the selection if:

- It includes a key that is not accepted in `manifest/ui-strings.json`.
- It includes a key already present in `translations/<LANG>.json`.
- It includes a key absent from both model artifacts.
- It includes non-string values.
- Rust format placeholders do not match.
- Protected tokens do not match.
- The JSON is invalid or unsorted.

Use the same helper logic as the pipeline where applicable:

- `tools.zed_i18n.rust_strings.rust_format_placeholders`
- `tools.zed_i18n.translation_checks.protected_tokens_match`

Write a mechanical review report to:

```
reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/mechanical-review.json
```

If a problem is clear and local, fix `selected.json` directly. If a problem suggests the sub-agent misunderstood the language or source context, send the issue back to that language's review sub-agent.

### 4. Apply Selected New Keys

For each language whose `selected.json` passes mechanical review:

1. Read `translations/<LANG>.json`.
2. Add only keys from `selected.json` that are still absent from the final file.
3. Preserve existing translations exactly.
4. Sort all keys lexicographically and write `translations/<LANG>.json` with the repo's JSON style.

Do not use `merge-translation` for this step. The model artifacts are partial review inputs, not final full translation files.

Write an apply summary to:

```
reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/apply-summary.json
```

The summary should include:

- `language`
- `model_a_slug`
- `model_b_slug`
- `selected`
- `applied`
- `skipped_already_present`
- `skipped_invalid`
- `output`

### 5. Validate Final Language Files

For every language updated in Phase 4, run:

```
uv run zed-i18n validate --language <LANG> --no-cleanup
```

If validation fails:

- Inspect the validation report.
- Fix only entries added by this review unless the failure clearly points to pre-existing data.
- Re-run validation for that language.
- Do not suppress or work around validation errors.

### 6. Cross-Language Sanity Pass

After all per-language validations pass, do a quick cross-language sanity pass over the newly applied keys:

- Confirm the same source key was handled consistently across languages where terminology is language-independent, such as product names, action IDs, URLs, and config keys.
- Confirm no language accidentally absorbed another language's translation.
- Confirm no model artifact was modified.
- Confirm no final language received keys that were absent from both model artifacts.

This pass should be lightweight and focused on catching orchestration mistakes.

### 7. Final Report

Output a summary block in Korean:

- 대상 언어 수
- 언어별 모델 A/B 입력 키 수
- 언어별 최종 선택 키 수
- 언어별 최종 적용 키 수
- 언어별 validate 결과
- 모델 A의 반복 강점/약점
- 모델 B의 반복 강점/약점
- 검토 중 직접 보정한 대표 사례 5–10개
- 사람이 추가로 보면 좋을 애매한 항목
- 최종적으로 수정된 `translations/<LANG>.json` 파일 목록

---

## Review Rules

Apply these rules per source key:

1. Pick the candidate that is more accurate, natural, concise for UI, and consistent with the language prompt.
2. Prefer consistency with existing `translations/<LANG>.json` when both candidates are acceptable.
3. If both candidates are wrong but the source context is clear, write a corrected translation yourself.
4. For grouped settings, connected multi-line strings, and prompt-component strings, prefer the candidate that makes the whole group coherent, not just the isolated source key.
5. For short settings enum labels, first inspect `kind`, sibling enum variants, setting title/description context, any `source_comment`, and source occurrences. Do not apply a glossary row just because the English token matches.
6. If neither candidate is safe and the source context is not enough, omit the key from `selected.json` and record why.
7. Do not translate internal IDs, action IDs, config keys, paths, URLs, file extensions, code-like values, or proper nouns unless the language prompt explicitly says otherwise. `settings_enum_variant_label` and `settings_enum_discriminant_label` are visible settings option labels, not internal IDs.
8. Preserve byte-for-byte inside translated values:
   - Rust placeholders (`{}`, `{0}`, `{name}`, `{path}`, `{count:?}`)
   - Backtick code spans
   - URLs, paths, file extensions, JSON keys, setting keys
   - Command IDs, action IDs, keybindings
   - Product and proper names
   - Escape sequences (`\n`, `\t`, `\r`, `\\`)
9. The language prompt's disambiguation and style rules override either model's choice.
10. Glossary/dictionary files are baseline references; source context wins when there is a real conflict.

---

## Hard Constraints

- Do NOT commit, stage, push, branch, or create worktrees.
- Do NOT delete or wipe `.cache/zed`; do NOT run `cargo clean`.
- Do NOT run `prepare-translation`, `extract`, or `apply`.
- Do NOT modify model artifacts `translations/<LANG>.<MODEL_A_SLUG>.json` or `translations/<LANG>.<MODEL_B_SLUG>.json`.
- Do NOT add final keys that are absent from both model artifacts.
- Do NOT rewrite existing final translations unrelated to this review.
- Do NOT let review sub-agents modify final translation files.
- Do NOT choose review sub-agent models implicitly from `MODEL_A` or `MODEL_B`; use `REVIEW_AGENT_MODEL`.
- Only the orchestrator applies selected entries to `translations/<LANG>.json`.
- JSON keys must equal source strings byte-for-byte.

---

## Anomaly Stop Conditions

The happy path runs end-to-end without check-ins. Stop, report what happened in Korean, and wait for the user ONLY in these cases:

- A target language is missing exactly one of the two model artifacts.
- A target language has new-key work but no `prompts/translation/<LANG>.md`.
- `REVIEW_AGENT_MODEL` is missing, still set to the placeholder, or names a model that cannot be used by the environment.
- A model artifact appears to contain a full final translation file instead of only new keys.
- A review sub-agent attempts to modify `translations/<LANG>.json` or either model artifact.
- Mechanical review finds widespread placeholder/protected-token corruption.
- Validation fails for a reason that cannot be attributed to entries added in this review.
- Resolving a term requires a project-level decision not covered by the language prompt, glossary, or existing translations.
- Any action would touch files outside `translations/<LANG>.json` and `reports/translation-review/<LANG>/<MODEL_A_SLUG>__<MODEL_B_SLUG>/`.

Routine retries, one bad selected entry, or a single sub-agent needing correction are NOT anomaly conditions — handle them and keep going.

Begin Phase 0 now.
