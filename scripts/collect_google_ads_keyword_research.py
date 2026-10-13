"""Collect a reviewable keyword-research dataset without generating content.

This script only calls Google Ads Keyword Planner and writes JSON. A separate
spreadsheet builder turns that JSON into an Excel review workbook, keeping data
collection separate from workbook authoring and from the publishing workflow.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from openpyxl import load_workbook
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modules.keyword_expander import KeywordExpander
from src.modules.keyword_filter.ai_filter import AIKeywordFilter
from src.modules.keyword_filter.industry_rules import apply_industry_rules

DEFAULT_INPUT = ROOT / "keyword_library" / "seo_phase3_long_cycle.xlsx"
DEFAULT_OUTPUT = ROOT / "data" / "output" / "google_ads_keyword_research.json"

MARKETS = {
    "US": {"label": "United States", "language": "languageConstants/1000", "geo": ["geoTargetConstants/2840"]},
    "UK": {"label": "United Kingdom", "language": "languageConstants/1000", "geo": ["geoTargetConstants/2826"]},
    "CA": {"label": "Canada", "language": "languageConstants/1000", "geo": ["geoTargetConstants/2124"]},
    "AU": {"label": "Australia", "language": "languageConstants/1000", "geo": ["geoTargetConstants/2036"]},
}


def load_core_pillar_seeds(input_path: Path, limit: int) -> List[str]:
    """Read the highest-priority pillar seeds in workbook order."""
    workbook = load_workbook(input_path, read_only=True, data_only=True)
    worksheet = workbook["keywords"]
    headers = [str(cell.value or "").strip().lower() for cell in next(worksheet.iter_rows())]
    rows = [dict(zip(headers, values)) for values in worksheet.iter_rows(min_row=2, values_only=True)]
    workbook.close()

    seeds: List[str] = []
    for row in rows:
        if str(row.get("lane") or "").strip().lower() != "pillar":
            continue
        if str(row.get("priority") or "").strip().upper() != "A":
            continue
        keyword = str(row.get("keywords") or "").strip()
        if keyword and keyword.lower() not in {item.lower() for item in seeds}:
            seeds.append(keyword)
        if len(seeds) >= limit:
            break
    return seeds


def collect(
    input_path: Path,
    output_path: Path,
    seed_limit: int,
    max_ideas: int,
    market_code: str,
    use_ai_filter: bool,
) -> Dict[str, Any]:
    seeds = load_core_pillar_seeds(input_path, seed_limit)
    if not seeds:
        raise ValueError("No priority-A pillar seeds found in the input workbook.")

    market = MARKETS[market_code]
    expander = KeywordExpander(
        "google_ads_keyword_research",
        config={
            "max_expansions_per_keyword": max_ideas,
            "request_delay_seconds": 0.2,
            "enable_public_suggestions": False,
            "google_ads_language": market["language"],
            "google_ads_geo_target_constants": market["geo"],
        },
    )
    expander.execute_impl(seeds)
    metadata = list(expander.get_keyword_metadata().values())
    decisions = {decision.keyword: decision for decision in apply_industry_rules(
        row["keyword"] for row in metadata
    )}
    eligible = [
        row["keyword"] for row in metadata
        if decisions[row["keyword"]].keep
    ]
    ai_kept = set(eligible)
    ai_filter_error = ""
    if use_ai_filter and eligible:
        try:
            ai_filter = AIKeywordFilter(
                "keyword_research_industry_filter",
                config={"batch_size": 50, "confidence_threshold": 0.7, "enable_fallback": True},
            )
            ai_kept = set(ai_filter.execute_impl(eligible))
        except Exception as exc:
            ai_filter_error = str(exc)

    for row in metadata:
        decision = decisions[row["keyword"]]
        if not decision.keep:
            row.update({
                "review_status": "Exclude",
                "filter_stage": "rule",
                "filter_reason": decision.reason,
            })
        elif row["keyword"] not in ai_kept:
            row.update({
                "review_status": "Exclude",
                "filter_stage": "AI",
                "filter_reason": "outside defined B2B manufacturing scope",
            })
        else:
            row.update({
                "review_status": "Review",
                "filter_stage": "AI" if use_ai_filter else "rule",
                "filter_reason": "requires editorial review",
            })
    metadata.sort(
        key=lambda row: (
            row.get("avg_monthly_searches") is None,
            -(row.get("avg_monthly_searches") or 0),
            row["keyword"].lower(),
        )
    )
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_workbook": str(input_path),
        "target_language": "English",
        "target_location": market["label"],
        "market_code": market_code,
        "google_ads_language": market["language"],
        "google_ads_geo_target_constants": market["geo"],
        "ai_filter_error": ai_filter_error,
        "seed_keywords": seeds,
        "statistics": expander.get_statistics(),
        "ideas": metadata,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed-limit", type=int, default=20)
    parser.add_argument("--max-ideas", type=int, default=100)
    parser.add_argument("--market", choices=sorted(MARKETS), default="US")
    parser.add_argument("--skip-ai-filter", action="store_true")
    args = parser.parse_args()

    payload = collect(
        args.input.resolve(), args.output.resolve(), args.seed_limit, args.max_ideas,
        args.market, not args.skip_ai_filter,
    )
    print("Google Ads keyword research complete")
    print(f"Seeds: {len(payload['seed_keywords'])}")
    print(f"Unique ideas: {len(payload['ideas'])}")
    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
