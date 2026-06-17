import unittest

from tools.zed_i18n.validate import validate_translations


class ValidateTests(unittest.TestCase):
    def test_reports_missing_accepted_translation(self) -> None:
        manifest = {
            "Open Settings": {"status": "accepted", "occurrences": []},
            "Save All": {"status": "needs_review", "occurrences": []},
        }

        report = validate_translations(manifest, {})

        self.assertEqual(report.missing, ["Open Settings"])
        self.assertEqual(report.placeholder_mismatches, [])
        self.assertEqual(report.extra, [])

    def test_reports_placeholder_mismatch(self) -> None:
        manifest = {
            "Updated to {app_name} {}": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "Updated to {app_name} {}": "{app_name} 버전으로 업데이트됨",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.missing, [])
        self.assertEqual(report.placeholder_mismatches, ["Updated to {app_name} {}"])
        self.assertEqual(report.protected_token_mismatches, [])
        self.assertEqual(report.extra, [])

    def test_allows_named_placeholders_to_move_around_implicit_placeholders(self) -> None:
        manifest = {
            "{message_start} the following {} files?\n{}{unsaved_warning}": {
                "status": "accepted",
                "occurrences": [],
            },
        }
        translations = {
            "{message_start} the following {} files?\n{}{unsaved_warning}": (
                "다음 {}개 파일을 {message_start}하시겠습니까?\n{}{unsaved_warning}"
            ),
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.placeholder_mismatches, [])

    def test_reports_implicit_placeholder_order_mismatch(self) -> None:
        manifest = {
            "Move {} to {:?}": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "Move {} to {:?}": "{:?} 위치로 {} 이동",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.placeholder_mismatches, ["Move {} to {:?}"])

    def test_allows_zero_precision_placeholder_for_known_plural_suffix(self) -> None:
        manifest = {
            "Show {} warning{}": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "Show {} warning{}": "{} 件の警告を表示{:.0}",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.placeholder_mismatches, [])

    def test_reports_protected_token_mismatches(self) -> None:
        manifest = {
            "Open `settings.json`": {"status": "accepted", "occurrences": []},
            "See https://zed.dev/docs": {"status": "accepted", "occurrences": []},
            "Use \\n in the replacement": {"status": "accepted", "occurrences": []},
            "Set session.restore_unsaved_buffers": {"status": "accepted", "occurrences": []},
            "Read ~/.config/zed/settings.json": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "Open `settings.json`": "settings.json 열기",
            "See https://zed.dev/docs": "문서를 확인하세요",
            "Use \\n in the replacement": "치환에 줄바꿈을 사용합니다",
            "Set session.restore_unsaved_buffers": "저장되지 않은 버퍼 복원을 설정합니다",
            "Read ~/.config/zed/settings.json": "Zed 설정을 읽습니다",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.missing, [])
        self.assertEqual(report.placeholder_mismatches, [])
        self.assertEqual(
            report.protected_token_mismatches,
            [
                "Open `settings.json`",
                "See https://zed.dev/docs",
                "Use \\n in the replacement",
                "Set session.restore_unsaved_buffers",
                "Read ~/.config/zed/settings.json",
            ],
        )
        self.assertEqual(report.extra, [])

    def test_reports_code_like_word_and_glob_mismatches(self) -> None:
        manifest = {
            "Supports parallel_tool_calls": {"status": "accepted", "occurrences": []},
            "Include: crates/**/*.toml": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "Supports parallel_tool_calls": "병렬 도구 호출 지원",
            "Include: crates/**/*.toml": "포함: 크레이트/**/*.toml",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.missing, [])
        self.assertEqual(report.placeholder_mismatches, [])
        self.assertEqual(
            report.protected_token_mismatches,
            [
                "Supports parallel_tool_calls",
                "Include: crates/**/*.toml",
            ],
        )
        self.assertEqual(report.extra, [])

    def test_allows_edge_space_differences(self) -> None:
        manifest = {
            "A file or folder with name {} ": {"status": "accepted", "occurrences": []},
            " matching “`{}`”": {"status": "accepted", "occurrences": []},
        }
        translations = {
            "A file or folder with name {} ": "{} 이름의 파일이나 폴더가",
            " matching “`{}`”": "“`{}`”에 일치하는 항목",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.protected_token_mismatches, [])

    def test_reports_extra_translations_not_accepted_by_manifest(self) -> None:
        manifest = {
            "Open Settings": {"status": "accepted", "occurrences": []},
            "Save All": {"status": "needs_review", "occurrences": []},
        }
        translations = {
            "Open Settings": "설정 열기",
            "Save All": "모두 저장",
            "Removed": "제거됨",
        }

        report = validate_translations(manifest, translations)

        self.assertEqual(report.missing, [])
        self.assertEqual(report.placeholder_mismatches, [])
        self.assertEqual(report.extra, ["Removed", "Save All"])


if __name__ == "__main__":
    unittest.main()
