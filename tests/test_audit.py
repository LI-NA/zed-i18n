import unittest

from tools.zed_i18n.audit import audit_string_candidates_from_source


class AuditTests(unittest.TestCase):
    def test_marks_rule_extracted_strings_and_unmatched_candidates(self) -> None:
        source = "\n".join(
            [
                "fn render(extension_id: &str) {",
                '    Label::new("Visible Label");',
                '    format!("Installing {extension_id} extension…");',
                '    let telemetry_key = "zed.event_name";',
                "}",
            ]
        )

        candidates = audit_string_candidates_from_source(
            source,
            relative_path="crates/activity_indicator/src/activity_indicator.rs",
        )

        by_source = {candidate.source: candidate for candidate in candidates}
        self.assertTrue(by_source["Visible Label"].matched_by_rule)
        self.assertEqual(by_source["Visible Label"].call, "Label::new")
        self.assertTrue(by_source["Installing {extension_id} extension…"].matched_by_rule)
        self.assertEqual(by_source["Installing {extension_id} extension…"].call, "format!")
        self.assertIn("zed.event_name", by_source)


if __name__ == "__main__":
    unittest.main()
