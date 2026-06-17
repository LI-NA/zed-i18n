You are a localization reviewer working in the zed-i18n repository. Merge two model-generated translation outputs into a single high-quality `translations/[LOCALE].json`, then validate.

## Target language and models
LOCALE: [LOCALE] (BCP-47 locale form used by `--language`, e.g., ko-KR, ja-JP, zh-CN)
MODEL_A: [MODEL_A]
MODEL_B: [MODEL_B]

## Read first (in this order, before touching any output)
1. `AGENTS.md` and `README.md` — confirm pipeline rules. Note: DO NOT COMMIT. No staging, no branches, no worktrees.
2. `prompts/translation/[LOCALE].md` — language-specific prompt. If missing, fall back to `prompts/translation/TEMPLATE.md`.
3. `prompts/translation/glossary/<lang>.md` — the curated glossary (uses a shorter code than the locale, e.g., `ko.md`, `ja.md`, `zh-cn.md`, `pt-br.md`). This is the baseline terminology.
4. `manifest/ui-strings.json` — read `occurrences`, `kind`, and `call` for any ambiguous or short string.
5. `reports/context-groups/[LOCALE]/` if it already exists — use grouped setting title/description, connected-line, and prompt-component reports to review sibling consistency, multi-line flow, and composed prompt/message flow.
6. `.cache/zed/<version>-clean-extract/...` — open ONLY the source files referenced by `occurrences` for entries you cannot disambiguate from the manifest or context-group reports alone.
7. VS Code language-pack hints if surfaced through `vscode_references` — treat as memory hints, not mandatory replacements.

## Inputs (must already exist; do not regenerate)
- `translations/[LOCALE].[MODEL_A].json`
- `translations/[LOCALE].[MODEL_B].json`

## Output (the only file you may create or modify)
- `translations/[LOCALE].json` — the merged translation map. Valid UTF-8 JSON.
- Key order is fixed: sort all entries lexicographically by the original English source key, matching `json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"`. Do not append keys from one model at the end.

## Merge rules (apply per source key)
1. Pick the candidate that is more accurate, more natural, and most consistent with Zed UI register, the language prompt's TRANSLATION STYLE / DISAMBIGUATION RULES, and the appended glossary.
2. If both candidates are wrong or partial, write a corrected translation yourself using the source context.
3. Preserve byte-for-byte inside translated values:
   - Rust placeholders (`{}`, `{0}`, `{name}`, `{path}`, `{count:?}`)
   - Backtick code spans, URLs, file paths, file extensions, JSON keys, setting keys, command IDs, action IDs
   - Key bindings (`cmd-shift-p`, `ctrl-k ctrl-s`)
   - Product / proper nouns (Zed, GitHub, GitLab, Copilot, Claude, Codex, OpenAI, Anthropic, LSP, Tree-sitter, Wasm, etc.)
   - Escape sequences (`\n`, `\t`, `\r`, `\\`)
4. Do NOT translate internal-ID-shaped values (kebab-case/snake_case that resembles code, config keys, URIs, routes, test fixtures). If a model wrongly translated such an entry, set the merged value to `null` (the validator and downstream tooling treat `null` as "ignore"). Match how existing accepted entries for this language handle these cases.
5. The language prompt's DISAMBIGUATION RULES override either model's choice when they conflict. Glossary is the baseline, not a hard override — source context wins.
6. For short settings enum labels, first inspect `kind`, sibling enum variants, setting title/description context, any `source_comment`, and source occurrences. Do not apply a glossary row just because the English token matches; verify whether the token is an option value, action, display mode, Git term, or adjective.
7. When entries belong to a setting title/description pair, connected multi-line group, or prompt-component group, judge the group together so title wording, description wording, line flow, and composed prompt/message flow agree.
8. Output must be valid JSON: no trailing commas, no comments, no markdown fences. Keys identical to the source strings.

## Forbidden
- Do NOT commit, stage, push, branch, or create worktrees.
- Do NOT modify any file other than `translations/[LOCALE].json`. The two model files, the prompt, the glossary, the manifest, and the Zed source checkout are READ-ONLY.
- Do NOT delete or wipe `.cache/zed`. Do NOT run `cargo clean`.
- Do NOT re-run `prepare-translation`, `extract`, or `apply`.
- Do NOT add new keys that are not present in at least one of the two model files.

## Stop and ask the user before
- Touching anything outside `translations/[LOCALE].json`.
- Removing keys that exist in both model files.
- Resolving an ambiguity that requires a project decision (e.g., a term not covered by the language prompt or glossary).

## Validation
After writing the merged file, run:

```
uv run zed-i18n validate --language [LOCALE] --no-cleanup
```

If validation fails, leave `reports/translation/[LOCALE]/` in place for inspection, fix the merged file based on the validate report, and re-run validation. Do not suppress or work around errors. Keep `--no-cleanup` so successful review validation does not remove local inspection material.

## Final report
1. Per-model evaluation — 1-2 lines each on strengths, weaknesses, and recurring errors (tense, register, placeholder handling, glossary drift, over-translation of IDs, etc.).
2. Merge criteria applied — the 2-3 prompt rules that drove the most decisions.
3. Notable resolutions — how you handled 2-3 large divergences or clear mistranslations.
4. Validation result — pass/fail, and any residual issues you flagged but did not auto-fix.
