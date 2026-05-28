import unittest

from tools.zed_i18n.rust_strings import rust_format_placeholders, rust_string_literal


class RustStringTests(unittest.TestCase):
    def test_extracts_format_placeholders_without_escaped_braces(self) -> None:
        self.assertEqual(
            rust_format_placeholders("Updated to {app_name} {} {{literal}} {err:#}"),
            ["{app_name}", "{}", "{err:#}"],
        )

    def test_placeholder_order_does_not_matter_for_named_placeholders(self) -> None:
        self.assertEqual(
            rust_format_placeholders("Failed to open {path:?}: {error}"),
            ["{path:?}", "{error}"],
        )

    def test_ignores_rust_unicode_escape_braces(self) -> None:
        self.assertEqual(rust_format_placeholders("New Thread\\u{2026}"), [])

    def test_does_not_ignore_invalid_rust_unicode_escape_braces(self) -> None:
        self.assertEqual(rust_format_placeholders("Bad escape \\u{ZZ}"), ["{ZZ}"])

    def test_rust_string_literal_preserves_rust_unicode_escapes(self) -> None:
        self.assertEqual(
            rust_string_literal("Saved to {sep}\\u{2039}name\\u{203A}"),
            '"Saved to {sep}\\u{2039}name\\u{203A}"',
        )


if __name__ == "__main__":
    unittest.main()
