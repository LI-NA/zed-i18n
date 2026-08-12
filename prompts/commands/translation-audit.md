TARGET LANGUAGES: [LOCALES_OR_ALL]
AUDIT_DIR_NAME: [DIR_NAME]

<!--
  TARGET LANGUAGES forms (one of):
    - all                                    → all 13 supported locales
    - ko-KR                                  → single locale
    - ko-KR,ja-JP,zh-CN                      → comma-separated subset
  Each locale code must:
    - have `prompts/translation/<code>.md`   (style guide must exist)
    - have `translations/<code>.json`        (final translation must exist)
  Supported set: cs-CZ, de-DE, es-ES, fr-FR, it-IT, ja-JP, ko-KR,
                 pl-PL, pt-BR, ru-RU, tr-TR, zh-CN, zh-TW.

  AUDIT_DIR_NAME is the leaf folder under `reports/` for all outputs of this run.
  Use a name that does NOT collide with existing reserved folders:
    - reports/translation-runs/      (per-model batch data, RESERVED)
    - reports/translation/           (prepare-translation workspace, RESERVED)
    - reports/translation-review/    (new-key model comparisons, RESERVED)
    - reports/context-groups/        (review-only context group reports, RESERVED)
  Recommended values: `translation-audit`, `translation-qa`, `translation-pass`.
  If the folder already exists with prior data, the procedure resumes from
  whatever is already on disk (idempotent — won't redo completed batches).
-->

# Zed i18n — Full Translation Audit (Conservative Review Pass)

You are running a coordinated, multi-agent **audit/QA pass** over one or more pre-translated Zed locales. The translation files already exist and have passed multiple earlier AI review rounds — your job is **NOT** to rewrite them, but to catch a small number of genuine defects (mistranslation, unnatural phrasing, broken connected-sentence flow inside multi-line doc-comment clusters, terminology/sibling inconsistencies, document-wide recurring mistranslations) and emit two artefacts per language:
- applied `changes.json` entries directly into `translations/<LOCALE>.json` (must-fix)
- a curated `suggestions.md` of optional improvements (could-do — left for human review)

Target conservative change rate: **1–5% of keys per batch**. A higher rate means you are being too aggressive — back off.

Read this whole prompt, then execute the phases in order. After every phase, output a single line: `✅ Phase N — <one-line result>`.

**Respond to the user in Korean throughout this task.** All status updates, phase summaries, and the final report MUST be written in Korean. Code, file paths, command lines, JSON keys/values, CLI output, and the per-language sub-agent prompts stay as-is.

**Run autonomously end-to-end.** This is a routine audit job. Once started, drive the work all the way through to the final SUMMARY.md without pausing for user confirmation between phases. Phase markers (`✅ Phase N — …`) are progress reports, NOT approval gates. The only time you stop and wait for the user is if you hit one of the **Anomaly stop conditions** at the bottom of this prompt.

---

## Phase 0 — Project discovery (do this first, no exceptions)

Before any audit work, ground yourself in the repository:

1. List the repo root; note the top-level layout, check Zed version in `config/project.toml`.
2. Read `AGENTS.md` end-to-end.
3. Read `CLAUDE.local.md` if it exists — honour any local "DO NOT COMMIT" rules.
4. Confirm these paths exist:
   - `manifest/ui-strings.json` — status-annotated key metadata (accepted / needs_review / ignored)
   - `catalog/en-US.json` — English source of truth
   - `.cache/zed/<zed-version>-clean-extract/` — clean Zed checkout used as source context
5. For every locale in `TARGET LANGUAGES`, confirm `translations/<LOCALE>.json` and `prompts/translation/<LOCALE>.md` exist. Note the matching glossary short code in `prompts/translation/glossary/`:
   - cs-CZ → cs · de-DE → de · es-ES → es · fr-FR → fr · it-IT → it
   - ja-JP → ja · ko-KR → ko · pl-PL → pl · pt-BR → pt-br · ru-RU → ru
   - tr-TR → tr · zh-CN → zh-cn · zh-TW → zh-tw
6. Check whether `reports/<AUDIT_DIR_NAME>/` already exists. If yes — this is an idempotent re-run, skip what's already done in Phases 1–2. If no — fresh run, will create the folder.
7. Verify no collision with reserved folders (see top-of-file comment).

Output a 5–8 line summary of findings (in Korean), the resolved locale list, and any anomaly. **If no anomaly was found, proceed directly to Phase 1 in the same response — do not pause for confirmation.**

---

## Goals

- For each locale in `TARGET LANGUAGES`, run a per-batch audit using one Claude Code sub-agent per batch.
- Each sub-agent emits `changes.json` (must-fix) + `suggestions.json` (ideation) + `notes.md` (audit memo) for its assigned batch.
- Use context-group reports to review setting title/description pairs, connected multi-line strings, and prompt-component strings as UI units instead of isolated alphabetic keys.
- After every batch in a locale finishes, the main agent applies that locale's `changes.json` entries to `translations/<LOCALE>.json` via the provided apply script.
- After all locales finish, compile per-locale `suggestions.md` and a top-level `SUMMARY.md`.
- **No `translations/<LOCALE>.json` is ever modified by a sub-agent directly** — only the main agent applies changes through the apply script.

---

## Procedure

### Phase 1 — Preprocess (idempotent)

Use audit metadata `schema_version: 2` for this contract. If `reports/<AUDIT_DIR_NAME>/preprocess/batches.json` already exists, accept the existing batch packing and do not repack it. Ensure `reports/<AUDIT_DIR_NAME>/context-groups/<LOCALE>/summary.json` exists for every resolved locale and generate any missing context-group reports. Then ensure the run-local metadata builder, agent guide, preflight, apply, and compiler helpers match the contract below. If any batch-meta file is missing or does not have top-level `schema_version: 2`, regenerate only the batch metadata with `build_batch_meta.py`; do not rebuild `batches.json`. Reuse versioned batch metadata only when every expected file has the current schema version. For a fresh run, perform every step below.

1. Create the workspace folder: `reports/<AUDIT_DIR_NAME>/preprocess/`.
2. For every resolved locale, generate or reuse grouped review context:
   ```
   uv run zed-i18n extract-context-groups --language <LOCALE> --group-type all --output-dir reports/<AUDIT_DIR_NAME>/context-groups/<LOCALE>
   ```
   If the output already contains `summary.json`, treat it as reusable for this idempotent run.
3. Write `reports/<AUDIT_DIR_NAME>/preprocess/build_batches.py` — the batch-split + cluster-detection script. It must:
   - load `manifest/ui-strings.json`, keep only entries with `status == "accepted"` that also exist in `catalog/en-US.json` (audit candidates)
   - group keys by their first occurrence's source file, sort by line within each file
   - keep setting title/description context groups atomic using `settings-groups.json`
   - keep connected-line context groups atomic using `connected-lines.json`
   - keep prompt-component context groups atomic using `prompt-components.json`
   - pack into batches targeting ~320 keys (max 420), keeping all context groups atomic
   - emit `batches.json`, `clusters.json`, `context-groups.json`, `summary.md` in the same folder
4. Write `reports/<AUDIT_DIR_NAME>/preprocess/build_batch_meta.py`, the per-batch metadata extractor. Every `batch-meta/batch-XXX.json` must contain top-level `schema_version: 2`. For each key include `key`, `source` (English), `primary` (file/line/kind/call from first occurrence), `files` (deduped), `occurrence_count`, and `cluster_id` / `context_group_id` / `context_group_type` when applicable. Also include:
   - `shared_short: true` when the exact source key is 30 characters or shorter and has at least 4 manifest occurrences. Only for those entries, include the complete deduplicated `occurrences` list with file, line, kind, and call so every call site can be reviewed. Do not copy full occurrences into ordinary entries.
   - `sibling_candidates` for another accepted key with a same-kind occurrence in the same file within 3 source lines. Each candidate contains its exact catalog key, file, line, kind, and line distance. This is review evidence only, not proof that both keys must change. Existing explicit settings, connected-line, and prompt context groups remain the stronger relationship signal.
   This lets sub-agents skip the 92K-line manifest without hiding the call sites needed for high-risk short keys.
5. On a fresh run, run both scripts. On a resume run with accepted batch packing, run only `build_batch_meta.py` when the version check above requires metadata regeneration:
   ```
   uv run python reports/<AUDIT_DIR_NAME>/preprocess/build_batches.py
   uv run python reports/<AUDIT_DIR_NAME>/preprocess/build_batch_meta.py
   ```
6. Write `reports/<AUDIT_DIR_NAME>/agent-guide.md` — the per-sub-agent instruction document. It must specify:
   - the six audit lenses (A. mistranslation · B. unnatural phrasing · C. setting title/description consistency · D. connected-sentence flow · E. terminology consistency · F. document-wide / recurring mistranslation)
   - **Short settings enum labels**: review `settings_enum_variant_label` and `settings_enum_discriminant_label` as option values. Check sibling variants, setting title/description, and any `source_comment` before changing them. Do not “fix” a compact option into a longer explanatory phrase, and do not align it to a glossary row unless the setting context matches.
   - **the MAJORITY TRAP rule** (state it explicitly): frequency is NOT correctness. NEVER align a correct translation to a more-frequent wrong one — consistency with a wrong term is still wrong. When the same English term is translated inconsistently across keys, first decide which form is CORRECT (from the source meaning + real target-language usage), then align wrong occurrences toward the correct form **even if the correct form is currently the minority**. If the DOMINANT form is itself the mistranslation, a document-wide correction is valid only as explicit per-key changes: emit one normal `changes.json` entry for each affected key you audited and whose `current` value you verified. Do NOT assume `recurring_term` causes automatic fan-out. If you suspect broader document-wide impact outside your assigned/audited keys, record it in `notes.md` and/or `suggestions.json` for follow-up rather than inventing changes.
   - **lens F output:** when a finding is a recurring/document-wide mistranslation, add a `recurring_term` field (the English term) to each explicit `changes.json` or `suggestions.json` entry that belongs to that recurring issue. This field is grouping/reporting metadata only. `apply_changes.py` applies only listed key-level changes and must not search, replace, or fan out changes from `recurring_term`.
   - **sibling review evidence:** when a changed key has `sibling_candidates`, require `sibling_review` with `reviewed_keys`, `decision` (`change_only_this`, `change_family`, or `no_true_sibling`), and a source/context-based `reason`. The candidate relationship requires review, not a forced sibling edit.
   - **shared short-key evidence:** when changing a `shared_short` entry, require `shared_key_review` with `occurrences_reviewed: true`, `reviewed_count` equal to `occurrence_count`, and a reason why the wording is valid at every call site. This is a per-locale evidence gate and does not make a locale-only change an error.
   - **suggestion admission:** every suggestion must have exactly one `defect_type` from `grammar`, `source_semantics`, `terminology_collision`, `sibling_inconsistency`, `explicit_style_rule`, or `connected_flow`, plus concrete `evidence`. Personal preference, "more natural", or frequency alone is not admissible. `explicit_style_rule` evidence cites the guide file and line; `source_semantics` evidence cites source or runtime behavior.
   - **term counts:** a terminology or recurring-term suggestion must include `term_evidence` with exact `live_form`, exact `proposed_form`, `count_mode: translation_values_containing_case_sensitive_literal`, `live_count`, and `proposed_count`. Counts establish whether a precedent exists; they never decide correctness and remain subject to the MAJORITY TRAP.
   - **family metadata:** `family` is optional review metadata with `basis`, exact catalog-key `members`, `reviewed_members`, `decision` (`change_all`, `keep_all`, `mixed_with_reason`, or `follow_up_required`), and `reason`. It never triggers search, replacement, or fan-out. Every changed family member still requires its own exact `key`, `current`, and `proposed` entry. If an out-of-batch member must change for the proposal to be safe, submit the issue as a `follow_up_required` suggestion instead of an incomplete must-fix.
   - the LANGUAGE_SHORT glossary mapping table
   - the prohibition list (no worktree / no branch / no git write / no `translations/*.json` modification / no auto-script audit / no sub-agent spawning)
   - the output spec for `changes.json`, `suggestions.json`, `notes.md` (key MUST byte-match catalog; current MUST byte-match the live translation; placeholders/backticks/product names/escapes preserved; conditional evidence fields above are required when their gate applies; optional `recurring_term` and `family` fields are metadata only and do not imply application to unlisted keys)
   - conservative target: **1–5% must-fix rate**
   - context-group workflow: read `reports/<AUDIT_DIR_NAME>/context-groups/<LOCALE>/settings-groups.md`, `connected-lines.md`, and `prompt-components.md` for assigned keys before proposing sibling, line-flow, or prompt-composition fixes
7. Write `reports/<AUDIT_DIR_NAME>/preflight_outputs.py`, the strict audit-output validator invoked with one locale before apply. It must exit nonzero and report exact batch/item errors when any check fails. It must:
   - require all three batch files and valid object/list/count shapes; reject missing/null required fields rather than silently defaulting them
   - verify every output key is an accepted catalog key assigned to that batch, every `current` byte-matches the live locale file, totals match list lengths, and explicit keys are not duplicated across batches
   - verify every `proposed` and `alternative` preserves Rust placeholders and protected tokens using the repository's existing checks
   - validate `defect_type` and non-empty concrete `evidence` for every suggestion
   - require and validate `sibling_review` for changed entries with candidates, while allowing a reasoned decision to leave every candidate unchanged
   - require `shared_key_review` for a changed `shared_short` key and verify its evidence covers every occurrence; never compare locales or flag a change merely because only one locale changes that English key
   - recompute each `term_evidence` count from the current `translations/<LOCALE>.json` values using the declared exact case-sensitive literal mode; counts are evidence only
   - validate every `family.members` and `family.reviewed_members` value as an exact catalog key. Treat `family` as metadata only. A family never triggers search, replacement, or fan-out, and every changed member must have its own exact per-key change entry
   - write a locale preflight log/summary and make any failure an anomaly before apply
8. Write `reports/<AUDIT_DIR_NAME>/apply_changes.py`, which applies one locale's `batch-XX/changes.json` files into `translations/<LOCALE>.json`. It must:
   - verify each change's `current` byte-matches the live file before applying (skip with warning on mismatch)
   - treat `recurring_term` and any other unknown metadata fields as informational only; apply only explicit entries with verified `key`, `current`, and `proposed`, never global search/replace or term-based fan-out
   - preserve original file formatting (2-space indent, `ensure_ascii=False`, sorted keys, trailing `\n`, Windows-default newline handling)
   - emit `reports/<AUDIT_DIR_NAME>/<LOCALE>/apply.log`
   - support `--dry-run`
9. Write `reports/<AUDIT_DIR_NAME>/compile_suggestions.py`. After strict preflight succeeds, it walks every `batch-XX/suggestions.json` per locale and produces `reports/<AUDIT_DIR_NAME>/<LOCALE>/suggestions.md` with a totals header, per-batch summary table, and per-suggestion blocks showing key, current, alternative, reason, `defect_type`, `evidence`, and any `term_evidence` or `family`. Do not tolerate missing/null required fields; preflight must reject them.

✅ Phase 1 — preprocess workspace ready (N batches, M clusters/context groups detected, N batch-meta files, helper scripts and agent-guide written)

### Phase 2 — Per-locale audit + apply (one locale per round-set)

For each locale in `TARGET LANGUAGES`, in this exact order:

1. **Dispatch round-set** — three sequential rounds of up to 6 sub-agents each:
   - Round A: `batch-001` … `batch-006` (folder names `batch-01` … `batch-06`)
   - Round B: `batch-007` … `batch-012`
   - Round C: `batch-013` … `batch-018`

   Each sub-agent receives a tiny, near-identical prompt of the form:

   ```
   You are a translation audit agent. **Read `reports/<AUDIT_DIR_NAME>/agent-guide.md` first** for full instructions, output spec, and prohibitions.

   Your assignment:
   - LANGUAGE = <LOCALE>
   - BATCH_ID = batch-NNN          ← NNN is zero-padded 3-digit (matches batch-meta filename)

   Primary input: `reports/<AUDIT_DIR_NAME>/preprocess/batch-meta/batch-NNN.json`.
   Grouped review context: `reports/<AUDIT_DIR_NAME>/context-groups/<LOCALE>/`.
   Output: `reports/<AUDIT_DIR_NAME>/<LOCALE>/batch-NN/` — `changes.json`, `suggestions.json`, `notes.md` (use `batch-NN`, two-digit zero-padded folder name).

   Reminders: no worktree/branch/commit/push; do not modify `translations/<LOCALE>.json`; audit each key by reading it (no auto-scripted comparison); review setting groups, short settings enum labels, connected-line groups, prompt-component groups, `sibling_candidates`, and every occurrence of `shared_short` keys when present; suggestions require `defect_type` and concrete `evidence`; family metadata never fans out changes; be conservative (~1–5% must-fix); final report under 200 words, file paths only.
   ```

2. **Retry transient failures.** If any sub-agent returns "API Error … Rate limited" or "Unable to connect", re-dispatch only the failed batches. Resume from the same round. Routine retries are not anomalies.

3. **Verify completeness.** After Round C, confirm every `batch-01` … `batch-18` folder contains all three files (`changes.json`, `suggestions.json`, `notes.md`). Re-dispatch any missing batch.

4. **Strict preflight:** once all 18 batches are complete, validate all changes, suggestions, and conditional review evidence before touching the translation:
   ```
   uv run python reports/<AUDIT_DIR_NAME>/preflight_outputs.py <LOCALE>
   ```
   Do not apply or compile that locale unless preflight exits successfully with no invalid items.

5. **Apply:** after strict preflight succeeds:
   ```
   uv run python reports/<AUDIT_DIR_NAME>/apply_changes.py <LOCALE>
   ```
   Then `git diff --stat translations/<LOCALE>.json` to confirm `N insertions / N deletions` matches `applied: N` in the log.

6. Emit a one-line per-locale summary in Korean: applied count, suggestion count, change rate %, top 1–2 recurring patterns.

Move to the next locale only after the current locale's apply succeeds.

✅ Phase 2 — all locales audited and applied

### Phase 3 — Compile per-locale `suggestions.md`

```
uv run python reports/<AUDIT_DIR_NAME>/compile_suggestions.py
```

This produces `reports/<AUDIT_DIR_NAME>/<LOCALE>/suggestions.md` for each locale touched.

✅ Phase 3 — N suggestions.md files compiled

### Phase 4 — Top-level SUMMARY.md

Write `reports/<AUDIT_DIR_NAME>/SUMMARY.md` with these sections (in Korean):

- 개요 표 (대상 언어 수, 키 수, 배치 수, 적용 changes 총합, suggestions 총합)
- 언어별 결과 표 (적용 changes · suggestions · 변화율)
- 주요 발견 패턴 (rust_doc_comment 클러스터, 용어 일관성, 평행 표현, 오역, 스타일 가이드 위반)
- 소스 코드 레벨 이슈 (placeholder 영문 잔존 등 — 사용자가 upstream Zed에 보고할 후보)
- 검수 파이프라인 다이어그램
- 다음 단계 권장 (suggestions.md 검토, 글로벌 용어 통일, validate 실행)
- 파일 구조 도표

✅ Phase 4 — SUMMARY.md written

### Phase 5 — Final report to the user (in Korean)

A concise message containing:
- 검수 완료 언어 / 배치 / 적용 changes / suggestions 총계
- 평균 변화율 + 목표 범위 충족 여부
- 가장 인상적인 발견 2–3건 (각 1줄)
- 핵심 산출물 경로 (SUMMARY.md, 각 언어 suggestions.md)
- `validate --language <LOCALE>` 권장 안내

---

## Hard constraints (carry forward to every sub-agent)

- **NEVER** create a git worktree. **NEVER** use `git worktree add`. **NEVER** pass `isolation: "worktree"` when spawning a sub-agent.
- **NEVER** change branches or create new branches. Stay on whatever branch the user is on (master/main).
- **NEVER** run any git write command (`git commit`, `git add`, `git push`, `git stash`, `git reset`). Read-only `git diff`/`git log` is fine.
- **NEVER** commit or stage anything, even if hooks suggest it.
- **Sub-agents MUST NOT modify `translations/<LOCALE>.json` directly.** Only the main agent applies changes via `apply_changes.py`.
- Sub-agents MUST NOT spawn their own sub-agents.
- Sub-agents MUST audit each key by reading it, not by writing a comparison script.
- Every `key` in a sub-agent's output MUST equal `catalog/en-US.json[key]` byte-for-byte.
- Every `current` field MUST equal `translations/<LOCALE>.json[key]` byte-for-byte at the time the sub-agent ran.
- Every `proposed`/`alternative` MUST preserve placeholders (`{}`, `{name}`, `{0}`), backtick code spans, URLs, file paths, product/proper nouns, and escape sequences (`\n`, `\t`).
- `sibling_candidates`, `shared_short`, `term_evidence`, and `family` are review evidence. They never authorize implicit edits. Every applied edit remains an explicit exact-key entry with a verified live `current` and a token-safe `proposed`.
- **Three plural-suffix keys are special — never alter their plural placeholder.** In `Show {} warning{}`, `{} Comment{}`, and `Resolve Merge Conflict{} with Agent`, the English source fills the trailing `{}` with a pluralization suffix (`""` for singular, `"s"` for plural — e.g. "1 warning" vs "3 warnings"). A correct translation MAY keep that `{}`, reposition it onto the head noun, or replace it with `{:.0}` — which renders **nothing** (precision 0 on the suffix string), a deliberate way to drop the English "s" in languages that do not pluralize by an appended suffix. All of these are intentional. NEVER "fix" `{:.0}` back to `{}`, never remove or relocate the suffix placeholder, and never flag these three keys' placeholder form as a defect: the current form is the answer.
- **Per-key token preservation inside connected-line groups (validator-enforced).** Protected tokens — single-quoted `'snake_case'` setting keys, backtick code spans, placeholders, paths — are checked PER KEY by `validate`. When smoothing the flow of a multi-line connected group, a token that appears in one key's English source MUST remain in that same key's translation — do NOT move it onto a sibling line to make the joined sentence read better. If a clean flow fix is impossible without dropping or relocating a token across keys, leave the current translation. (The `'preferred_line_length'` connected key has failed validation exactly this way.)
- The audit run NEVER touches `.cache/zed/` (read-only) or any file outside `reports/<AUDIT_DIR_NAME>/` and `translations/<LOCALE>.json` for in-scope locales.
- On Windows, write Python helper scripts to a `.py` file and invoke with `uv run python <file>` — do not use inline `python -c` or heredocs (cp949 / shell-escaping pitfalls).

---

## Anomaly stop conditions

The happy path runs end-to-end without check-ins. Stop, report in Korean, and wait for the user ONLY in these cases:

- `manifest/ui-strings.json` or `catalog/en-US.json` does not exist.
- For any requested locale, `translations/<LOCALE>.json` or `prompts/translation/<LOCALE>.md` does not exist.
- `AUDIT_DIR_NAME` collides with a reserved folder under `reports/` AND that folder already contains unrelated data.
- A batch keeps failing after 3 re-dispatch attempts (not a transient rate-limit retry).
- `preflight_outputs.py` reports any invalid item, stale current, missing conditional evidence, count mismatch, duplicate key, or family member that is not an exact catalog key.
- `apply_changes.py` reports `skipped_mismatch > 0` on a fresh run with no prior partial apply — this means a sub-agent's `current` does not match the live file, which signals a manifest drift or a race.
- The per-batch must-fix rate exceeds 10% across multiple batches in a row — sub-agents are being too aggressive; the agent-guide may need tightening.

Routine retries (single failed sub-agent, transient rate limit, connection blip) are NOT anomaly conditions — handle them and keep going.

Begin Phase 0 now.
