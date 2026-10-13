import json

from src.enhanced_features.image_integration.editorial_image_library import (
    EditorialImageLibrary,
)


def _write_asset(root, relative_path, size=1024):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def test_selects_matching_featured_image_and_section_evidence(tmp_path):
    _write_asset(tmp_path, "products/floor-lamp.webp")
    _write_asset(tmp_path, "factory/quality-check.webp")
    catalog = {
        "assets": [
            {
                "file": "products/floor-lamp.webp",
                "role": "product",
                "featured_eligible": True,
                "topics": ["floor lamp sets"],
                "alt_text": "Floor lamp set",
                "width": 900,
                "height": 900,
            },
            {
                "file": "factory/quality-check.webp",
                "role": "factory_evidence",
                "featured_eligible": False,
                "topics": ["quality control"],
                "alt_text": "Factory quality inspection",
                "width": 900,
                "height": 700,
            },
        ]
    }
    (tmp_path / "editorial_assets.json").write_text(json.dumps(catalog), encoding="utf-8")
    library = EditorialImageLibrary(tmp_path)

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
    _write_asset(tmp_path, "products/small.webp")
    catalog = {
        "assets": [
            {
                "file": "products/small.webp",
                "role": "product",
                "featured_eligible": True,
                "topics": ["floor lamp sets"],
                "alt_text": "Small floor lamp image",
                "width": 600,
                "height": 600,
            }
        ]
    }
    (tmp_path / "editorial_assets.json").write_text(json.dumps(catalog), encoding="utf-8")

    plan = EditorialImageLibrary(tmp_path).plan_article_images(
        {"keyword": "floor lamp sets"}, "Floor Lamp Sets", "<article><p>Body.</p></article>"
    )

    assert plan.featured_image is None


def test_rotates_equivalent_evidence_images_by_article_seed(tmp_path):
    for number in range(3):
        _write_asset(tmp_path, f"factory/qc-{number}.webp")
    catalog = {
        "assets": [
            {
                "file": f"factory/qc-{number}.webp",
                "role": "factory_evidence",
                "featured_eligible": False,
                "topics": ["quality control"],
                "alt_text": "Factory quality inspection",
                "width": 900,
                "height": 700,
            }
            for number in range(3)
        ]
    }
    (tmp_path / "editorial_assets.json").write_text(json.dumps(catalog), encoding="utf-8")
    library = EditorialImageLibrary(tmp_path)
    content = "<article><h2><strong>Quality Control Checks</strong></h2><p>Verify samples.</p></article>"

    selected = {
        library.plan_article_images({"keyword": f"keyword-{number}"}, "Guide", content)
        .inline_images[0]["file"]
        for number in range(12)
    }

    assert len(selected) > 1
