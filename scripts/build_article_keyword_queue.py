"""Turn an AI-reviewed Google Ads research export into a ready-to-run SEO queue.

The queue is deliberately conservative: it retains only B2B-relevant, measured
US keywords, removes topics already used in prior workflow results, and keeps
one representative per near-duplicate intent cluster.  It does not call AI,
Google Ads, or WordPress.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_RESEARCH = ROOT / "data" / "output" / "google_ads_keyword_research_us_filtered.json"
DEFAULT_OUTPUT = ROOT / "data" / "output" / "article_keyword_queue_us.json"

EXCLUDED_PATTERNS = re.compile(
    r"\b(?:machine|kit|repair|replacement|near me|solar|night light|outdoor|audit|assessment|verification)\b",
    re.IGNORECASE,
)


def historical_keywords() -> set[str]:
    """Return exact keywords previously accepted by the workflow."""
    seen: set[str] = set()
    for path in (ROOT / "output").glob("workflow_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        steps = payload.get("steps", {})
        for value in steps.get("3_filtered_keywords", {}).get("data", []):
            keyword = str(value or "").strip().lower()
            if keyword:
                seen.add(keyword)
    return seen


def topic_cluster(keyword: str) -> str:
    """Group variants so one article does not cannibalize another."""
    value = keyword.lower()
    if "lamp parts" in value:
        return "lamp-parts-supply"
    if "fixture" in value:
        return "fixture-parts-supply"
    if "chandelier" in value:
        return "chandelier-parts"
    if "led" in value and ("component" in value or "part" in value or "accessor" in value):
        return "led-components"
    if "bulb holder" in value:
        return "bulb-holders"
    if "lighting component" in value:
        return "lighting-components"
    cleaned = re.sub(r"\b(?:manufacturer|manufacturers|supplier|suppliers|supply|supplies|wholesale)\b", "", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def commercial_fit(keyword: str) -> int:
    value = keyword.lower()
    score = 0
    if re.search(r"\b(?:lamp|lighting|light fixture|chandelier|bulb holder)\b", value):
        score += 35
    if re.search(r"\b(?:manufacturer|supplier|suppliers|wholesale)\b", value):
        score += 25
    if re.search(r"\b(?:custom|oem|odm)\b", value):
        score += 15
    if "audit" in value:
        score += 8
    return score


def score(row: dict[str, Any]) -> int:
    volume = max(0, int(row.get("avg_monthly_searches") or 0))
    volume_points = min(40, round(math.log10(volume + 1) * 14))
    competition_points = {"LOW": 15, "MEDIUM": 10, "HIGH": 6}.get(
        str(row.get("competition") or "").upper(), 4
    )
    high_bid = int(row.get("high_top_of_page_bid_micros") or 0)
    bid_points = min(15, round(math.log10(high_bid / 1_000_000 + 1) * 8))
    return volume_points + competition_points + bid_points + commercial_fit(row["keyword"])


def direction_for(keyword: str) -> str:
    value = keyword.lower()
    if "audit" in value:
        return "supplier evaluation, quality verification, and factory audit evidence"
    if "supplier" in value or "manufacturer" in value or "wholesale" in value:
        return "B2B sourcing, supplier evaluation, specifications, and factory verification"
    return "component fit, technical specifications, manufacturing quality checks, and sourcing guidance"


def build_queue(research: dict[str, Any], limit: int) -> dict[str, Any]:
    historical = historical_keywords()
    staged: list[dict[str, Any]] = []
    for source in research.get("ideas", []):
        keyword = str(source.get("keyword") or "").strip()
        if not keyword or source.get("review_status") != "Review":
            continue
        if keyword.lower() in historical or EXCLUDED_PATTERNS.search(keyword):
            continue
        if int(source.get("avg_monthly_searches") or 0) < 10:
            continue
        candidate = dict(source)
        candidate["topic_cluster"] = topic_cluster(keyword)
        candidate["priority_score"] = score(candidate)
        staged.append(candidate)

    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in staged:
        by_cluster[candidate["topic_cluster"]].append(candidate)

    selected = [
        sorted(
            candidates,
            key=lambda row: (-row["priority_score"], -(row.get("avg_monthly_searches") or 0), row["keyword"].lower()),
        )[0]
        for candidates in by_cluster.values()
    ]
    selected.sort(key=lambda row: (-row["priority_score"], -(row.get("avg_monthly_searches") or 0), row["keyword"].lower()))

    queue = []
    for index, row in enumerate(selected[:limit], start=1):
        queue.append({
            "sequence": index,
            "keyword": row["keyword"],
            "category": "Technical Guides" if "audit" not in row["keyword"].lower() else "Industry Insights",
            "lane": "ordinary",
            "priority": "A" if index <= 8 else "B",
            "cluster": row["topic_cluster"],
            "direction": direction_for(row["keyword"]),
            "internal_link_targets": "Home; Services; Contact",
            "avg_monthly_searches": row.get("avg_monthly_searches"),
            "competition": row.get("competition"),
            "high_top_of_page_bid_micros": row.get("high_top_of_page_bid_micros"),
            "priority_score": row["priority_score"],
            "selection_reason": "AI/rule-approved; measured Google Ads demand; B2B fit; no exact historical workflow match; one representative per topic cluster",
            "workflow_status": "Ready for SEO workflow",
        })
    return {
        "source_research": str(DEFAULT_RESEARCH),
        "market": research.get("target_location"),
        "selection_rules": {
            "minimum_monthly_searches": 10,
            "historical_duplicate_check": "exact keyword match against prior workflow results",
            "topic_deduplication": "one best keyword per intent cluster",
            "excluded_patterns": EXCLUDED_PATTERNS.pattern,
        },
        "statistics": {
            "source_ideas": len(research.get("ideas", [])),
            "review_approved": sum(1 for row in research.get("ideas", []) if row.get("review_status") == "Review"),
            "after_rules": len(staged),
            "unique_topic_clusters": len(selected),
            "selected_for_queue": len(queue),
        },
        "queue": queue,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    research = json.loads(args.research.read_text(encoding="utf-8"))
    payload = build_queue(research, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["statistics"], ensure_ascii=False))
    for row in payload["queue"]:
        print(f"{row['sequence']:>2}. {row['keyword']} ({row['avg_monthly_searches']}/mo, score {row['priority_score']})")


if __name__ == "__main__":
    main()
