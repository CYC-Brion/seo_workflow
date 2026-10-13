import json
import zlib

from src.enhanced_features.image_integration.editorial_image_library import (
    EditorialImageLibrary,
)


def _asset(file_name, **overrides):
    """造一条关联到 WP 媒体库的资产。

    这些测试**故意不碰磁盘** —— 选择门槛看的是 catalog 里的 WP 引用，
    本地文件在不在都不影响结果。以前 fixture 要造一堆假文件才能满足
    `path.is_file()` 门槛，那正是「换台机器就静默没图」的根源。
    """
    asset = {
        "file": file_name,
        "role": "factory_evidence",
        "featured_eligible": False,
        "topics": ["quality control"],
        "alt_text": "Factory quality inspection",
        "width": 900,
        "height": 700,
        "size_kb": 100,
        "wordpress_media": {
            "id": zlib.crc32(file_name.encode("utf-8")) or 1,
            "source_url": f"https://yushengco.com/wp-content/uploads/2026/08/{file_name}",
            "filename": file_name,
            "width": 900,
            "height": 700,
            "mime_type": "image/webp",
            "filesize_bytes": 100 * 1024,
            "match_rule": "A",
            "dimension_check": "exact",
            "verified_at": "2026-10-13T00:00:00Z",
        },
    }
    asset.update(overrides)
    return asset


def _write_catalog(root, assets):
    (root / "editorial_assets.json").write_text(
        json.dumps({"assets": assets}), encoding="utf-8"
    )
    return EditorialImageLibrary(root)


def test_selects_matching_featured_image_and_section_evidence(tmp_path):
    library = _write_catalog(
        tmp_path,
        [
            _asset(
                "products/floor-lamp.webp",
                role="product",
                featured_eligible=True,
                topics=["floor lamp sets"],
                alt_text="Floor lamp set",
                width=900,
                height=900,
            ),
            _asset("factory/quality-check.webp"),
        ],
    )

    plan = library.plan_article_images(
        {"keyword": "floor lamp sets", "cluster": "floor lamp sets"},
        "How to Source Floor Lamp Sets",
        # Real AI output wraps H2 text in <strong> — markers must still match
        "<article><h2><strong>Quality Control Checks</strong></h2><p>Verify samples.</p></article>",
    )

    assert plan.featured_image["file"] == "products/floor-lamp.webp"
    assert len(plan.inline_images) == 1
    assert "<!-- editorial-image:factory/quality-check.webp -->" in plan.content


def test_rejects_small_featured_image(tmp_path):
    library = _write_catalog(
        tmp_path,
        [
            _asset(
                "products/small.webp",
                role="product",
                featured_eligible=True,
                topics=["floor lamp sets"],
                alt_text="Small floor lamp image",
                width=600,
                height=600,
            )
        ],
    )

    plan = library.plan_article_images(
        {"keyword": "floor lamp sets"}, "Floor Lamp Sets", "<article><p>Body.</p></article>"
    )

    assert plan.featured_image is None


def test_rotates_equivalent_evidence_images_by_article_seed(tmp_path):
    library = _write_catalog(
        tmp_path, [_asset(f"factory/qc-{number}.webp") for number in range(3)]
    )
    content = "<article><h2><strong>Quality Control Checks</strong></h2><p>Verify samples.</p></article>"

    selected = {
        library.plan_article_images({"keyword": f"keyword-{number}"}, "Guide", content)
        .inline_images[0]["file"]
        for number in range(12)
    }

    assert len(selected) > 1


def test_asset_without_wordpress_reference_is_never_selected(tmp_path):
    """没有 WP 引用的资产一律不可选 —— 哪怕本地文件就在那里。

    回归背景：门槛原本是 `path.is_file()`。pic/ 不入库，换台机器 clone 下来
    所有本地文件都不在，配图会静默消失、文章照发。
    """
    orphan = _asset("factory/never-uploaded.webp")
    orphan["wordpress_media"] = None
    library = _write_catalog(tmp_path, [orphan, _asset("factory/linked.webp")])

    plan = library.plan_article_images(
        {"keyword": "quality control"},
        "Quality Control Guide",
        "<article><h2>Quality Control Checks</h2><p>Verify samples.</p></article>",
    )

    assert plan.featured_image is None
    assert [image["file"] for image in plan.inline_images] == ["factory/linked.webp"]
    assert library.unlinked_asset_count == 1
    assert [asset["file"] for asset in library.unlinked_assets] == [
        "factory/never-uploaded.webp"
    ]


def test_incomplete_reference_counts_as_unlinked(tmp_path):
    """有 id 没 URL（或反过来）不算有效引用，否则会写出 src="" 的图。"""
    broken = _asset("factory/half-linked.webp")
    broken["wordpress_media"] = {"id": 42, "source_url": ""}
    library = _write_catalog(tmp_path, [broken])

    assert library.unlinked_asset_count == 1
    assert library.wordpress_reference(broken) is None


def test_reference_filesize_beats_local_size_kb(tmp_path):
    """引用的是 jpg/png 原图，体积以 filesize_bytes 为准，不能用本地 WebP 的体积蒙混。"""
    heavy = _asset("factory/heavy-original.jpg", size_kb=10)
    heavy["wordpress_media"]["filesize_bytes"] = 600 * 1024
    library = _write_catalog(tmp_path, [heavy])

    assert not library._is_file_eligible(heavy, 400, 500 * 1024)


def test_falls_back_to_size_kb_when_wordpress_filesize_is_missing(tmp_path):
    """WP 没给 filesize 时退回 size_kb*1024，而不是当成 0 字节一律放行。"""
    asset = _asset("factory/no-filesize.webp", size_kb=600)
    asset["wordpress_media"]["filesize_bytes"] = None
    library = _write_catalog(tmp_path, [asset])

    assert not library._is_file_eligible(asset, 400, 500 * 1024)
    assert library._reference_bytes(asset) == 600 * 1024


def test_missing_catalog_yields_an_empty_library(tmp_path):
    library = EditorialImageLibrary(tmp_path)

    assert library.assets == []
    assert library.unlinked_asset_count == 0
