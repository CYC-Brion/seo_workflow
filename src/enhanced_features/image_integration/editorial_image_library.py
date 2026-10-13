"""Select and place curated editorial images without weakening article relevance."""

import html
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


IMAGE_MARKER_PREFIX = "<!-- editorial-image:"


@dataclass
class EditorialImagePlan:
    """The selected assets and HTML with upload-time image placeholders."""

    content: str
    featured_image: Optional[Dict[str, Any]]
    inline_images: List[Dict[str, Any]]


class EditorialImageLibrary:
    """Read the local asset catalogue and select images under strict constraints."""

    FEATURED_MIN_DIMENSION = 750
    BODY_MIN_DIMENSION = 400
    FEATURED_MAX_BYTES = 900 * 1024
    BODY_MAX_BYTES = 500 * 1024
    MAX_INLINE_IMAGES = 2

    SECTION_TERMS = {
        "quality control": ("quality", "qc", "inspection", "verify", "test"),
        "export packaging": ("packaging", "pack", "crate", "shipping", "delivery", "export"),
        "assembly process": ("assembly", "assemble", "wiring", "production"),
        "factory capability": ("factory", "manufacturing", "machining", "production line", "capacity"),
        "polishing": ("finish", "finishing", "polishing", "surface treatment"),
        "CNC machining": ("cnc", "machining", "machine", "tolerance"),
        "lighting applications": (
            "application", "project", "hotel", "commercial", "residential",
            "interior", "installation",
        ),
        "engineering collaboration": (
            "engineering", "design", "drawing", "sample", "customization",
            "development",
        ),
    }

    def __init__(self, library_dir: Optional[Path] = None):
        self.library_dir = library_dir or (
            Path(__file__).resolve().parents[3] / "pic" / "editorial_library"
        )
        self.catalog_path = self.library_dir / "editorial_assets.json"
        self.assets = self._load_assets()

    def _load_assets(self) -> List[Dict[str, Any]]:
        if not self.catalog_path.exists():
            return []
        data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return [asset for asset in data.get("assets", []) if isinstance(asset, dict)]

    def plan_article_images(
        self,
        workflow_item: Dict[str, Any],
        title: str,
        content: str,
    ) -> EditorialImagePlan:
        """Choose a featured image plus up to two section-relevant inline images."""
        context = " ".join(
            str(workflow_item.get(key, ""))
            for key in ("keyword", "cluster", "direction", "internal_link_targets")
        )
        selection_seed = "|".join(
            (str(workflow_item.get("keyword", "")), str(workflow_item.get("direction", "")), title)
        )
        featured = self._select_featured_image(
            f"{title} {context}", selection_seed
        )
        inline_images = self._select_inline_images(content, featured, selection_seed)
        return EditorialImagePlan(
            content=self._insert_inline_markers(content, inline_images),
            featured_image=featured,
            inline_images=inline_images,
        )

    def _select_featured_image(
        self, context: str, selection_seed: str = ""
    ) -> Optional[Dict[str, Any]]:
        candidates = []
        for asset in self.assets:
            if not asset.get("featured_eligible") or not self._is_file_eligible(
                asset, self.FEATURED_MIN_DIMENSION, self.FEATURED_MAX_BYTES
            ):
                continue
            score = self._topic_score(asset, context)
            if score:
                candidates.append((score, asset))
        if not candidates:
            return None
        best_score = max(score for score, _ in candidates)
        best_candidates = [asset for score, asset in candidates if score == best_score]
        return self._choose_candidate(best_candidates, selection_seed).copy()

    def _select_inline_images(
        self,
        content: str,
        featured: Optional[Dict[str, Any]],
        selection_seed: str = "",
    ) -> List[Dict[str, Any]]:
        headings = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", content, re.I | re.S)
        used_files = {featured.get("file")} if featured else set()
        selected: List[Dict[str, Any]] = []
        for heading in headings:
            heading_text = re.sub(r"<[^>]+>", " ", heading).lower()
            candidates = []
            for asset in self.assets:
                if len(selected) >= self.MAX_INLINE_IMAGES:
                    return selected
                if asset.get("file") in used_files or not self._is_file_eligible(
                    asset, self.BODY_MIN_DIMENSION, self.BODY_MAX_BYTES
                ):
                    continue
                if not self._matches_heading(asset, heading_text):
                    continue
                candidates.append(asset)
            if candidates:
                chosen = self._choose_candidate(
                    candidates, f"{selection_seed}|{heading_text}|{len(selected)}"
                ).copy()
                # Store the original heading HTML (may include <strong>, <a> etc.)
                # so that _insert_inline_markers can match the real markup.
                chosen["heading"] = heading
                selected.append(chosen)
                used_files.add(chosen.get("file"))
        return selected

    def _insert_inline_markers(
        self, content: str, inline_images: List[Dict[str, Any]]
    ) -> str:
        updated = content
        for asset in inline_images:
            marker = self.marker_for(asset["file"])
            escaped_heading = re.escape(asset["heading"])
            pattern = re.compile(
                r"(<h[23][^>]*>\s*" + escaped_heading + r"\s*</h[23]>)",
                re.I | re.S,
            )
            updated, replacements = pattern.subn(r"\1\n" + marker, updated, count=1)
            if not replacements:
                continue
        return updated

    @staticmethod
    def marker_for(file_name: str) -> str:
        return f"{IMAGE_MARKER_PREFIX}{file_name} -->"

    def _matches_heading(self, asset: Dict[str, Any], heading: str) -> bool:
        topics = " ".join(asset.get("topics", [])).lower()
        for topic, terms in self.SECTION_TERMS.items():
            if topic in topics and any(term in heading for term in terms):
                return True
        if asset.get("role") == "product_detail":
            return any(term in heading for term in ("specification", "design", "component", "tube", "joint"))
        return False

    @staticmethod
    def _topic_score(asset: Dict[str, Any], context: str) -> int:
        normalized_context = context.lower()
        return sum(
            1 for topic in asset.get("topics", []) if topic.lower() in normalized_context
        )

    @staticmethod
    def _choose_candidate(
        candidates: List[Dict[str, Any]], selection_seed: str
    ) -> Dict[str, Any]:
        """Spread equivalent evidence images deterministically across articles."""
        ordered = sorted(candidates, key=lambda asset: str(asset.get("file", "")))
        digest = hashlib.sha256(selection_seed.encode("utf-8")).hexdigest()
        return ordered[int(digest, 16) % len(ordered)]

    def _is_file_eligible(
        self, asset: Dict[str, Any], min_dimension: int, max_bytes: int
    ) -> bool:
        width = int(asset.get("width", 0) or 0)
        height = int(asset.get("height", 0) or 0)
        path = self.library_dir / str(asset.get("file", ""))
        return (
            width >= min_dimension
            and height >= min_dimension
            and path.is_file()
            and path.stat().st_size <= max_bytes
        )


def build_inline_image_html(image: Dict[str, Any], source_url: str) -> str:
    """Build a responsive, layout-stable body image after WordPress upload."""
    width = int(image.get("width", 0) or 0)
    height = int(image.get("height", 0) or 0)
    alt_text = html.escape(str(image.get("alt_text", "")), quote=True)
    caption = html.escape(str(image.get("alt_text", "")))
    return (
        '<figure class="seo-article-image" '
        'style="max-width: 960px; margin: 32px auto;">'
        f'<img src="{html.escape(source_url, quote=True)}" alt="{alt_text}" '
        f'width="{width}" height="{height}" loading="lazy" decoding="async" '
        'style="display: block; width: 100%; height: auto; border-radius: 4px;" />'
        f"<figcaption>{caption}</figcaption></figure>"
    )
