"""Deterministic relevance rules for Yusheng's B2B keyword research."""

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class KeywordRuleDecision:
    keyword: str
    keep: bool
    reason: Optional[str] = None


# These terms are deliberately scoped to clear false-positive verticals or
# consumer/local purchase intent. Ambiguous lighting and hardware terms remain
# for the AI B2B relevance review instead of being discarded here.
EXCLUSION_RULES = {
    "automotive lighting": (
        r"\bautomotive\b", r"\bcar\b", r"\btruck\b", r"\bvehicle\b",
        r"\bmotorcycle\b", r"\bheadlights?\b", r"\btail\s*lights?\b",
        r"\blight\s*bar\b", r"\bwiring\s*harness\b", r"\brestoration\b",
    ),
    "retail or local purchase intent": (
        r"\bnear\s+me\b", r"\b(store|shop|retail)\b", r"\bamazon\b",
        r"\bwalmart\b", r"\bhome\s+depot\b", r"\bbest\s+buy\b",
    ),
    "consumer repair or replacement intent": (
        r"\bhow\s+to\s+(repair|replace|fix)\b", r"\brepair\s+kit\b",
    ),
}


def classify_keyword(keyword: str) -> KeywordRuleDecision:
    """Exclude only unambiguous off-topic terms; leave grey areas for AI review."""
    normalized = " ".join(str(keyword).lower().split())
    for reason, patterns in EXCLUSION_RULES.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            return KeywordRuleDecision(keyword=str(keyword), keep=False, reason=reason)
    return KeywordRuleDecision(keyword=str(keyword), keep=True)


def apply_industry_rules(keywords: Iterable[str]) -> List[KeywordRuleDecision]:
    return [classify_keyword(keyword) for keyword in keywords]
