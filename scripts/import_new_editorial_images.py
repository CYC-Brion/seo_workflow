"""Import reviewed new photos into the editorial SEO image library."""

import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps


# 锚定到项目根，避免从其它目录启动时读不到图库
ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "pic" / "editorial_library"
SOURCE_ROOT = LIBRARY / "new"
CATALOG_PATH = LIBRARY / "editorial_assets.json"


def add_asset(assets, existing, source, destination, role, featured, topics, alt, notes):
    if destination.as_posix() in existing:
        return False

    target = LIBRARY / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA", "P"):
            if image.mode == "P":
                image = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        image.save(target, "WEBP", quality=80, method=6)
        width, height = image.size

    size_kb = round(target.stat().st_size / 1024, 1)
    if featured and (width < 750 or height < 750 or size_kb > 900):
        featured = False

    assets.append(
        {
            "file": destination.as_posix(),
            "original_source": source.relative_to(LIBRARY).as_posix(),
            "original_source_deleted_after_optimization": False,
            "role": role,
            "featured_eligible": featured,
            "topics": topics,
            "alt_text": alt,
            "notes": notes,
            "width": width,
            "height": height,
            "size_kb": size_kb,
        }
    )
    existing.add(destination.as_posix())
    return True


def image_dimensions(path):
    with Image.open(path) as image:
        return image.size


def import_factory_assets(assets, existing, counts):
    configs = {
        "通用工厂能力首图": (
            "factory-evidence",
            "factory",
            [
                "lighting hardware manufacturer",
                "lighting hardware factory",
                "factory capability",
                "production capacity",
                "factory audit",
            ],
            "Yusheng lighting hardware manufacturing facility",
            "Use for supplier capability, factory audit, and manufacturing-overview content.",
        ),
        "QC与检测横图": (
            "factory-evidence",
            "quality-control",
            [
                "quality control",
                "lighting parts quality control",
                "quality assurance",
                "inspection report",
                "quality standards",
            ],
            "Quality inspection of lighting hardware components at the Yusheng factory",
            "Use only beside inspection, verification, or quality-control content.",
        ),
        "工艺过程横图": (
            "factory-evidence",
            "manufacturing-process",
            [
                "lighting manufacturing process",
                "lamp manufacturing process",
                "lighting production process",
                "assembly process",
                "CNC machining",
                "polishing",
                "surface treatment",
            ],
            "Lighting hardware manufacturing process at the Yusheng factory",
            "Use only beside the named process or manufacturing section.",
        ),
        "采购与出口物流图": (
            "factory-evidence",
            "export-packaging",
            [
                "export packaging",
                "export logistics",
                "packaging and shipping",
                "order process",
                "project procurement",
            ],
            "Export packaging and logistics preparation at the Yusheng factory",
            "Use only beside logistics, packaging, or procurement content.",
        ),
        "工程协作素材": (
            "factory-evidence",
            "engineering-collaboration",
            [
                "engineering collaboration",
                "design support",
                "sample request",
                "customization process",
                "custom lighting hardware",
            ],
            "Engineering collaboration and sample development at Yusheng",
            "Use only beside engineering, sample, or customization content.",
        ),
    }
    for group, config in configs.items():
        prefix, topic_slug, topics, alt, notes = config
        for index, source in enumerate(sorted((SOURCE_ROOT / group).glob("*")), 1):
            if source.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            width, height = image_dimensions(source)
            if min(width, height) < 400:
                continue
            featured = group == "通用工厂能力首图" and width >= height
            if add_asset(
                assets,
                existing,
                source,
                Path(f"{prefix}/{topic_slug}-{index:02d}.webp"),
                "factory_evidence",
                featured,
                topics,
                alt,
                notes,
            ):
                counts[group] += 1


