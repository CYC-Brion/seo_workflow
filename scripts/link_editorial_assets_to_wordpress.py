"""把 catalog 里的图库资产关联到 WordPress 媒体库已存在的条目。

**这个脚本只读 WordPress，永远不上传。** 它只调 `GET /wp-json/wp/v2/media`，
然后把匹配结果写回 `pic/editorial_library/editorial_assets.json`。

默认 dry-run：只打印报告，不改文件。加 `--apply` 才落盘。

用法：

    python scripts/link_editorial_assets_to_wordpress.py            # 看报告
    python scripts/link_editorial_assets_to_wordpress.py --apply    # 写回 catalog
    python scripts/link_editorial_assets_to_wordpress.py --verify   # 复查已记的 id 是否还在

匹配规则本身在 src/enhanced_features/image_integration/wordpress_media_matcher.py，
本文件只负责取数、报告、落盘。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.enhanced_features.image_integration.wordpress_media_matcher import (  # noqa: E402
    MatchReport,
    match_assets,
    reference_from_item,
)


CATALOG_PATH = PROJECT_ROOT / "pic" / "editorial_library" / "editorial_assets.json"

#: 2026-10-13 实测值。漂移即非零退出 —— 宁可响亮失败，也不要悄悄写坏 catalog。
EXPECTED_COUNTS = {
    "matched": 82,
    "ambiguous": 2,
    "rejected_generic": 30,
    "unmatched": 165,
}
EXPECTED_BY_RULE = {"A": 53, "C": 25, "D": 4}

#: catalog 的合法版本。出现别的版本说明有另一个写者改了格式，先停下来看。
ACCEPTED_LIBRARY_VERSIONS = {"3.0", "3.1"}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 catalog 资产关联到 WordPress 媒体库已有条目（只读 WP，不上传）"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="把匹配结果写回 catalog；不加则只打印报告",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="逐个 GET /media/<id> 复查 catalog 里已记的引用是否还有效",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_PATH,
        help=f"catalog 路径（默认 {CATALOG_PATH}）",
    )
    parser.add_argument(
        "--no-drift-check",
        action="store_true",
        help="跳过 82/2/30/165 与 A53 C25 D4 的漂移断言（只在确实改过图库时用）",
    )
    parser.add_argument(
        "--list-unmatched",
        action="store_true",
        help="打印完整的未匹配清单（默认只打印前 20 条）",
    )
    return parser.parse_args(argv)


def load_catalog(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"catalog 不存在：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    version = str(data.get("library_version", ""))
    if version not in ACCEPTED_LIBRARY_VERSIONS:
        raise SystemExit(
            f"catalog library_version={version!r}，本脚本只认识 "
            f"{sorted(ACCEPTED_LIBRARY_VERSIONS)}。先确认格式没被别的写者改过。"
        )
    if not isinstance(data.get("assets"), list):
        raise SystemExit("catalog 里没有 assets 数组")
    return data


def fetch_media_items() -> List[Dict[str, Any]]:
    """拉取 WP 媒体库全部图片条目。纯 GET。"""
    from src.modules.wordpress_integration.wp_api_client import get_wordpress_client

    client = get_wordpress_client(api_type="rest")
    if not hasattr(client, "list_media"):
        raise SystemExit("当前客户端不支持读取媒体库，linker 需要 REST 客户端")

    items = client.list_media(per_page=100, max_items=0)
    if not items:
        raise SystemExit("媒体库返回 0 条 —— 配置或权限有问题，先别往下走")
    return items


def build_report(data: Dict[str, Any], items: List[Dict[str, Any]]) -> MatchReport:
    return match_assets(data["assets"], items)


def check_drift(report: MatchReport) -> List[str]:
    """比对实测值与预期值，返回所有不一致的描述。"""
    summary = report.summary()
    problems: List[str] = []

    for key, expected in EXPECTED_COUNTS.items():
        actual = summary.get(key, 0)
        if actual != expected:
            problems.append(f"{key}: 预期 {expected}，实测 {actual}")

    by_rule = summary.get("by_rule", {})
    for rule, expected in EXPECTED_BY_RULE.items():
        actual = by_rule.get(rule, 0)
        if actual != expected:
            problems.append(f"规则 {rule}: 预期 {expected}，实测 {actual}")

    return problems


def print_report(
    report: MatchReport, verbose_unmatched: bool, drift: List[str]
) -> None:
    summary = report.summary()
    print("=" * 72)
    print("图库 → WordPress 媒体库 匹配报告")
    print("=" * 72)
    print(
        f"匹配 {summary['matched']} / 歧义 {summary['ambiguous']} / "
        f"纯数字名排除 {summary['rejected_generic']} / 未匹配 {summary['unmatched']}"
    )
    print(f"按规则：A(webp 同名) {summary['by_rule'].get('A', 0)}  "
          f"C(媒体 ID) {summary['by_rule'].get('C', 0)}  "
          f"D(原名+宽高比) {summary['by_rule'].get('D', 0)}")

    mismatches = [o for o in report.matched if o.dimension_check == "mismatch"]
    if mismatches:
        print(f"\n⚠ 尺寸对不上的匹配 {len(mismatches)} 条：")
        for outcome in mismatches[:20]:
            print(f"  - {outcome.file}")

    ambiguous = report.by_status("ambiguous")
    if ambiguous:
        print(f"\n歧义 {len(ambiguous)} 条（同名或归一化名有多个候选，按设计不匹配）：")
        for outcome in ambiguous:
            print(f"  - {outcome.file}  {outcome.detail}")

    unmatched = report.by_status("unmatched") + report.by_status("rejected_generic")
    if unmatched:
        limit = len(unmatched) if verbose_unmatched else 20
        print(f"\n未关联 WP 的资产 {len(unmatched)} 条：")
        for outcome in unmatched[:limit]:
            suffix = f"  [{outcome.detail}]" if outcome.detail else ""
            print(f"  - {outcome.file}{suffix}")
        if limit < len(unmatched):
            print(f"  …… 其余 {len(unmatched) - limit} 条用 --list-unmatched 查看")

    if drift:
        print("\n" + "!" * 72)
        print("漂移检测未通过：")
        for problem in drift:
            print(f"  - {problem}")
        print("!" * 72)
    else:
        print("\n漂移检测通过（82/2/30/165，A53 C25 D4）")
    print()


def load_verified_at_map(data: Dict[str, Any]) -> Dict[str, str]:
    """记录每条资产已有的 verified_at，用于保持重复运行幂等。"""
    result: Dict[str, str] = {}
    for asset in data["assets"]:
        reference = asset.get("wordpress_media") or {}
        verified_at = reference.get("verified_at")
        media_id = reference.get("id")
        if verified_at and media_id is not None:
            result[str(asset.get("file", ""))] = f"{media_id}:{verified_at}"
    return result


def _without_timestamp(index: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in index.items() if k != "generated_at"}


def apply_to_catalog(
    data: Dict[str, Any], report: MatchReport, catalog_path: Path
) -> Dict[str, int]:
    """把匹配结果写回 catalog。返回统计数字。

    只做两件事：给每个资产加/更新 `wordpress_media`，给顶层加
    `wordpress_media_index`。已有 key 顺序不动，资产里新键追加在末尾，
    所以 diff 是纯新增。
    """
    previous = load_verified_at_map(data)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    outcome_by_file = {o.file: o for o in report.outcomes}
    reference_count = 0

    for asset in data["assets"]:
        outcome = outcome_by_file.get(str(asset.get("file", "")))
        if outcome is None or outcome.status != "matched" or outcome.media is None:
            asset["wordpress_media"] = None
            continue

        media_id = str(outcome.media.get("id"))
        key = str(asset["file"])
        # 引用没变就沿用旧时间戳，重复运行不产生假 diff。
        verified_at = now
        if key in previous and previous[key].split(":", 1)[0] == media_id:
            verified_at = previous[key].split(":", 1)[1]

        asset["wordpress_media"] = reference_from_item(
            outcome.media,
            rule=outcome.rule,
            dimension_check=outcome.dimension_check,
            verified_at=verified_at,
        )
        reference_count += 1

    summary = report.summary()
    data["library_version"] = "3.1"
    previous_index = data.get("wordpress_media_index") or {}
    index = {
        "generated_at": now,
        "source": "GET /wp-json/wp/v2/media?media_type=image",
        "linked_assets": reference_count,
        "total_assets": len(data["assets"]),
        "matched": summary["matched"],
        "ambiguous": summary["ambiguous"],
        "rejected_generic": summary["rejected_generic"],
        "unmatched": summary["unmatched"],
        "by_rule": summary["by_rule"],
        "notes": (
            "Only assets with a wordpress_media reference are selectable by the "
            "pipeline; the rest have never been uploaded to WordPress."
        ),
    }
    # 内容没变就不刷新时间戳，否则每次运行都产生一行假 diff。
    if _without_timestamp(previous_index) == _without_timestamp(index):
        index["generated_at"] = previous_index.get("generated_at", now)
    data["wordpress_media_index"] = index

    catalog_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"linked": reference_count, "total": len(data["assets"])}


def verify_references(data: Dict[str, Any]) -> int:
    """复查 catalog 里已记的 media id 是否还在媒体库。返回失效条数。"""
    from src.modules.wordpress_integration.wp_api_client import get_wordpress_client

    client = get_wordpress_client(api_type="rest")
    checked = 0
    missing: List[str] = []

    for asset in data["assets"]:
        reference = asset.get("wordpress_media") or {}
        media_id = reference.get("id")
        if media_id is None:
            continue
        checked += 1
        try:
            item = client.get_media(int(media_id))
            if not item.get("id"):
                missing.append(f"{asset['file']} → id {media_id}")
        except Exception as error:  # noqa: BLE001 - 逐条报告比整批中断有用
            missing.append(f"{asset['file']} → id {media_id} ({error})")

    print(f"复查 {checked} 条引用，失效 {len(missing)} 条")
    for entry in missing[:50]:
        print(f"  - {entry}")
    return len(missing)


def main() -> int:
    args = parse_args()
    data = load_catalog(args.catalog)
    items = fetch_media_items()
    print(f"媒体库读取到 {len(items)} 条图片\n")

    report = build_report(data, items)
    drift = [] if args.no_drift_check else check_drift(report)
    print_report(report, args.list_unmatched, drift)

    if args.verify:
        missing = verify_references(data)
        if missing:
            print("有失效引用，先清理再发布。")
            return 1

    if not args.apply:
        print("dry-run：未改动 catalog（加 --apply 落盘）")
        return 1 if drift else 0

    if drift:
        print("漂移检测未通过，拒绝写回。确认图库确实变了再加 --no-drift-check。")
        return 1

    result = apply_to_catalog(data, report, args.catalog)
    print(f"已写回 {args.catalog}")
    print(f"  linked {result['linked']} / total {result['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
