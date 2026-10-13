"""Retry one locally saved workflow article as a WordPress draft without duplicates."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.enhanced_features.image_integration.editorial_image_library import EditorialImageLibrary
from src.modules.wordpress_integration.wordpress_publisher import WordPressPublisher


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--category", default="Technical Guides")
    args = parser.parse_args()

    content = args.article.read_text(encoding="utf-8")
    library = EditorialImageLibrary(ROOT / "pic" / "editorial_library")
    editorial_images = []
    for relative_path in re.findall(r"<!-- editorial-image:([^\s]+) -->", content):
        editorial_images.append({
            "file": relative_path,
            "path": str(library.library_dir / relative_path),
            "marker": library.marker_for(relative_path),
        })

    publisher = WordPressPublisher("wordpress_retry_publisher", config={
        "batch_size": 1,
        "api_type": "rest",
        "default_status": "draft",
        "auto_create_categories": False,
        "auto_create_tags": False,
        "enable_media_upload": True,
    })
    result = publisher.execute([{
        "title": args.title,
        "content": content,
        "keyword": args.keyword,
        "categories": [args.category],
        "publish_status": "draft",
        "editorial_images": editorial_images,
    }])
    if result.status.value != "completed" or not result.output_data:
        print(result.error_message or "WordPress retry failed")
        return 1
    post = result.output_data[0]
    print(f"status={post.status} post_id={post.post_id} url={post.url} error={post.error}")
    return 0 if post.post_id else 1


if __name__ == "__main__":
    raise SystemExit(main())
