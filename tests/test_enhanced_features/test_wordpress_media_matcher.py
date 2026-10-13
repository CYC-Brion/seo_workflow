"""匹配规则的单元测试。手工造索引，不联网。"""

from src.enhanced_features.image_integration.wordpress_media_matcher import (
    MediaIndex,
    RULE_MEDIA_ID,
    RULE_ORIGINAL_NAME,
    RULE_WEBP_NAME,
    extract_media_id,
    is_generic_stem,
    match_asset,
    match_assets,
    media_filename,
    normalize_stem,
    reference_from_item,
)


def _media(media_id, filename, width=900, height=700, source_url=None):
    return {
        "id": media_id,
        "source_url": source_url
        or f"https://yushengco.com/wp-content/uploads/2026/08/{filename}",
        "mime_type": "image/webp",
        "media_details": {"width": width, "height": height, "filesize": 180000},
    }


def _asset(file_name, width=900, height=700, original_source=""):
    return {
        "file": file_name,
        "width": width,
        "height": height,
        "original_source": original_source,
    }


def test_rule_a_matches_a_unique_filename_stem():
    index = MediaIndex([_media(101, "factory-08.webp")])

    outcome = match_asset(_asset("factory-evidence/factory-08.webp"), index)

    assert outcome.status == "matched"
    assert outcome.rule == RULE_WEBP_NAME
    assert outcome.media["id"] == 101
    assert outcome.dimension_check == "exact"


def test_duplicate_filenames_become_ambiguous_not_a_coin_flip():
    """同名条目有两个时不能随便挑一个 —— 过去重复上传留下的副本要人来判断。"""
    index = MediaIndex(
        [_media(101, "factory-10.webp"), _media(202, "factory-10.webp")]
    )

    outcome = match_asset(_asset("factory-evidence/factory-10.webp"), index)

    assert outcome.status == "ambiguous"
    assert outcome.media is None


def test_rule_c_uses_the_embedded_media_id():
    index = MediaIndex([_media(12529, "12529_wall-lamp-sets.jpg", 800, 600)])

    outcome = match_asset(
        _asset(
            "products/counterweight-base-01.webp",
            800,
            600,
            "wordpress_media/products/12529_wall-lamp-sets.jpg",
        ),
        index,
    )

    assert outcome.status == "matched"
    assert outcome.rule == RULE_MEDIA_ID
    assert outcome.media["id"] == 12529


def test_rule_c_refuses_a_dimension_mismatch():
    """ID 是对的但尺寸对不上，说明这条 original_source 记错了，宁可不匹配。"""
    index = MediaIndex([_media(12529, "12529_wall-lamp-sets.jpg", 800, 1600)])

    outcome = match_asset(
        _asset(
            "products/counterweight-base-01.webp",
            800,
            600,
            "wordpress_media/products/12529_wall-lamp-sets.jpg",
        ),
        index,
    )

    assert outcome.status == "unmatched"


def test_rule_d_decodes_url_encoded_chinese_names():
    index = MediaIndex(
        [
            _media(
                301,
                "全检-1.jpg",
                1200,
                800,
                source_url=(
                    "https://yushengco.com/wp-content/uploads/2026/08/"
                    "%E5%85%A8%E6%A3%80-1.jpg"
                ),
            )
        ]
    )

    outcome = match_asset(
        _asset("factory-evidence/qc-full-inspection-01.webp", 1200, 800, "全检1-scaled.jpg"),
        index,
    )

    assert outcome.status == "matched"
    assert outcome.rule == RULE_ORIGINAL_NAME
    assert outcome.media["id"] == 301


def test_generic_numeric_names_are_rejected_rather_than_collapsed():
    """1.jpg 这类名字会把一堆不同资产全部塌到同一张图，必须挡掉。"""
    index = MediaIndex(
        [_media(401, "1.jpg", 1200, 800), _media(402, "2.jpg", 1200, 800)]
    )

    outcomes = [
        match_asset(_asset(f"factory-evidence/factory-{n:02d}.webp", 1200, 800, "1.jpg"), index)
        for n in (3, 5, 7)
    ]

    assert {outcome.status for outcome in outcomes} == {"rejected_generic"}
    assert {outcome.media for outcome in outcomes} == {None}


def test_normalize_stem_strips_ids_size_prefixes_and_suffixes():
    assert normalize_stem("12529_wall-lamp-sets.jpg") == "walllampsets"
    assert normalize_stem("480-3801Wall-Lamp-Sets.jpg") == "walllampsets"
    assert normalize_stem("全检2-scaled.jpg") == "全检2"
    assert normalize_stem("01_14263.jpg") == "14263"


def test_is_generic_stem_guards_short_and_numeric_values():
    assert is_generic_stem("1")
    assert is_generic_stem("002")
    assert is_generic_stem("ab")
    # 纯数字即使是 5 位也算泛化名 —— 它是附件 ID，不是能用来认图的描述。
    # 这类文件靠规则 C（尺寸精确校验）匹配，不靠名字。
    assert is_generic_stem("14263")
    assert not is_generic_stem("全检2")
    assert not is_generic_stem("factory08")


def test_extract_media_id_only_trusts_three_digits_or_more():
    assert extract_media_id("wordpress_media/products/12529_wall-lamp-sets.jpg") == "12529"
    assert extract_media_id("products/counterweight-base/01_14263.jpg") == "14263"
    assert extract_media_id("new/工艺过程横图/2.jpg") is None
    assert extract_media_id("") is None


def test_media_filename_from_source_url():
    item = {"source_url": "https://yushengco.com/wp-content/uploads/2026/08/factory-08.webp"}
    assert media_filename(item) == "factory-08.webp"


def test_match_assets_summarises_the_whole_catalog():
    assets = [
        _asset("factory-evidence/factory-08.webp"),
        _asset("factory-evidence/never-uploaded.webp"),
        _asset("factory-evidence/factory-03.webp", 1200, 800, "1.jpg"),
    ]
    index_items = [_media(101, "factory-08.webp"), _media(401, "1.jpg", 1200, 800)]

    summary = match_assets(assets, index_items).summary()

    assert summary["matched"] == 1
    assert summary["rejected_generic"] == 1
    assert summary["unmatched"] == 1
    assert summary["by_rule"] == {RULE_WEBP_NAME: 1}


def test_reference_from_item_carries_everything_the_publisher_needs():
    item = _media(101, "factory-08.webp")

    reference = reference_from_item(
        item, rule=RULE_WEBP_NAME, dimension_check="exact", verified_at="2026-10-13T00:00:00Z"
    )

    assert reference["id"] == 101
    assert reference["source_url"].endswith("/factory-08.webp")
    assert reference["filesize_bytes"] == 180000
    assert reference["match_rule"] == RULE_WEBP_NAME
    assert reference["verified_at"] == "2026-10-13T00:00:00Z"
