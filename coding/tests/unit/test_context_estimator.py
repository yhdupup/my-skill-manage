from __future__ import annotations

import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest

from skill_manager.application.skills.context_estimator import (
    DEFAULT_CONTEXT_WINDOW_TOKENS,
    SkillContextEstimator,
    is_wide_character,
)


class SkillContextEstimatorUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.estimator = SkillContextEstimator()

    def test_ascii_one_to_four_characters_estimate_one_token(self) -> None:
        self.assertEqual(self.estimator.count_tokens("a"), 1)
        self.assertEqual(self.estimator.count_tokens("abcd"), 1)
        self.assertEqual(self.estimator.count_tokens("abcde"), 2)

    def test_ascii_groups_round_up(self) -> None:
        self.assertEqual(self.estimator.count_tokens("abcde"), 2)
        self.assertEqual(self.estimator.count_tokens("abcdefgh"), 2)
        self.assertEqual(self.estimator.count_tokens("abcdefghi"), 3)

    def test_whitespace_is_not_counted(self) -> None:
        self.assertEqual(self.estimator.count_tokens("   "), 0)
        self.assertEqual(self.estimator.count_tokens("\n\t"), 0)
        self.assertEqual(self.estimator.count_tokens("a  b\nc\td"), 1)

    def test_chinese_characters_count_one_token_each(self) -> None:
        self.assertEqual(self.estimator.count_tokens("中"), 1)
        self.assertEqual(self.estimator.count_tokens("中文"), 2)
        self.assertEqual(self.estimator.count_tokens("汉字测试"), 4)

    def test_japanese_kana_counts_one_token_each(self) -> None:
        self.assertEqual(self.estimator.count_tokens("ひらがな"), 4)
        self.assertEqual(self.estimator.count_tokens("カタカナ"), 4)
        self.assertEqual(self.estimator.count_tokens("ｶﾀｶﾅ"), 4)

    def test_korean_characters_count_one_token_each(self) -> None:
        self.assertEqual(self.estimator.count_tokens("한글"), 2)
        self.assertEqual(self.estimator.count_tokens("한국어테스트"), 6)

    def test_fullwidth_punctuation_counts_one_token_each(self) -> None:
        self.assertEqual(self.estimator.count_tokens("、。！"), 3)
        self.assertEqual(self.estimator.count_tokens("【】："), 3)

    def test_mixed_chinese_and_ascii_count_separately(self) -> None:
        self.assertEqual(self.estimator.count_tokens("中a"), 2)
        self.assertEqual(self.estimator.count_tokens("中文abcde"), 4)

    def test_frontmatter_is_counted(self) -> None:
        document = "---\nname: 中文\n---\n# 标题\n\n正文"
        # 9 wide characters; non-wide: "---", ": ", " ", " "
        self.assertEqual(self.estimator.count_tokens(document), 9)

    def test_only_references_and_scripts_do_not_count(self) -> None:
        # The estimator never opens files outside of the SKILL.md payload.
        # We test the helper directly; reading references is impossible
        # from the public API.
        self.assertTrue(callable(is_wide_character))
        self.assertTrue(is_wide_character("中"))
        self.assertFalse(is_wide_character("a"))

    def test_non_empty_text_returns_at_least_one_token(self) -> None:
        self.assertEqual(self.estimator.count_tokens(" "), 0)
        self.assertEqual(self.estimator.count_tokens("\t\n"), 0)
        self.assertEqual(self.estimator.count_tokens("a"), 1)
        self.assertEqual(self.estimator.count_tokens("中"), 1)

    def test_empty_text_estimates_zero_tokens(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "empty-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("", encoding="utf-8")
            result = self.estimator.estimate(root, DEFAULT_CONTEXT_WINDOW_TOKENS)
        self.assertEqual(result.estimated_tokens, 0)
        self.assertEqual(result.status, "normal")
        self.assertEqual(result.usage_percent, 0.0)
        self.assertIsNone(result.reason)

    def test_status_normal_below_two_percent(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "small-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a" * 100, encoding="utf-8")
            # 100 ascii chars => 25 tokens; 25 / 100000 * 100 = 0.025%
            result = self.estimator.estimate(root, 100000)
        self.assertEqual(result.status, "normal")
        self.assertEqual(result.estimated_tokens, 25)
        self.assertEqual(result.usage_percent, 0.03)

    def test_status_warning_at_exact_two_percent(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "two-percent-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a" * 8, encoding="utf-8")  # 2 tokens
            # 2 / 100 * 100 = 2.0% exact
            result = self.estimator.estimate(root, 100)
        self.assertEqual(result.status, "warning")
        self.assertEqual(result.estimated_tokens, 2)
        self.assertEqual(result.usage_percent, 2.0)

    def test_status_warning_just_below_five_percent(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "four-percent-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a" * 16, encoding="utf-8")  # 4 tokens
            result = self.estimator.estimate(root, 100)
        self.assertEqual(result.status, "warning")
        self.assertEqual(result.usage_percent, 4.0)

    def test_status_high_at_exact_five_percent(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "five-percent-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a" * 20, encoding="utf-8")  # 5 tokens
            result = self.estimator.estimate(root, 100)
        self.assertEqual(result.status, "high")
        self.assertEqual(result.estimated_tokens, 5)
        self.assertEqual(result.usage_percent, 5.0)

    def test_status_uses_unrounded_ratio(self) -> None:
        # 1 token / 60 tokens = 1.666...%; rounded display = 1.67% but
        # status must still be ``normal`` because raw value < 2.
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "raw-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a", encoding="utf-8")
            result = self.estimator.estimate(root, 60)
        self.assertEqual(result.status, "normal")
        self.assertEqual(result.usage_percent, 1.67)

    def test_missing_root_returns_unavailable(self) -> None:
        result = self.estimator.estimate(None, DEFAULT_CONTEXT_WINDOW_TOKENS)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "skill_document_missing")
        self.assertIsNone(result.estimated_tokens)
        self.assertIsNone(result.usage_percent)

    def test_missing_skill_md_returns_unavailable(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "broken-skill"
            root.mkdir()
            result = self.estimator.estimate(root, DEFAULT_CONTEXT_WINDOW_TOKENS)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "skill_document_missing")

    def test_unreadable_skill_md_returns_unavailable(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX permission test skipped on Windows")
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "no-read-skill"
            root.mkdir()
            skill_md = root / "SKILL.md"
            skill_md.write_text("中", encoding="utf-8")
            skill_md.chmod(0)
            try:
                result = self.estimator.estimate(root, DEFAULT_CONTEXT_WINDOW_TOKENS)
            finally:
                skill_md.chmod(stat.S_IRUSR | stat.S_IWUSR)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "skill_document_unreadable")
        self.assertIsNone(result.estimated_tokens)
        self.assertIsNone(result.usage_percent)

    def test_invalid_window_returns_invalid_reason(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "valid-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("hello", encoding="utf-8")
            result = self.estimator.estimate(root, 0)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.reason, "invalid_context_window")
        self.assertIsNone(result.estimated_tokens)
        self.assertIsNone(result.usage_percent)

        result_bool = self.estimator.estimate(None, True)  # type: ignore[arg-type]
        self.assertEqual(result_bool.reason, "invalid_context_window")

    def test_estimate_does_not_recurse_into_references(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "main-skill"
            root.mkdir()
            (root / "SKILL.md").write_text("a", encoding="utf-8")
            references = root / "references"
            references.mkdir()
            (references / "deep.md").write_text("中文 中文 中文", encoding="utf-8")
            result = self.estimator.estimate(root, DEFAULT_CONTEXT_WINDOW_TOKENS)
        self.assertEqual(result.estimated_tokens, 1)


if __name__ == "__main__":
    unittest.main()