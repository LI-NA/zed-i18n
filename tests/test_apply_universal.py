import json
import shutil
import unittest
from pathlib import Path
from unittest import mock

import tools.zed_i18n.apply_universal as apply_universal_module
from tools.zed_i18n.apply_universal import (
    _rewrite_implicit_format_macros,
    _rewrite_nested_format_literals,
    _rewrite_nested_indoc_literals,
    _verify_manual_rewrite_sites,
    apply_universal,
    build_handling_map,
)


class UniversalApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.zed_root = self.root / "zed"
        self.zed_root.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_builds_complete_handling_map_from_ast_context(self) -> None:
        source = "\n".join(
            [
                'fn render(name: &str) { Label::new("Open Settings"); let _ = format!("Hello {name}"); }',
                'const TITLE: &str = "Fixed title";',
                '/// Setting documentation.',
                'pub struct Setting;',
                'actions!(app, [/// Runs the action.',
                'Run]);',
                'pub enum Mode { Auto }',
            ]
        )
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Open Settings": self._entry(path, source, '"Open Settings"', 1, "label"),
            "Hello {name}": self._entry(path, source, '"Hello {name}"', 1, "label"),
            "Fixed title": self._entry(path, source, '"Fixed title"', 2, "default_title"),
            "Setting documentation.": self._entry(
                path,
                source,
                "Setting documentation.",
                3,
                "rust_doc_comment",
            ),
            "Runs the action.": self._entry(
                path,
                source,
                "Runs the action.",
                5,
                "action_description",
            ),
            "Auto": self._entry(path, source, "Auto", 7, "settings_enum_variant_label"),
        }
        report = build_handling_map(self.zed_root, manifest)

        self.assertEqual(report.accepted_occurrences, 6)
        self.assertEqual(report.kind_count, 5)
        self.assertEqual(
            report.class_counts,
            {
                "action_metadata": 1,
                "rewrite_const_context": 1,
                "rewrite_format": 1,
                "rewrite_static": 1,
                "schema_metadata": 1,
                "settings_enum": 1,
            },
        )
        self.assertEqual(report.duplicates, ())
        self.assertEqual(report.unclassified, ())

    def test_rewrites_static_and_format_calls_and_adds_direct_dependency(self) -> None:
        source = "\n".join(
            [
                "fn render(delta: i32) {",
                '    Label::new("Open Settings");',
                '    Label::new(format!("Changed {} by {delta:+}", side_effect()));',
                "}",
                "",
            ]
        )
        path = self._write_source("crates/demo/src/lib.rs", source)
        cargo = self.zed_root / "crates" / "demo" / "Cargo.toml"
        cargo.write_text(
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n[dependencies]\ngpui.workspace = true\n",
            encoding="utf-8",
        )
        manifest = {
            "Open Settings": self._entry(path, source, '"Open Settings"', 2, "label"),
            "Changed {} by {delta:+}": self._entry(
                path,
                source,
                '"Changed {} by {delta:+}"',
                3,
                "label",
            ),
        }

        report = apply_universal(self.root, self.zed_root, manifest)
        first_source = path.read_text(encoding="utf-8")
        first_cargo = cargo.read_text(encoding="utf-8")
        second = apply_universal(self.root, self.zed_root, manifest)

        self.assertTrue(report.ok)
        self.assertFalse(report.already_applied)
        self.assertEqual(report.applied_occurrences, 2)
        self.assertIn(
            'Label::new(localization::localized_str!("Open Settings"));',
            first_source,
        )
        self.assertIn("localization::format_message(", first_source)
        self.assertIn('"Changed {} by {delta:+}"', first_source)
        self.assertIn('(\"0\", format!(\"{}\", __zed_i18n_arg_0))', first_source)
        self.assertIn('let __zed_i18n_arg_1 = format!(\"{:+}\", delta);', first_source)
        self.assertIn('(\"delta\", format!(\"{}\", __zed_i18n_arg_1))', first_source)
        self.assertEqual(first_source.count("side_effect()"), 1)
        self.assertEqual(first_source.count('format!("{:+}", delta);'), 1)
        self.assertIn("localization.workspace = true", first_cargo)
        self.assertTrue(second.ok)
        self.assertTrue(second.already_applied)
        self.assertEqual(path.read_text(encoding="utf-8"), first_source)
        self.assertEqual(cargo.read_text(encoding="utf-8"), first_cargo)

    def test_nested_literal_argument_is_not_mistaken_for_format_template(self) -> None:
        source = '''fn render(value: Option<&str>) {
    let _ = format!("Status: {}", value.unwrap_or("Disconnected"));
}
'''
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Status: {}": self._entry(path, source, '"Status: {}"', 2, "label"),
            "Disconnected": self._entry(path, source, '"Disconnected"', 2, "label"),
        }
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\n',
            encoding="utf-8",
        )

        report = build_handling_map(self.zed_root, manifest)
        apply_universal(self.root, self.zed_root, manifest)
        rewritten = path.read_text(encoding="utf-8")

        self.assertEqual(
            report.class_counts,
            {"rewrite_format": 1, "rewrite_static": 1},
        )
        self.assertIn("localization::format_message(", rewritten)
        self.assertIn(
            'value.unwrap_or(localization::localized_str!("Disconnected"))',
            rewritten,
        )

    def test_uses_the_runtime_value_of_a_line_continued_format_literal(self) -> None:
        source = 'fn render(name: &str) {\n    let _ = format!("First \\\n        second {name}");\n}\n'
        literal = '"First \\\n        second {name}"'
        path = self._write_source("crates/demo/src/lib.rs", source)
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\n',
            encoding="utf-8",
        )
        manifest = {
            "First second {name}": self._entry(path, source, literal, 2, "label")
        }

        apply_universal(self.root, self.zed_root, manifest)
        rewritten = path.read_text(encoding="utf-8")

        self.assertIn('"First second {name}"', rewritten)
        self.assertNotIn('"First         second {name}"', rewritten)

    def test_rewrites_concat_format_components_as_one_template(self) -> None:
        source = '''fn render(name: &str) {
    let _ = format!(concat!("Hello {} ", "from ", "Zed"), name);
}
'''
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            part: self._entry(path, source, literal, 2, "label")
            for part, literal in (
                ("Hello {} ", '"Hello {} "'),
                ("from ", '"from "'),
                ("Zed", '"Zed"'),
            )
        }
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\n',
            encoding="utf-8",
        )

        apply_universal(self.root, self.zed_root, manifest)
        rewritten = path.read_text(encoding="utf-8")

        self.assertEqual(rewritten.count("localization::format_message("), 1)
        self.assertIn('"Hello {} from Zed"', rewritten)

    def test_rejects_stale_span_without_modifying_checkout(self) -> None:
        source = 'fn render() { Label::new("Open Settings"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Open Settings": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "crates/demo/src/lib.rs",
                        "line": 1,
                        "call": "Label::new",
                        "kind": "label",
                        "start_byte": 0,
                        "end_byte": len('"Open Settings"'.encode("utf-8")),
                    }
                ],
            }
        }

        with self.assertRaisesRegex(ValueError, "stale occurrence span"):
            apply_universal(self.root, self.zed_root, manifest)

        self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_adds_dependency_to_target_specific_dependency_section(self) -> None:
        source = 'fn render() { Label::new("Open"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo.write_text(
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n\n"
            "[target.'cfg(target_os = \"linux\")'.dependencies]\nanyhow.workspace = true\n",
            encoding="utf-8",
        )
        manifest = {"Open": self._entry(path, source, '"Open"', 1, "label")}

        apply_universal(self.root, self.zed_root, manifest)

        self.assertIn("localization.workspace = true", cargo.read_text(encoding="utf-8"))

    def test_rewrites_write_macro_format_literal_without_changing_result_type(self) -> None:
        source = '''fn render(output: &mut String, count: usize) {
    write!(output, " + {} more", count).unwrap();
}
'''
        path = self._write_source("crates/demo/src/lib.rs", source)
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\n',
            encoding="utf-8",
        )
        manifest = {
            " + {} more": self._entry(path, source, '" + {} more"', 2, "label")
        }

        apply_universal(self.root, self.zed_root, manifest)
        rewritten = path.read_text(encoding="utf-8")

        self.assertIn('write!(output, "{}", {', rewritten)
        self.assertIn("localization::format_message(", rewritten)
        self.assertEqual(rewritten.count('format!("{}", count);'), 1)

    def test_repairs_format_macro_nested_inside_an_outer_token_tree(self) -> None:
        source = '''fn render(name: &str) {
    let _ = vec![format!(localization::localized_str!("Hello {name}"))];
}
'''

        rewritten = _rewrite_nested_format_literals(source)

        self.assertNotIn("format!(localization::localized_str!", rewritten)
        self.assertIn("localization::format_message(", rewritten)
        self.assertEqual(rewritten.count('format!("{}", name);'), 1)

    def test_keeps_indoc_compile_time_and_translates_its_static_result(self) -> None:
        source = '''fn render() {
    let _ = indoc!{localization::localized_str!("\n        Help text")};
}
'''

        rewritten = _rewrite_nested_indoc_literals(source)

        self.assertIn(
            'localization::translate_static(indoc!{"\n        Help text"})',
            rewritten,
        )

    def test_preserves_anyhow_family_implicit_formatting(self) -> None:
        source = '''fn validate(path: &str, limit: usize) -> anyhow::Result<()> {
    let first = anyhow!(localization::localized_str!("Invalid path {path:?}"));
    anyhow::bail!(localization::localized_str!("Limit is {}"), limit);
    anyhow::ensure!(limit > 0, localization::localized_str!("Limit {limit} is invalid"));
}
'''

        rewritten = _rewrite_implicit_format_macros(source)

        self.assertNotIn('anyhow!(localization::localized_str!("Invalid path', rewritten)
        self.assertNotIn('bail!(localization::localized_str!("Limit is', rewritten)
        self.assertIn('anyhow!("{}", {', rewritten)
        self.assertIn('anyhow::bail!("{}", {', rewritten)
        self.assertIn('anyhow::ensure!(limit > 0, "{}", {', rewritten)
        self.assertEqual(rewritten.count("localization::format_message("), 3)
        self.assertEqual(rewritten.count('format!("{:?}", path);'), 1)
        self.assertEqual(rewritten.count('format!("{}", limit);'), 2)

    def test_rejects_manual_rewrite_site_missing_from_the_patch_allowlist(self) -> None:
        source = 'const TITLE: &str = "Brand new const";\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Brand new const": self._entry(
                path, source, '"Brand new const"', 1, "default_title"
            )
        }
        handling = build_handling_map(self.zed_root, manifest)

        with self.assertRaisesRegex(ValueError, "unpatched manual rewrite sites"):
            _verify_manual_rewrite_sites(handling)

    def test_rejects_expected_manual_rewrite_sites_that_disappeared(self) -> None:
        handling = build_handling_map(self.zed_root, {})

        with self.assertRaisesRegex(ValueError, "disappeared"):
            _verify_manual_rewrite_sites(handling)

    def test_rejects_second_occurrence_of_an_allowlisted_manual_site(self) -> None:
        source = (
            'const A: &str = "Get Started";\n'
            'static B: &str = "Get Started";\n'
        )
        self._write_source("crates/workspace/src/welcome.rs", source)
        needle = '"Get Started"'
        first = source.index(needle)
        second = source.index(needle, first + 1)
        occurrences = [
            {
                "file": "crates/workspace/src/welcome.rs",
                "line": line,
                "call": "test",
                "kind": "default_title",
                "start_byte": start,
                "end_byte": start + len(needle),
            }
            for line, start in ((1, first), (2, second))
        ]
        handling = build_handling_map(
            self.zed_root,
            {"Get Started": {"status": "accepted", "occurrences": occurrences}},
        )

        with self.assertRaisesRegex(ValueError, "unpatched manual rewrite sites"):
            _verify_manual_rewrite_sites(handling)

    def test_structural_patch_failure_leaves_the_checkout_untouched(self) -> None:
        # An incomplete overlay makes structural planning fail after the
        # call-site rewrites were already planned; nothing may reach disk.
        (self.root / "tools" / "zed_i18n" / "runtime_overlay").mkdir(parents=True)
        source = 'fn render() { Label::new("Open"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        cargo = self.zed_root / "crates/demo/Cargo.toml"
        cargo_text = '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\n'
        cargo.write_text(cargo_text, encoding="utf-8")
        locales = self.zed_root / "assets" / "locales"
        locales.mkdir(parents=True)
        (locales / "index.json").write_text("{}", encoding="utf-8")
        manifest = {"Open": self._entry(path, source, '"Open"', 1, "label")}

        with mock.patch.object(
            apply_universal_module, "_EXPECTED_MANUAL_SITES", frozenset()
        ):
            with self.assertRaisesRegex(ValueError, "runtime overlay file does not exist"):
                apply_universal(self.root, self.zed_root, manifest)

        self.assertEqual(path.read_text(encoding="utf-8"), source)
        self.assertEqual(cargo.read_text(encoding="utf-8"), cargo_text)
        self.assertFalse((self.zed_root / ".zed-i18n-universal.json").exists())

    def test_requires_generated_bundles_before_runtime_patching(self) -> None:
        (self.root / "tools" / "zed_i18n" / "runtime_overlay").mkdir(parents=True)
        source = 'fn render() { Label::new("Open"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {"Open": self._entry(path, source, '"Open"', 1, "label")}

        with self.assertRaisesRegex(ValueError, "generate-runtime-bundles"):
            apply_universal(self.root, self.zed_root, manifest)

        self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_rejects_duplicate_occurrence_span(self) -> None:
        source = 'fn render() { Label::new("Open Settings"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        entry = self._entry(path, source, '"Open Settings"', 1, "label")
        entry["occurrences"].append(dict(entry["occurrences"][0]))

        with self.assertRaisesRegex(ValueError, "duplicate accepted occurrence"):
            build_handling_map(self.zed_root, {"Open Settings": entry})

    def test_rejects_new_unreviewed_kind(self) -> None:
        source = 'fn render() { Label::new("Open Settings"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Open Settings": self._entry(
                path,
                source,
                '"Open Settings"',
                1,
                "brand_new_ui_kind",
            )
        }

        with self.assertRaisesRegex(ValueError, "unrecognized occurrence kind"):
            build_handling_map(self.zed_root, manifest)

    def test_validates_rust_string_line_continuations_like_the_extractor(self) -> None:
        source = 'fn render() { Label::new("First \\\n                              second"); }\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        entry = self._entry(
            path,
            source,
            '"First \\\n                              second"',
            1,
            "label",
        )

        collapsed = build_handling_map(self.zed_root, {"First second": entry})
        preserved = build_handling_map(
            self.zed_root,
            {"First                               second": entry},
        )

        self.assertEqual(collapsed.class_counts, {"rewrite_static": 1})
        self.assertEqual(preserved.class_counts, {"rewrite_static": 1})

    def test_ignores_runtime_overlay_occurrences_during_checkout_rewrite(self) -> None:
        manifest = {
            "Restart Zed": {
                "status": "accepted",
                "occurrences": [
                    {
                        "file": "runtime-overlay/crates/settings_ui/src/locale_picker.rs",
                        "line": 1,
                        "call": "localization::localized_str!",
                        "kind": "runtime_overlay_message",
                        "start_byte": 32,
                        "end_byte": 45,
                    }
                ],
            }
        }

        report = build_handling_map(self.zed_root, manifest)

        self.assertEqual(report.accepted_occurrences, 0)
        self.assertEqual(report.overlay_occurrences, 1)

    def test_validates_generated_settings_enum_labels_against_variant_identifier(self) -> None:
        source = "pub enum DisplayMode { AllScreens }\n"
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "All Screens": self._entry(
                path,
                source,
                "AllScreens",
                1,
                "settings_enum_variant_label",
            )
        }

        report = build_handling_map(self.zed_root, manifest)

        self.assertEqual(report.class_counts, {"settings_enum": 1})

    def test_validates_action_metadata_stored_in_a_string_literal(self) -> None:
        source = 'split_structs!(SplitDown => "Splits the pane downward.");\n'
        path = self._write_source("crates/demo/src/lib.rs", source)
        manifest = {
            "Splits the pane downward.": self._entry(
                path,
                source,
                '"Splits the pane downward."',
                1,
                "action_description",
            )
        }

        report = build_handling_map(self.zed_root, manifest)

        self.assertEqual(report.class_counts, {"action_metadata": 1})

    def _write_source(self, relative: str, source: str) -> Path:
        path = self.zed_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    @staticmethod
    def _entry(
        path: Path,
        source_text: str,
        needle: str,
        line: int,
        kind: str,
    ) -> dict[str, object]:
        char_start = source_text.index(needle)
        start = len(source_text[:char_start].encode("utf-8"))
        end = start + len(needle.encode("utf-8"))
        return {
            "status": "accepted",
            "occurrences": [
                {
                    "file": path.as_posix().split("/zed/", 1)[1],
                    "line": line,
                    "call": "test",
                    "kind": kind,
                    "start_byte": start,
                    "end_byte": end,
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