def import_product_assets(assets, existing, counts):
    configs = {
        "壁灯套件产品图": {
            "slug": "wall-lamp-set",
            "topics": [
                "wall lamp sets",
                "wall lamp parts",
                "wall lamp parts manufacturer",
                "wall lamp accessory supplier",
                "wall lamp mounting hardware",
            ],
            "alt": "Wall lamp set and component manufactured by Yusheng",
            "featured": {"01.jpg", "1.jpg", "8.jpg", "QQ图片20230220101917.jpg"},
        },
        "台灯套件产品图": {
            "slug": "table-lamp-set",
            "topics": [
                "table lamp sets",
                "table lamp parts",
                "table lamp parts manufacturer",
                "table lamp accessories parts",
                "table lamp base parts",
            ],
            "alt": "Table lamp set and component manufactured by Yusheng",
            "featured": {
                "008.jpg",
                "009.jpg",
                "05.jpg",
                "09.jpg",
                "白底.jpg",
                "白底图.jpg",
                "白底图1.jpg",
                "白底图2.jpg",
                "白底图3.jpg",
            },
        },
        "金属件管材产品图": {
            "slug": "metal-tube-and-machined-part",
            "topics": [
                "custom metal parts",
                "custom metal hardware parts",
                "machined parts",
                "machined metal parts factory",
                "CNC parts",
                "aluminum lamp tube components",
                "steel lamp tube supplier",
            ],
            "alt": "Custom metal tube or machined lighting hardware component by Yusheng",
            "featured": {
                "QQ图片20230307173727.jpg",
                "QQ图片20230307173731.jpg",
                "微信图片_20230831085915.jpg",
                "微信图片_202308310859151.jpg",
            },
        },
    }
    for group, config in configs.items():
        for index, source in enumerate(sorted((SOURCE_ROOT / group).glob("*")), 1):
            if source.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            width, height = image_dimensions(source)
            if min(width, height) < 400:
                continue
            featured = source.name in config["featured"] and min(width, height) >= 750
            if add_asset(
                assets,
                existing,
                source,
                Path(f"products/{config['slug']}-{index:02d}.webp"),
                "product" if featured else "product_detail",
                featured,
                config["topics"],
                config["alt"],
                "Use only in a matching product or specification article.",
            ):
                counts[group] += 1


def import_application_assets(assets, existing, counts):
    group = "项目应用场景图"
    topics = [
        "lighting applications",
        "lighting hardware for hotel projects",
        "contract lighting project",
        "commercial lighting hardware",
        "residential lighting hardware",
        "interior lighting project",
        "project lighting hardware",
    ]
    for index, source in enumerate(sorted((SOURCE_ROOT / group).glob("*")), 1):
        if source.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        width, height = image_dimensions(source)
        if min(width, height) < 600:
            continue
        if add_asset(
            assets,
            existing,
            source,
            Path(f"applications/lighting-project-application-{index:02d}.webp"),
            "application_scene",
            width >= height and min(width, height) >= 750,
            topics,
            "Lighting hardware application in an interior project",
            "Use only in project, application, commercial, residential, or hotel lighting content.",
        ):
            counts[group] += 1


def main():
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assets = data["assets"]
    existing = {asset["file"] for asset in assets}
    counts = Counter()
    import_factory_assets(assets, existing, counts)
    import_product_assets(assets, existing, counts)
    import_application_assets(assets, existing, counts)
    data["library_version"] = "3.0"
    data["selection_policy"] = (
        "Select a featured image only when featured_eligible is true, its topic matches "
        "the article cluster, both dimensions are at least 750 px, and the optimized "
        "WebP is no larger than 900 KB. Use factory_evidence, product_detail, and "
        "application_scene assets only beside matching sections."
    )
    data["summary"] = dict(sorted(Counter(asset["role"] for asset in assets).items()))
    data["new_asset_import"] = dict(counts)
    CATALOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"imported": sum(counts.values()), "by_group": counts, "summary": data["summary"]}, ensure_ascii=False, default=dict))


if __name__ == "__main__":
    main()
