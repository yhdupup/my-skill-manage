from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from math import ceil
from pathlib import Path
import unicodedata

from skill_manager.errors import MutationError
from skill_manager.harness.support_store import DEFAULT_CONTEXT_WINDOW_TOKENS


__all__ = [
    "CONTEXT_USAGE_STATUS_HIGH",
    "CONTEXT_USAGE_STATUS_NORMAL",
    "CONTEXT_USAGE_STATUS_UNAVAILABLE",
    "CONTEXT_USAGE_STATUS_WARNING",
    "SkillContextEstimator",
    "SkillContextUsage",
]

CONTEXT_USAGE_STATUS_NORMAL = "normal"
CONTEXT_USAGE_STATUS_WARNING = "warning"
CONTEXT_USAGE_STATUS_HIGH = "high"
CONTEXT_USAGE_STATUS_UNAVAILABLE = "unavailable"

_REASON_DOCUMENT_MISSING = "skill_document_missing"
_REASON_DOCUMENT_UNREADABLE = "skill_document_unreadable"
_REASON_INVALID_WINDOW = "invalid_context_window"

_SKILL_DOCUMENT_NAME = "SKILL.md"


@dataclass(frozen=True)
class SkillContextUsage:
    """Result returned by the local context estimator."""

    estimated_tokens: int | None
    context_window_tokens: int
    usage_percent: float | None
    status: str
    reason: str | None

    def to_payload(self) -> dict[str, object]:
        return {
            "estimatedTokens": self.estimated_tokens,
            "contextWindowTokens": self.context_window_tokens,
            "usagePercent": self.usage_percent,
            "status": self.status,
            "reason": self.reason,
        }


class SkillContextEstimator:
    """Local, deterministic estimator for Skill 文档 size in tokens.

    Only reads each Skill's root ``SKILL.md``. Walks the document code point
    by code point, applies the agreed product rule and decides a status
    bucket. Every public method is pure and side-effect free so it can be
    exercised from unit tests without disk fixtures.
    """

    def __init__(self, *, default_window_tokens: int = DEFAULT_CONTEXT_WINDOW_TOKENS) -> None:
        self._default_window_tokens = default_window_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def estimate(
        self,
        skill_root: Path | None,
        context_window_tokens: int,
    ) -> SkillContextUsage:
        """Estimate context usage for the skill rooted at ``skill_root``.

        ``skill_root`` is expected to be a directory containing the canonical
        ``SKILL.md``. The estimator never recurses into ``references`` or
        reads attached scripts.
        """

        if not isinstance(context_window_tokens, int) or isinstance(context_window_tokens, bool):
            return SkillContextUsage(
                estimated_tokens=None,
                context_window_tokens=context_window_tokens,
                usage_percent=None,
                status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
                reason=_REASON_INVALID_WINDOW,
            )
        if context_window_tokens <= 0:
            return SkillContextUsage(
                estimated_tokens=None,
                context_window_tokens=context_window_tokens,
                usage_percent=None,
                status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
                reason=_REASON_INVALID_WINDOW,
            )

        if skill_root is None or not skill_root.exists() or not skill_root.is_dir():
            return SkillContextUsage(
                estimated_tokens=None,
                context_window_tokens=context_window_tokens,
                usage_percent=None,
                status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
                reason=_REASON_DOCUMENT_MISSING,
            )

        document_path = skill_root / _SKILL_DOCUMENT_NAME
        if not document_path.is_file():
            return SkillContextUsage(
                estimated_tokens=None,
                context_window_tokens=context_window_tokens,
                usage_percent=None,
                status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
                reason=_REASON_DOCUMENT_MISSING,
            )

        try:
            document = document_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return SkillContextUsage(
                estimated_tokens=None,
                context_window_tokens=context_window_tokens,
                usage_percent=None,
                status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
                reason=_REASON_DOCUMENT_UNREADABLE,
            )

        estimated_tokens = self._count_tokens(document)
        raw_percent = estimated_tokens / context_window_tokens * 100
        status = _classify_status(raw_percent)
        return SkillContextUsage(
            estimated_tokens=estimated_tokens,
            context_window_tokens=context_window_tokens,
            usage_percent=_round_percent(raw_percent),
            status=status,
            reason=None,
        )

    def estimate_unavailable(self, context_window_tokens: int) -> SkillContextUsage:
        """Return an :class:`unavailable` result with the given window token count."""

        return SkillContextUsage(
            estimated_tokens=None,
            context_window_tokens=context_window_tokens,
            usage_percent=None,
            status=CONTEXT_USAGE_STATUS_UNAVAILABLE,
            reason=_REASON_DOCUMENT_MISSING,
        )

    # ------------------------------------------------------------------
    # Pure helpers (also used by tests directly)
    # ------------------------------------------------------------------
    def count_tokens(self, text: str) -> int:
        """Count tokens for ``text`` using the deterministic estimator rule."""

        return self._count_tokens(text)

    @staticmethod
    def _count_tokens(text: str) -> int:
        wide_count = 0
        other_count = 0
        for char in text:
            if char.isspace():
                continue
            if _is_wide_character(char):
                wide_count += 1
            else:
                other_count += 1

        tokens = wide_count + ceil(other_count / 4)
        # An empty SKILL.md has neither wide nor other glyphs; it counts as
        # 0 tokens. Anything that contains at least one counted character
        # (i.e. a wide glyph or at least one non-whitespace byte) yields a
        # minimum of 1 token so consumers never see a zero estimate.
        if tokens == 0 and (wide_count or other_count):
            return 1
        return tokens


def is_wide_character(char: str) -> bool:
    return _is_wide_character(char)


def _is_wide_character(char: str) -> bool:
    if not char:
        return False
    category = unicodedata.category(char)
    if category.startswith("Lo"):
        # Letter, other. CJK unified ideographs, kana, hangul syllables and
        # extensions all fall under Lo and we treat every Lo glyph as wide.
        return True
    if category.startswith("P") or category.startswith("S") or category.startswith("Z"):
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in {"W", "F"}:
            return True
        # Hangul Jamo (initial/final vowels & consonants) live under Lo too,
        # already covered above. Hangul compatibility jamo sits in ``Lo`` as
        # well but some compatibility punctuation sits in ``So``; treat them
        # as wide for compatibility.
        if category == "Lo":
            return True
    return False


def _classify_status(raw_percent: float) -> str:
    if raw_percent < 2:
        return CONTEXT_USAGE_STATUS_NORMAL
    if raw_percent < 5:
        return CONTEXT_USAGE_STATUS_WARNING
    return CONTEXT_USAGE_STATUS_HIGH


def _round_percent(raw_percent: float) -> float:
    decimal_value = Decimal(str(raw_percent)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(decimal_value)


def resolve_default_window_tokens() -> int:
    return DEFAULT_CONTEXT_WINDOW_TOKENS


def assert_supported_status(status: str) -> str:
    if status not in {
        CONTEXT_USAGE_STATUS_NORMAL,
        CONTEXT_USAGE_STATUS_WARNING,
        CONTEXT_USAGE_STATUS_HIGH,
        CONTEXT_USAGE_STATUS_UNAVAILABLE,
    }:
        raise MutationError(f"unsupported context usage status: {status}", status=500)
    return status