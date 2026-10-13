"""Schedule existing WordPress drafts at a fixed hourly interval."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modules.wordpress_integration.wp_api_client import get_wordpress_client
from src.utils import config_manager


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_ids", nargs="+", type=int)
    parser.add_argument("--first-delay-hours", type=float, default=1)
    parser.add_argument("--interval-hours", type=float, default=1)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    config_manager.load_all_configs()
    client = get_wordpress_client("rest")
    if not client.test_connection():
        raise RuntimeError("WordPress connection test failed")

    first_slot = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=args.first_delay_hours)
    receipt = []
    for index, post_id in enumerate(args.post_ids):
        slot = first_slot + timedelta(hours=index * args.interval_hours)
        result = client.update_post(post_id, {"status": "future", "date": slot.isoformat()})
        receipt.append({
            "post_id": post_id,
            "status": result.get("status"),
            "title": result.get("title", {}).get("rendered", ""),
            "scheduled_utc": slot.isoformat(),
            "link": result.get("link", ""),
        })
        print(f"{post_id}: {slot.isoformat()} -> {result.get('status')}")

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
