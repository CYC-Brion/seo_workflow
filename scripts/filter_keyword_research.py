"""Apply deterministic industry exclusions to an existing keyword-research JSON file."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modules.keyword_filter.industry_rules import apply_industry_rules


def apply_filters(payload: Dict[str, Any]) -> Dict[str, Any]:
    ideas = payload.get("ideas", [])
    decisions = {
        decision.keyword: decision
        for decision in apply_industry_rules(row.get("keyword", "") for row in ideas)
    }
    for row in ideas:
        decision = decisions[row.get("keyword", "")]
        if decision.keep:
            row.update({
                "review_status": "Review",
                "filter_stage": "rule",
                "filter_reason": "passes deterministic B2B exclusion rules; requires AI/editorial review",
            })
        else:
            row.update({
                "review_status": "Exclude",
                "filter_stage": "rule",
                "filter_reason": decision.reason,
            })
    payload["industry_filter"] = {
        "mode": "deterministic rules before AI review",
        "kept_for_review": sum(1 for row in ideas if row["review_status"] == "Review"),
        "excluded": sum(1 for row in ideas if row["review_status"] == "Exclude"),
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    filtered = apply_filters(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(filtered["industry_filter"], ensure_ascii=False))


if __name__ == "__main__":
    main()
