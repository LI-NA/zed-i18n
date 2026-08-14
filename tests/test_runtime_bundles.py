import hashlib
import json
import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.config import ProjectConfig
from tools.zed_i18n.runtime_bundles import (
    compile_format_plan,
    generate_runtime_bundles,
    load_locale_config,
)


class RuntimeBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True)
        self.zed_root = self.root / "zed"
        self.zed_root.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_repository_locale_config_covers_every_translation(self) -> None:
        repository_root = Path.cwd()

        config = load_locale_config(repository_root / "config" / "locales.toml")

        configured = {locale.id for locale in config.locales if locale.enabled}
        translated = {path.stem for path in (repository_root / "translations").glob("*.json")}
        self.assertEqual(configured - {"en-US"}, translated)
        self.assertEqual(config.source_locale, "en-US")
        self.assertEqual(len(translated), 13)

    def test_rejects_duplicate_locale_aliases(self) -> None:
        path = self.root / "locales.toml"
        path.write_text(
            """
source_locale = "en-US"

[[locale]]
id = "en-US"
english_name = "English"
native_name = "English"
aliases = ["en"]
direction = "ltr"
enabled = true

[[locale]]
id = "en-GB"
english_name = "English"
native_name = "English"
aliases = ["en"]
direction = "ltr"
enabled = true
""".lstrip(),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "duplicate locale alias"):
            load_locale_config(path)

    def test_compiles_positional_named_and_escaped_format_segments(self) -> None:
        self.assertEqual(
            compile_format_plan("Use {{name}}: {user} moved {1} from {0:+}"),
            (
                {"text": "Use {name}: "},
                {"arg": "user"},
                {"text": " moved "},
                {"arg": "1"},
                {"text": " from "},
                {"arg": "0"},
            ),
        )
        self.assertEqual(
            compile_format_plan("Today at {} ({:+})"),
            (
                {"text": "Today at "},
                {"arg": "0"},
                {"text": " ("},
                {"arg": "1"},
                {"text": ")"},
            ),
        )
        self.assertEqual(
            compile_format_plan(r"\u{2014} Modified in {place}"),
            ({"text": "\N{EM DASH} Modified in "}, {"arg": "place"}),
        )

    def test_rejects_dynamic_width_and_precision(self) -> None:
        for source in ("{value:width$}", "{value:.*}"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "dynamic width or precision"):
                    compile_format_plan(source)

    def test_generates_static_format_and_joined_doc_entries_deterministically(self) -> None:
        source_file = self.zed_root / "crates" / "sample" / "src" / "lib.rs"
        source_file.parent.mkdir(parents=True)
        source_text = (
            'pub fn message(name: &str) -> String { format!("Welcome, {name}!") }\n'
            'pub const STATIC: &str = "Use {name} literally";\n'
            "/// First documentation line.\n"
            "/// Second documentation line.\n"
            "pub struct Setting;\n"
        )
        source_file.write_text(source_text, encoding="utf-8")
        format_start = len('pub fn message(name: &str) -> String { format!('.encode("utf-8"))
        format_literal = '"Welcome, {name}!"'
        static_start = len(
            (
                'pub fn message(name: &str) -> String { format!("Welcome, {name}!") }\n'
                "pub const STATIC: &str = "
            ).encode("utf-8")
        )
        doc_one_start = len(source_text[: source_text.index("First documentation")].encode("utf-8"))
        doc_two_start = len(source_text[: source_text.index("Second documentation")].encode("utf-8"))

        catalog = {
            "First documentation line.": "First documentation line.",
            "Second documentation line.": "Second documentation line.",
            "Use {name} literally": "Use {name} literally",
            "Welcome, {name}!": "Welcome, {name}!",
        }
        manifest = {
            "Welcome, {name}!": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=1,
                        start=format_start,
                        end=format_start + len(format_literal.encode("utf-8")),
                        call="Label::new",
                        kind="label",
                    )
                ],
            },
            "Use {name} literally": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=2,
                        start=static_start,
                        end=static_start + len('"Use {name} literally"'.encode("utf-8")),
                        call="SharedString::new_static",
                        kind="shared_string",
                    )
                ],
            },
            "First documentation line.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=3,
                        start=doc_one_start,
                        end=doc_one_start + len("First documentation line.".encode("utf-8")),
                        call="rust_doc_comment",
                        kind="rust_doc_comment",
                    )
                ],
            },
            "Second documentation line.": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=4,
                        start=doc_two_start,
                        end=doc_two_start + len("Second documentation line.".encode("utf-8")),
                        call="rust_doc_comment",
                        kind="rust_doc_comment",
                    )
                ],
            },
        }
        translations = {
            "First documentation line.": "첫 번째 문서 줄.",
            "Second documentation line.": "두 번째 문서 줄.",
            "Use {name} literally": "{name}을 문자 그대로 사용",
            "Welcome, {name}!": "{name}님, 환영합니다!",
        }
        self._write_inputs(catalog, manifest, translations)

        first = generate_runtime_bundles(self.root, self.zed_root, self._project())
        first_bytes = {
            path.name: path.read_bytes()
            for path in sorted((self.zed_root / "assets" / "locales").glob("*.json"))
        }
        second = generate_runtime_bundles(self.root, self.zed_root, self._project())
        second_bytes = {
            path.name: path.read_bytes()
            for path in sorted((self.zed_root / "assets" / "locales").glob("*.json"))
        }

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first.catalog_sha256, second.catalog_sha256)
        expected_hash = hashlib.sha256(
            (json.dumps(catalog, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode(
                "utf-8"
            )
        ).hexdigest()
        self.assertEqual(first.catalog_sha256, expected_hash)
        index = json.loads(first_bytes["index.json"])
        bundle = json.loads(first_bytes["ko-KR.json"])
        self.assertEqual(index["source_formats"]["Welcome, {name}!"], [
            {"text": "Welcome, "},
            {"arg": "name"},
            {"text": "!"},
        ])
        self.assertNotIn("Use {name} literally", index["source_formats"])
        self.assertEqual(bundle["messages"]["Use {name} literally"], "{name}을 문자 그대로 사용")
        self.assertEqual(
            bundle["messages"]["First documentation line.\nSecond documentation line."],
            "첫 번째 문서 줄.\n두 번째 문서 줄.",
        )
        self.assertEqual(bundle["formats"]["Welcome, {name}!"], [
            {"arg": "name"},
            {"text": "님, 환영합니다!"},
        ])
        self.assertLessEqual(first.raw_payload_bytes, 12 * 1024 * 1024)

    def test_joins_paragraph_and_indented_doc_lines_like_their_consumers(self) -> None:
        source_text = (
            "/// Whether the feature is enabled.\n"
            "///\n"
            "/// Default: true\n"
            "pub struct Toggle;\n"
            '///   "auto"\n'
            "/// Values are listed.\n"
            "pub struct Values;\n"
            "actions!(zed, [\n"
            "    /// Opens the settings.\n"
            "    ///\n"
            "    ///   With extra indent.\n"
            "    OpenSettings,\n"
            "]);\n"
        )
        source_file = self.zed_root / "crates" / "sample" / "src" / "lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        entries = (
            ("Whether the feature is enabled.", 1, "rust_doc_comment"),
            ("Default: true", 3, "rust_doc_comment"),
            ('"auto"', 5, "rust_doc_comment"),
            ("Values are listed.", 6, "rust_doc_comment"),
            ("Opens the settings.", 9, "action_description"),
            ("With extra indent.", 11, "action_description"),
        )
        catalog = {source: source for source, _, _ in entries}
        manifest = {}
        offset = 0
        for source, line, kind in entries:
            start = source_text.index(source, offset)
            offset = start + len(source)
            manifest[source] = {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=line,
                        start=len(source_text[:start].encode("utf-8")),
                        end=len(source_text[:start].encode("utf-8"))
                        + len(source.encode("utf-8")),
                        call="rust_doc_comment",
                        kind=kind,
                    )
                ],
            }
        translations = {
            "Whether the feature is enabled.": "기능 활성화 여부.",
            "Default: true": "기본값: true",
            '"auto"': '"자동"',
            "Values are listed.": "값이 나열됩니다.",
            "Opens the settings.": "설정을 엽니다.",
            "With extra indent.": "추가 들여쓰기 포함.",
        }
        self._write_inputs(catalog, manifest, translations)

        report = generate_runtime_bundles(self.root, self.zed_root, self._project())
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        # schemars keeps blank doc lines as empty strings, so paragraph
        # descriptions join as "first\n\nsecond".
        self.assertEqual(
            bundle["messages"]["Whether the feature is enabled.\n\nDefault: true"],
            "기능 활성화 여부.\n\n기본값: true",
        )
        # schemars strips at most one leading space per line, so indented
        # list entries keep the remaining indentation in source and
        # translation alike.
        self.assertEqual(
            bundle["messages"]['  "auto"\nValues are listed.'],
            '  "자동"\n값이 나열됩니다.',
        )
        # derive_action trims every line before joining.
        self.assertEqual(
            bundle["messages"]["Opens the settings.\n\nWith extra indent."],
            "설정을 엽니다.\n\n추가 들여쓰기 포함.",
        )
        self.assertEqual(report.joined_message_count, 3)

    def test_rejects_indoc_literal_whose_runtime_value_cannot_be_collapsed(self) -> None:
        source_text = (
            "pub fn help() -> &'static str {\n"
            '    indoc!{"\n'
            "        First paragraph line.\n"
            "\n"
            "        Second paragraph line.\"}\n"
            "}\n"
        )
        source_file = self.zed_root / "crates" / "sample" / "src" / "lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        literal_start = source_text.index('"\n')
        literal_end = source_text.index('"}') + 1
        literal = source_text[literal_start:literal_end]
        source = literal[1:-1]
        catalog = {source: source}
        manifest = {
            source: {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=2,
                        start=len(source_text[:literal_start].encode("utf-8")),
                        end=len(source_text[:literal_end].encode("utf-8")),
                        call="Label::new",
                        kind="label",
                    )
                ],
            }
        }
        self._write_inputs(catalog, manifest, {source: "번역"})

        with self.assertRaisesRegex(ValueError, "indoc! runtime value diverges"):
            generate_runtime_bundles(self.root, self.zed_root, self._project())

    def test_rejects_translation_that_drops_a_placeholder(self) -> None:
        source_file = self.zed_root / "crates" / "sample" / "src" / "lib.rs"
        source_file.parent.mkdir(parents=True)
        prefix = "pub fn message(count: usize) -> String { format!("
        literal = '"Deleted {} files"'
        source_file.write_text(f"{prefix}{literal}, count) }}\n", encoding="utf-8")
        start = len(prefix.encode("utf-8"))
        catalog = {"Deleted {} files": "Deleted {} files"}
        manifest = {
            "Deleted {} files": {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=1,
                        start=start,
                        end=start + len(literal.encode("utf-8")),
                        call="Label::new",
                        kind="label",
                    )
                ],
            }
        }
        translations = {"Deleted {} files": "Files deleted"}
        self._write_inputs(catalog, manifest, translations)

        with self.assertRaisesRegex(ValueError, "placeholder mismatch"):
            generate_runtime_bundles(self.root, self.zed_root, self._project())

    def test_rejects_enabled_locale_without_translation_file(self) -> None:
        self._write_inputs(
            {"Open": "Open"},
            {"Open": {"status": "accepted", "occurrences": []}},
            None,
        )

        with self.assertRaisesRegex(ValueError, "enabled locale has no translation file"):
            generate_runtime_bundles(self.root, self.zed_root, self._project())

    def test_derives_one_format_plan_from_concat_literal_components(self) -> None:
        source_text = '''pub fn message(name: &str) -> Vec<String> {
    vec![format!(concat!("Hello {} ", "from ", "Zed"), name)]
}
'''
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        manifest = {}
        catalog = {}
        translations = {}
        for source, literal, translation in (
            ("Hello {} ", '"Hello {} "', "안녕하세요 {} "),
            ("from ", '"from "', "출처 "),
            ("Zed", '"Zed"', "Zed"),
        ):
            start = len(source_text[: source_text.index(literal)].encode("utf-8"))
            catalog[source] = source
            translations[source] = translation
            manifest[source] = {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=2,
                        start=start,
                        end=start + len(literal.encode("utf-8")),
                        call="format!",
                        kind="label",
                    )
                ],
            }
        self._write_inputs(catalog, manifest, translations)

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        composite = "Hello {} from Zed"
        self.assertIn(composite, index["source_formats"])
        self.assertEqual(
            bundle["formats"][composite],
            [{"text": "안녕하세요 "}, {"arg": "0"}, {"text": " 출처 Zed"}],
        )

    def test_classifies_anyhow_family_implicit_format_strings(self) -> None:
        source_text = '''pub fn validate(path: &str, limit: usize) -> anyhow::Result<()> {
    let _ = anyhow!("Invalid path {path:?}");
    anyhow::bail!("Limit is {}", limit)
}
'''
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        catalog = {
            "Invalid path {path:?}": "Invalid path {path:?}",
            "Limit is {}": "Limit is {}",
        }
        translations = {
            "Invalid path {path:?}": "잘못된 경로 {path:?}",
            "Limit is {}": "제한은 {}",
        }
        manifest = {}
        for source, literal, line in (
            ("Invalid path {path:?}", '"Invalid path {path:?}"', 2),
            ("Limit is {}", '"Limit is {}"', 3),
        ):
            start = len(source_text[: source_text.index(literal)].encode("utf-8"))
            manifest[source] = {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=line,
                        start=start,
                        end=start + len(literal.encode("utf-8")),
                        call="anyhow!",
                        kind="configuration_error",
                    )
                ],
            }
        self._write_inputs(catalog, manifest, translations)

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertIn("Invalid path {path:?}", index["source_formats"])
        self.assertIn("Limit is {}", index["source_formats"])
        self.assertEqual(
            bundle["formats"]["Invalid path {path:?}"],
            [{"text": "잘못된 경로 "}, {"arg": "path"}],
        )

    def test_maps_line_continued_catalog_keys_to_their_runtime_values(self) -> None:
        source_text = (
            'pub fn message(name: &str) -> String { format!("First \\\n        second {name}") }\n'
            'pub fn label() -> &\'static str { "Hello \\\n        world" }\n'
        )
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        format_literal = '"First \\\n        second {name}"'
        static_literal = '"Hello \\\n        world"'
        static_catalog_source = "Hello         world"
        catalog = {
            "First second {name}": "First second {name}",
            static_catalog_source: static_catalog_source,
        }
        translations = {
            "First second {name}": "{name}, 첫 번째 두 번째",
            static_catalog_source: "안녕 세상",
        }
        manifest = {}
        for source, literal, kind in (
            ("First second {name}", format_literal, "label"),
            (static_catalog_source, static_literal, "description"),
        ):
            start = len(source_text[: source_text.index(literal)].encode("utf-8"))
            manifest[source] = {
                "status": "accepted",
                "occurrences": [
                    self._occurrence(
                        line=1 if source.startswith("First") else 3,
                        start=start,
                        end=start + len(literal.encode("utf-8")),
                        call="format!" if source.startswith("First") else "label",
                        kind=kind,
                    )
                ],
            }
        self._write_inputs(catalog, manifest, translations)

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertIn("First second {name}", index["source_formats"])
        self.assertEqual(
            bundle["formats"]["First second {name}"],
            [{"arg": "name"}, {"text": ", 첫 번째 두 번째"}],
        )
        self.assertEqual(bundle["messages"]["Hello world"], "안녕 세상")

    def test_maps_a_composite_catalog_key_to_its_runtime_format(self) -> None:
        source_text = '''pub fn label(count: usize) -> String {
    format!("{} {}", count, pluralize("project rule", count))
}
'''
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        literal = '"{} {}"'
        start = len(source_text[: source_text.index(literal)].encode("utf-8"))
        occurrence = self._occurrence(
            line=2,
            start=start,
            end=start + len(literal.encode("utf-8")),
            call="Button::new",
            kind="button",
        )
        occurrence["composite_rule_id"] = "agent.project_rules_count"
        catalog_source = "{} project rules"
        self._write_inputs(
            {catalog_source: catalog_source},
            {
                catalog_source: {
                    "status": "accepted",
                    "occurrences": [occurrence],
                }
            },
            {catalog_source: "프로젝트 규칙 {}개"},
        )

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            index["source_formats"]["{} {}"],
            [{"arg": "0"}, {"text": " "}, {"arg": "1"}],
        )
        self.assertEqual(
            bundle["formats"]["{} {}"],
            [{"text": "프로젝트 규칙 "}, {"arg": "0"}, {"text": "개"}],
        )

    def test_includes_overlay_format_source_without_a_translation(self) -> None:
        source = "System Default ({language}, {locale})"
        self._write_inputs(
            {source: source},
            {
                source: {
                    "status": "accepted",
                    "occurrences": [
                        {
                            "file": "runtime-overlay/crates/settings_ui/src/locale.rs",
                            "line": 1,
                            "start_byte": 0,
                            "end_byte": len(source.encode("utf-8")),
                            "call": "localization::format_message",
                            "kind": "runtime_overlay",
                        }
                    ],
                }
            },
            {},
        )

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            index["source_formats"][source],
            [
                {"text": "System Default ("},
                {"arg": "language"},
                {"text": ", "},
                {"arg": "locale"},
                {"text": ")"},
            ],
        )
        self.assertNotIn(source, bundle["formats"])

    def test_keeps_a_source_used_by_both_static_and_format_calls_in_both_maps(self) -> None:
        source_text = '''pub fn format_label() -> String { format!("Allow") }
pub const STATIC_LABEL: &str = "Allow";
'''
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        first = source_text.index('"Allow"')
        second = source_text.index('"Allow"', first + 1)
        occurrence_length = len('"Allow"'.encode("utf-8"))
        self._write_inputs(
            {"Allow": "Allow"},
            {
                "Allow": {
                    "status": "accepted",
                    "occurrences": [
                        self._occurrence(
                            line=1,
                            start=len(source_text[:first].encode("utf-8")),
                            end=len(source_text[:first].encode("utf-8"))
                            + occurrence_length,
                            call="format!",
                            kind="permission_option",
                        ),
                        self._occurrence(
                            line=2,
                            start=len(source_text[:second].encode("utf-8")),
                            end=len(source_text[:second].encode("utf-8"))
                            + occurrence_length,
                            call="label",
                            kind="permission_option",
                        ),
                    ],
                }
            },
            {"Allow": "허용"},
        )

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertEqual(bundle["messages"]["Allow"], "허용")
        self.assertEqual(bundle["formats"]["Allow"], [{"text": "허용"}])

    def test_classifies_dynamic_thiserror_source_as_a_format(self) -> None:
        source_text = '''#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error("{} provider is not configured", .0)]
    Missing(String),
}
'''
        source_file = self.zed_root / "crates/sample/src/lib.rs"
        source_file.parent.mkdir(parents=True)
        source_file.write_text(source_text, encoding="utf-8")
        literal = '"{} provider is not configured"'
        start = len(source_text[: source_text.index(literal)].encode("utf-8"))
        source = "{} provider is not configured"
        self._write_inputs(
            {source: source},
            {
                source: {
                    "status": "accepted",
                    "occurrences": [
                        self._occurrence(
                            line=3,
                            start=start,
                            end=start + len(literal.encode("utf-8")),
                            call="configuration_error",
                            kind="configuration_error",
                        )
                    ],
                }
            },
            {source: "{} 프로바이더가 구성되지 않음"},
        )

        generate_runtime_bundles(self.root, self.zed_root, self._project())
        index = json.loads(
            (self.zed_root / "assets/locales/index.json").read_text(encoding="utf-8")
        )
        bundle = json.loads(
            (self.zed_root / "assets/locales/ko-KR.json").read_text(encoding="utf-8")
        )

        self.assertIn(source, index["source_formats"])
        self.assertEqual(
            bundle["formats"][source],
            [{"arg": "0"}, {"text": " 프로바이더가 구성되지 않음"}],
        )

    def _occurrence(
        self,
        *,
        line: int,
        start: int,
        end: int,
        call: str,
        kind: str,
    ) -> dict[str, object]:
        return {
            "file": "crates/sample/src/lib.rs",
            "line": line,
            "start_byte": start,
            "end_byte": end,
            "call": call,
            "kind": kind,
        }

    def _write_inputs(
        self,
        catalog: dict[str, str],
        manifest: dict[str, object],
        translations: dict[str, str] | None,
    ) -> None:
        self._write_json(self.root / "catalog" / "en-US.json", catalog)
        self._write_json(self.root / "manifest" / "ui-strings.json", manifest)
        config = self.root / "config" / "locales.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            """
source_locale = "en-US"

[[locale]]
id = "en-US"
english_name = "English (United States)"
native_name = "English (United States)"
aliases = ["en"]
direction = "ltr"
enabled = true

[[locale]]
id = "ko-KR"
english_name = "Korean"
native_name = "한국어"
aliases = ["ko"]
direction = "ltr"
enabled = true
""".lstrip(),
            encoding="utf-8",
        )
        if translations is not None:
            self._write_json(self.root / "translations" / "ko-KR.json", translations)

    @staticmethod
    def _project() -> ProjectConfig:
        return ProjectConfig(
            zed_version="v1.15.0",
            zed_commit="abc123",
            zed_repository="https://github.com/zed-industries/zed",
            cache_dir=Path(".cache/zed"),
        )

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
