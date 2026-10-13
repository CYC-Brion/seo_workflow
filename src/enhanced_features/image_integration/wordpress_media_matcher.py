"""把本地图库资产匹配到 WordPress 媒体库里已存在的条目。

这个模块**只做匹配**：不发网络请求、不读本地图片文件、不写任何文件。
取数据和落盘都由 scripts/link_editorial_assets_to_wordpress.py 负责，
这样规则本身可以脱离网络单独测试。

## 为什么要匹配而不是直接上传

每次发布会把本地 WebP 重新上传一遍，媒体库里就多一份副本（实测
factory-10.webp、白底图.jpg 各有 2 个同名条目，就是重复上传留下的）。
改成引用已有条目后，发布只写 URL，不再产生新副本。

## 三条规则

按优先级从高到低，第一条命中即止：

- **A** 本地 ``file`` 的 stem 与某个 WP 文件名 stem **唯一**相等。
  这些是我们自己压好上传的 WebP，所以引用到的就是优化后的版本，最理想。
- **C** ``original_source`` 里嵌着 WP 附件 ID
  （``wordpress_media/products/12529_wall-lamp-sets.jpg`` → 12529）。
  实测 25 条全部通过 width×height 精确相等校验，所以这条要求尺寸严格一致。
- **D** 原名归一化后唯一命中，且宽高比一致。用来捞 ``全检2-scaled.jpg``、
  ``白底图-1.jpg`` 这类中文名。

## 为什么必须有「纯数字名」防护

``original_source`` 里有 30 条是 ``1.jpg`` / ``02.jpg`` / ``002.jpg`` 这种名字。
不设防的话 ``factory-03``、``wall-lamp-set-05``、``manufacturing-process-05``
会**全部塌到同一张 1.jpg**，把错误的图配进文章。所以这类一律不匹配，
标记为 rejected_generic 交人工处理。
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

#: 匹配规则标识
RULE_WEBP_NAME = "A"
RULE_MEDIA_ID = "C"
RULE_ORIGINAL_NAME = "D"

#: 宽高比容差（规则 D）
ASPECT_TOLERANCE = 0.02

#: 归一化后长度低于此值、或纯数字的 stem 不允许参与匹配
MIN_SAFE_STEM_LENGTH = 3

#: 文件名开头的「序号_」或「ID_」，如 01_14263、12859_1
_RE_LEADING_ID = re.compile(r"^\d+_")
#: WordPress 给缩放图加的「宽-高」前缀，如 480-3801Wall-Lamp-Sets
_RE_SIZE_PREFIX = re.compile(r"^\d+-\d+")
#: 尾部的 -scaled / -copy
_RE_TRAILING_SUFFIX = re.compile(r"[-_](?:scaled|copy)$", re.IGNORECASE)
#: 所有分隔符
_RE_SEPARATORS = re.compile(r"[\s_\-]+")
#: 文件名里第一个 3 位以上的数字，视为 WP 附件 ID
_RE_MEDIA_ID = re.compile(r"(\d{3,})")


def media_filename(item: Dict[str, Any]) -> str:
    """从媒体条目的 source_url 取文件名。

    必须做 URL 解码 —— 中文名（``%E5%85%A8%E6%A3%80`` 之类）靠它才能匹配上。
    """
    source_url = str(item.get("source_url") or "")
    path = urlparse(source_url).path
    if not path:
        return str(item.get("slug", ""))
    return unquote(str(path).rsplit("/", 1)[-1])


def stem(name: str) -> str:
    """去掉目录和扩展名。"""
    return str(name).rsplit("/", 1)[-1].rsplit(".", 1)[0]


def normalize_stem(name: str) -> str:
    """把文件名归一化成可比较的 key。

    去掉数字前缀（媒体 ID 或序号）、WordPress 的 ``480-380`` 尺寸前缀、
    尾部的 ``-scaled`` / ``-copy``，再去掉所有分隔符并小写。
    """
    value = stem(name)
    value = _strip_leading_number_prefix(value)
    value = _RE_SIZE_PREFIX.sub("", value)
    value = _RE_TRAILING_SUFFIX.sub("", value)
    value = _RE_SEPARATORS.sub("", value)
    return value.lower()


def is_generic_stem(value: str) -> bool:
    """纯数字或过短的 stem 不能用来匹配 —— 会大量假阳性。"""
    return len(value) < MIN_SAFE_STEM_LENGTH or value.isdigit()


def extract_media_id(source: str) -> Optional[str]:
    """从 original_source 里抠出 WP 附件 ID。

    ``wordpress_media/products/12529_wall-lamp-sets.jpg`` → ``12529``
    ``products/counterweight-base/01_14263.jpg`` → ``14263``
    ``new/工艺过程横图/2.jpg`` → ``None``（只有一位数，不像 ID）
    """
    if not source:
        return None
    basename = str(source).rsplit("/", 1)[-1]
    match = _RE_MEDIA_ID.search(basename)
    return match.group(1) if match else None


@dataclass
class MatchOutcome:
    """单个资产的匹配结果。"""

    file: str
    status: str  # matched / ambiguous / rejected_generic / unmatched
    rule: str = ""
    dimension_check: str = ""
    media: Optional[Dict[str, Any]] = None
    detail: str = ""


@dataclass
class MatchReport:
    """整批资产的匹配报告。"""

    outcomes: List[MatchOutcome] = field(default_factory=list)

    def by_status(self, status: str) -> List[MatchOutcome]:
        return [o for o in self.outcomes if o.status == status]

    @property
    def matched(self) -> List[MatchOutcome]:
        return self.by_status("matched")

    def count_by_rule(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for outcome in self.matched:
            counts[outcome.rule] = counts.get(outcome.rule, 0) + 1
        # 排序让报告和落盘结果稳定，不随资产顺序变化。
        return dict(sorted(counts.items()))

    def summary(self) -> Dict[str, Any]:
        return {
            "matched": len(self.matched),
            "ambiguous": len(self.by_status("ambiguous")),
            "rejected_generic": len(self.by_status("rejected_generic")),
            "unmatched": len(self.by_status("unmatched")),
            "by_rule": self.count_by_rule(),
        }


class MediaIndex:
    """按文件名 stem 和媒体 ID 建索引的 WordPress 媒体库快照。"""

    def __init__(self, items: List[Dict[str, Any]]):
        self.items = list(items)
        self.by_stem: Dict[str, List[Dict[str, Any]]] = {}
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.by_normalized: Dict[str, List[Dict[str, Any]]] = {}

        for item in self.items:
            filename = media_filename(item)
            if not filename:
                continue
            self.by_stem.setdefault(stem(filename).lower(), []).append(item)
            normalized = normalize_stem(filename)
            if normalized:
                self.by_normalized.setdefault(normalized, []).append(item)
            media_id = item.get("id")
            if media_id is not None:
                self.by_id[str(media_id)] = item

    def dimensions(self, item: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        details = item.get("media_details") or {}
        return details.get("width"), details.get("height")

    def filesize(self, item: Dict[str, Any]) -> Optional[int]:
        details = item.get("media_details") or {}
        value = details.get("filesize")
        try:
            return int(value) if value else None
        except (TypeError, ValueError):
            return None


def match_asset(asset: Dict[str, Any], index: MediaIndex) -> MatchOutcome:
    """按 A → C → D 的优先级匹配单个资产。"""
    file_name = str(asset.get("file", ""))

    # --- 规则 A：本地 webp 文件名唯一命中 WP ---
    candidates = index.by_stem.get(stem(file_name).lower(), [])
    if len(candidates) == 1:
        return MatchOutcome(
            file=file_name,
            status="matched",
            rule=RULE_WEBP_NAME,
            dimension_check=_compare_dimensions(asset, candidates[0], index),
            media=candidates[0],
        )
    if len(candidates) > 1:
        return MatchOutcome(
            file=file_name,
            status="ambiguous",
            detail=f"同名条目 {len(candidates)} 个",
        )

    source = str(asset.get("original_source", ""))

    # --- 规则 C：original_source 里嵌的媒体 ID（要求尺寸精确一致）---
    media_id = extract_media_id(source)
    if media_id and media_id in index.by_id:
        item = index.by_id[media_id]
        if _compare_dimensions(asset, item, index) == "exact":
            return MatchOutcome(
                file=file_name,
                status="matched",
                rule=RULE_MEDIA_ID,
                dimension_check="exact",
                media=item,
            )

    # --- 规则 D：原名归一化 + 宽高比 ---
    if source:
        normalized = normalize_stem(source)
        if is_generic_stem(normalized):
            return MatchOutcome(
                file=file_name,
                status="rejected_generic",
                detail=f"归一化后是纯数字/过短：{normalized!r}",
            )

        name_candidates = index.by_normalized.get(normalized, [])
        if len(name_candidates) == 1:
            item = name_candidates[0]
            check = _compare_dimensions(asset, item, index)
            if check in ("exact", "aspect"):
                return MatchOutcome(
                    file=file_name,
                    status="matched",
                    rule=RULE_ORIGINAL_NAME,
                    dimension_check=check,
                    media=item,
                )
        elif len(name_candidates) > 1:
            return MatchOutcome(
                file=file_name,
                status="ambiguous",
                detail=f"归一化名 {normalized!r} 命中 {len(name_candidates)} 个条目",
            )

    return MatchOutcome(file=file_name, status="unmatched")


def match_assets(
    assets: List[Dict[str, Any]], items: List[Dict[str, Any]]
) -> MatchReport:
    """匹配整批资产。"""
    index = MediaIndex(items)
    return MatchReport(outcomes=[match_asset(a, index) for a in assets])


def reference_from_item(
    item: Dict[str, Any],
    rule: str = "",
    dimension_check: str = "",
    verified_at: str = "",
) -> Dict[str, Any]:
    """把匹配到的媒体条目转成写进 catalog 的 ``wordpress_media`` 结构。"""
    details = item.get("media_details") or {}
    try:
        filesize = int(details["filesize"]) if details.get("filesize") else None
    except (TypeError, ValueError):
        filesize = None

    return {
        "id": item.get("id"),
        "source_url": item.get("source_url", ""),
        "filename": media_filename(item),
        "width": details.get("width"),
        "height": details.get("height"),
        "mime_type": item.get("mime_type", ""),
        "filesize_bytes": filesize,
        "match_rule": rule,
        "dimension_check": dimension_check,
        "verified_at": verified_at,
    }


def _strip_leading_number_prefix(value: str) -> str:
    """``12859_1`` → ``1``；``01_14263`` → ``14263``。"""
    while True:
        match = _RE_LEADING_ID.match(value)
        if not match:
            return value
        value = value[match.end():]


def _compare_dimensions(
    asset: Dict[str, Any], item: Dict[str, Any], index: MediaIndex
) -> str:
    """比较 catalog 声明的尺寸与 WP 条目的实际尺寸。"""
    width, height = index.dimensions(item)
    asset_width = asset.get("width")
    asset_height = asset.get("height")
    if not (width and height and asset_width and asset_height):
        return "unchecked"
    if (width, height) == (asset_width, asset_height):
        return "exact"
    asset_ratio = float(asset_width) / float(asset_height)
    item_ratio = float(width) / float(height)
    if abs(item_ratio - asset_ratio) / asset_ratio <= ASPECT_TOLERANCE:
        return "aspect"
    return "mismatch"
