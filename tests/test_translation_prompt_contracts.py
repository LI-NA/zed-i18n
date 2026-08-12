import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_PROMPTS = ROOT / "prompts" / "translation"
GLOSSARY_DIR = TRANSLATION_PROMPTS / "glossary"
VERSION_DIFF_REPORT = (
    "reports/version-diff/<from-version>-to-<to-version>/key-changes.json"
)
QUOTE_PRESERVATION_RULE = (
    "For an untranslated technical literal, preserve its content and any quote "
    "characters that are part of its syntax. For translated natural-language prose "
    "or UI labels, localize the surrounding quote glyphs according to the locale guide."
)


class TranslationPromptContractTests(unittest.TestCase):
    def test_translation_prompts_share_quote_preservation_rule(self) -> None:
        prompt_paths = sorted(TRANSLATION_PROMPTS.glob("*.md"))
        self.assertEqual(len(prompt_paths), 14)

        for prompt_path in prompt_paths:
            with self.subTest(prompt=prompt_path.name):
                prompt = prompt_path.read_text(encoding="utf-8")
                self.assertEqual(prompt.count(QUOTE_PRESERVATION_RULE), 1)
                self.assertNotIn("Quote characters used as syntax or emphasis", prompt)

        locale_quote_rules = {
            "cs-CZ.md": "Use Czech quotation marks `„“` for quoted natural-language prose.",
            "pl-PL.md": "Use Polish quotation marks `„”` for quoted natural-language prose.",
            "ja-JP.md": (
                "Use Japanese corner brackets `「」` for primary quotes and `『』` for "
                "nested quotes in natural-language prose."
            ),
            "zh-CN.md": (
                "Use Chinese quotation marks `“”` for primary quotes and `‘’` for "
                "nested quotes in natural-language prose."
            ),
        }
        for file_name, quote_rule in locale_quote_rules.items():
            with self.subTest(locale=file_name):
                prompt = (TRANSLATION_PROMPTS / file_name).read_text(encoding="utf-8")
                self.assertIn(quote_rule, prompt)

        existing_locale_quote_rules = {
            "de-DE.md": "In prose use German-style quotation marks",
            "es-ES.md": "Use straight quotes",
            "fr-FR.md": "Use guillemets « » in prose",
            "ru-RU.md": "Use Russian-style guillemets « »",
            "zh-TW.md": "Use `「」` for primary quotes",
        }
        for file_name, quote_rule in existing_locale_quote_rules.items():
            with self.subTest(locale=file_name):
                prompt = (TRANSLATION_PROMPTS / file_name).read_text(encoding="utf-8")
                self.assertIn(quote_rule, prompt)

    def test_language_prompts_keep_preserve_rules_in_disambiguation_section(self) -> None:
        required_tokens = ("SKILL.md", "Agent Client Protocol", "Claude Agent")
        for prompt_path in sorted(TRANSLATION_PROMPTS.glob("*.md")):
            if prompt_path.name == "TEMPLATE.md":
                continue
            with self.subTest(prompt=prompt_path.name):
                section = _section(prompt_path.read_text(encoding="utf-8"), "DISAMBIGUATION RULES")
                for token in required_tokens:
                    self.assertIn(token, section)

    def test_template_glossary_coverage_terms_exist_in_all_glossaries(self) -> None:
        template = (TRANSLATION_PROMPTS / "TEMPLATE.md").read_text(encoding="utf-8")
        covered_terms = _template_glossary_coverage_terms(template)
        self.assertGreater(len(covered_terms), 0)

        for glossary_path in sorted(GLOSSARY_DIR.glob("*.md")):
            glossary_terms = _glossary_english_terms(glossary_path)
            missing = sorted(covered_terms - glossary_terms)
            with self.subTest(glossary=glossary_path.name):
                self.assertEqual(missing, [])

    def test_curated_glossaries_use_three_column_table(self) -> None:
        for glossary_path in sorted(GLOSSARY_DIR.glob("*.md")):
            with self.subTest(glossary=glossary_path.name):
                rows = _glossary_rows(glossary_path)
                self.assertGreater(len(rows), 0)
                for cells in rows:
                    self.assertEqual(len(cells), 3)
                    self.assertTrue(cells[0])
                    self.assertTrue(cells[2])

    def test_review_prompt_uses_curated_glossary_wording(self) -> None:
        review_prompt = (ROOT / "prompts" / "commands" / "translation-review.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("curated glossary", review_prompt)
        self.assertNotIn("auto-generated glossary", review_prompt)

    def test_translation_prompts_document_settings_enum_option_labels(self) -> None:
        required_tokens = (
            "settings_enum_variant_label",
            "settings_enum_discriminant_label",
            "short settings option labels",
        )
        for prompt_path in sorted(TRANSLATION_PROMPTS.glob("*.md")):
            with self.subTest(prompt=prompt_path.name):
                prompt = prompt_path.read_text(encoding="utf-8")
                for token in required_tokens:
                    self.assertIn(token, prompt)

    def test_glossary_headers_warn_against_context_free_replacements(self) -> None:
        required_tokens = (
            "single-but-ambiguous",
            "blank = applies broadly after checking UI role",
            "glossary rows are not blind replacements",
        )
        for glossary_path in sorted(GLOSSARY_DIR.glob("*.md")):
            with self.subTest(glossary=glossary_path.name):
                glossary = glossary_path.read_text(encoding="utf-8")
                for token in required_tokens:
                    self.assertIn(token, glossary)

    def test_command_prompts_call_out_short_settings_enum_labels(self) -> None:
        command_dir = ROOT / "prompts" / "commands"
        expectations = {
            "translation-start.md": (
                "settings_enum_variant_label",
                "visible settings option label",
            ),
            "translation-review.md": (
                "short settings enum labels",
                "Do not apply a glossary row just because the English token matches",
            ),
            "translation-audit.md": (
                "Short settings enum labels",
                "Do not “fix” a compact option into a longer explanatory phrase",
            ),
            "translation-start-new-keys.md": (
                "settings_enum_variant_label",
                "visible settings option label",
            ),
            "translation-review-new-keys.md": (
                "short settings enum labels",
                "Do not apply a glossary row just because the English token matches",
            ),
        }
        for file_name, required_tokens in expectations.items():
            with self.subTest(prompt=file_name):
                prompt = (command_dir / file_name).read_text(encoding="utf-8")
                for token in required_tokens:
                    self.assertIn(token, prompt)

    def test_translation_audit_recurring_term_is_metadata_only(self) -> None:
        audit_prompt = (ROOT / "prompts" / "commands" / "translation-audit.md").read_text(
            encoding="utf-8"
        )

        required_tokens = (
            "recurring_term",
            "grouping/reporting metadata only",
            "must not search, replace, or fan out",
            "never global search/replace or term-based fan-out",
        )
        for token in required_tokens:
            self.assertIn(token, audit_prompt)

    def test_translation_audit_generates_strict_review_evidence_contract(self) -> None:
        audit_prompt = (ROOT / "prompts" / "commands" / "translation-audit.md").read_text(
            encoding="utf-8"
        )

        required_tokens = (
            "schema_version",
            "sibling_candidates",
            "shared_short",
            "sibling_review",
            "shared_key_review",
            "defect_type",
            "evidence",
            "term_evidence",
            "family",
            "preflight_outputs.py",
            "regenerate only the batch metadata",
            "does not make a locale-only change an error",
            "Every changed family member still requires its own exact `key`, `current`, and `proposed` entry",
        )
        for token in required_tokens:
            self.assertIn(token, audit_prompt)

        self.assertIn("never triggers search, replacement, or fan-out", audit_prompt)
        self.assertLess(
            audit_prompt.index("preflight_outputs.py <LOCALE>"),
            audit_prompt.index("apply_changes.py <LOCALE>"),
        )

    def test_version_bump_instructions_use_executable_key_change_workflow(self) -> None:
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        required_tokens = (
            "generate-version-diff",
            VERSION_DIFF_REPORT,
            "The main orchestrator only runs the generator command",
            "`prepare-translation` automatically",
        )
        forbidden_tokens = (
            "deleted-key-memory.json",
            "git show <base_commit>",
        )

        for token in required_tokens:
            self.assertIn(token, instructions)
        for token in forbidden_tokens:
            self.assertNotIn(token, instructions)

    def test_new_key_prompt_relies_on_automatic_batch_references(self) -> None:
        prompt = (
            ROOT / "prompts" / "commands" / "translation-start-new-keys.md"
        ).read_text(encoding="utf-8")
        required_tokens = (
            "previous_version_references",
            "optional historical translation hints",
            "current source context",
            "current placeholders and protected tokens win",
        )
        for token in required_tokens:
            self.assertIn(token, prompt)
        self.assertNotIn("deleted-key-memory.json", prompt)
        self.assertIsNone(re.search(r"(?i)\bgit\b", prompt))

    def test_new_key_prompt_scopes_model_artifact_writes_to_translations(self) -> None:
        prompt = (
            ROOT / "prompts" / "commands" / "translation-start-new-keys.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "The only file under `translations/` that this workflow may write is "
            "`translations/<LANG>.<MODEL_SLUG>.json`",
            prompt,
        )

    def test_korean_readme_documents_version_diff_workflow(self) -> None:
        readme = (ROOT / "docs" / "readme" / "ko-KR.md").read_text(encoding="utf-8")
        usage = _section(readme, "사용법")
        commands = (
            "uv run zed-i18n extract --zed-root .cache/zed/<version>-clean-extract",
            "uv run zed-i18n generate-version-diff",
            "uv run zed-i18n audit-candidates --zed-root .cache/zed/<version>-clean-extract",
        )

        command_positions = [usage.find(command) for command in commands]
        self.assertTrue(all(position >= 0 for position in command_positions))
        self.assertEqual(command_positions, sorted(command_positions))
        self.assertIn("key-changes.json", usage)
        self.assertIn("prepare-translation", usage)


def _section(markdown: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n(?P<body>.*?)(?=^## |\Z)",
        markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return ""
    return match.group("body")


def _template_glossary_coverage_terms(template: str) -> set[str]:
    section = _section(template, "CURATED GLOSSARY AND DISAMBIGUATION")
    terms: set[str] = set()
    capture = False
    for line in section.splitlines():
        if line.startswith("The glossary covers terms"):
            capture = True
            continue
        if capture and not line.startswith("- "):
            break
        if not capture:
            continue
        _, term_list = line.split(":", 1)
        terms.update(term.strip() for term in term_list.split(",") if term.strip())
    return terms


def _glossary_english_terms(path: Path) -> set[str]:
    return {cells[0] for cells in _glossary_rows(path)}


def _glossary_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells[0] == "English":
            continue
        rows.append(cells)
    return rows


if __name__ == "__main__":
    unittest.main()
