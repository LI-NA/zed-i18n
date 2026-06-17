import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_PROMPTS = ROOT / "prompts" / "translation"
GLOSSARY_DIR = TRANSLATION_PROMPTS / "glossary"


class TranslationPromptContractTests(unittest.TestCase):
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
