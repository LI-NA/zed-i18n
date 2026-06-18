import unittest

from tools.zed_i18n.translation_checks import protected_tokens_match


class TranslationChecksTests(unittest.TestCase):
    def test_allows_translating_regular_slash_phrases(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                "Allows to enable/disable formatting with Prettier",
                "Prettier를 통한 포맷팅을 활성화하거나 비활성화할 수 있습니다.",
            )
        )
        self.assertTrue(
            protected_tokens_match(
                "Choose light/dark modes.",
                "밝게/어둡게 모드를 선택합니다.",
            )
        )

    def test_allows_translating_eg_examples(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                "Displays file size in binary units (e.g., KiB, MiB).",
                "파일 크기를 이진 단위로 표시합니다(예: KiB, MiB).",
            )
        )

    def test_accepts_protected_tokens_with_korean_suffixes(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                "Edit in settings.json",
                "settings.json에서 편집",
            )
        )
        self.assertTrue(
            protected_tokens_match(
                "Contact billing-support@zed.dev.",
                "billing-support@zed.dev로 문의하세요.",
            )
        )

    def test_reports_missing_essential_tokens(self) -> None:
        self.assertFalse(
            protected_tokens_match(
                "Open `settings.json`",
                "settings.json 열기",
            )
        )
        self.assertFalse(
            protected_tokens_match(
                "Read ~/.config/zed/settings.json",
                "Zed 설정을 읽습니다",
            )
        )

    def test_accepts_globs_after_translated_punctuation(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                "Exclude: vendor/*, *.lock",
                "排除：vendor/*, *.lock",
            )
        )
        self.assertTrue(
            protected_tokens_match(
                "Include: crates/**/*.toml",
                "包含：crates/**/*.toml",
            )
        )

    def test_ignores_sentence_punctuation_after_paths(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                "Adds a file to the repository's .git/info/exclude.",
                "저장소의 .git/info/exclude에 파일을 추가합니다.",
            )
        )

    def test_ignores_plain_words_accidentally_wrapped_in_backticks(self) -> None:
        self.assertTrue(
            protected_tokens_match(
                'example, "editor::Cancel"` or `"workspace::CloseActiveItem"`.',
                '예: "editor::Cancel"` 또는 `"workspace::CloseActiveItem"`.',
            )
        )


if __name__ == "__main__":
    unittest.main()
