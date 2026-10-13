# Editorial Image Library

Clean, topic-tagged WebP assets for the current lighting-hardware SEO workflow.
Only assets registered in `editorial_assets.json` are eligible for automatic article use.

## WordPress Linkage

Articles **reference existing WordPress media library entries**; the pipeline does
not upload these files. Each asset therefore carries a `wordpress_media` block
(`id`, `source_url`, dimensions, byte size, and which rule matched it), or an
explicit `null` when the asset has never been uploaded.

- An asset with `"wordpress_media": null` is **not selectable**, full stop — even
  when its local file is present on disk. This is deliberate: `pic/` is not in
  git, so a fresh clone has no image files and image selection would otherwise
  fail silently.
- Of 279 assets, **82 are linked**; the other 197 (mostly the `new/` source
  photos) have never been uploaded. Run the linker to see the full list.

Rebuild or refresh the linkage with:

```bash
python scripts/link_editorial_assets_to_wordpress.py            # report only
python scripts/link_editorial_assets_to_wordpress.py --apply    # write catalog
python scripts/link_editorial_assets_to_wordpress.py --verify   # re-check ids still exist
```

The script is read-only against WordPress (only `GET /wp-json/wp/v2/media`) and
refuses to write when the match counts drift from the recorded baseline.

## Selection Policy

- Use only assets that carry a WordPress media reference (see above).
- Use only `featured_eligible: true` assets as featured images, and only when their topic matches the article cluster.
- Use `product_detail` and `factory_evidence` only beside the exact process, QC, packaging, export, engineering, or capability section they support.
- Use `application_scene` only for project, installation, residential, commercial, or interior-application sections.
- `factory_evidence` images are not product claims. When they show a finished makeup-mirror product, the article must describe the image only as a factory process or capability.
- The selector uses a stable article-specific rotation, so repeated pillar directions do not all receive the same image.

## Contents

- `product`: 36
- `product_detail`: 82
- `factory_evidence`: 123
- `application_scene`: 38

## Source Archive

`new/` keeps the owner-supplied source photos for traceability. It is not read by the article generator. Selected images are optimized to WebP, size-checked, topic-tagged, and copied into the role folders above before they can be used.

Use `editorial_assets.json` for topic matching and alt-text generation.
