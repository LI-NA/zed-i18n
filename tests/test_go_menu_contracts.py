"""Contracts for the Go menu title vs debug-adapter language identifiers.

The menu-bar `Go` title is display text and is translated. The identical
`adapter_language_name` return values ("Go", "Python") are language-registry
identifiers matched against `LanguageName`, so the extractor skips them and
they must never reappear in the manifest (see `_is_inside_adapter_language_name`
in tools/zed_i18n/extract.py).
"""

import json
import unittest
from pathlib import Path

from tools.zed_i18n.runtime_bundles import release_locale_ids


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads(
        (ROOT / "manifest" / "ui-strings.json").read_text(encoding="utf-8")
    )


class GoMenuContractTests(unittest.TestCase):
    def test_go_is_accepted_with_only_the_menu_occurrence(self) -> None:
        entry = _manifest()["Go"]
        self.assertEqual(entry["status"], "accepted")
        self.assertEqual(len(entry["occurrences"]), 1)
        occurrence = entry["occurrences"][0]
        self.assertEqual(occurrence["file"], "crates/zed/src/zed/app_menus.rs")
        self.assertEqual(occurrence["kind"], "menu")

    def test_adapter_language_identifiers_stay_out_of_the_manifest(self) -> None:
        manifest = _manifest()
        for source in ("Go", "Python"):
            with self.subTest(source=source):
                files = [
                    occurrence["file"]
                    for occurrence in manifest[source]["occurrences"]
                ]
                self.assertFalse(
                    [file for file in files if file.startswith("crates/dap_adapters/")],
                    f"{source} must not be patched inside crates/dap_adapters/",
                )

    def test_every_release_locale_translates_the_go_menu(self) -> None:
        for locale in release_locale_ids(ROOT):
            with self.subTest(locale=locale):
                translations = json.loads(
                    (ROOT / "translations" / f"{locale}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertIn("Go", translations)
                self.assertTrue(translations["Go"].strip())


if __name__ == "__main__":
    unittest.main()
