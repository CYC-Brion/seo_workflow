"""
站内链接规则配置
集中维护文章内链的触发词和目标 URL。
"""

from typing import Any, Dict, List


def get_default_internal_link_rules() -> List[Dict[str, Any]]:
    """返回默认站内链接规则"""
    return [
        {
            "url": "https://yushengco.com/product-category/floor-lamp-sets/",
            "phrases": ["floor lamp accessories", "floor lamp kit", "floor standing lamp", "standing lamp", "floor lamp"],
        },
        {
            "url": "https://yushengco.com/product-category/wall-lamp-sets/",
            "phrases": ["wall lamp accessories", "wall lamp kit", "wall mounted lighting", "wall light", "wall lamp", "wall sconce"],
        },
        {
            "url": "https://yushengco.com/product-category/table-lamp-sets/",
            "phrases": ["table lamp accessories", "table lamp kit", "desk lamp", "bedside lamp", "table lamp"],
        },
        {
            "url": "https://yushengco.com/product-category/custom-hotel-parts/",
            "phrases": ["hotel project", "hospitality lighting", "hotel room lighting", "hotel parts", "contract project"],
        },
        {
            "url": "https://yushengco.com/product-category/custom-made-parts/",
            "phrases": ["custom metal parts", "custom parts", "bespoke parts", "OEM parts", "made-to-order parts"],
        },
        {
            "url": "https://yushengco.com/product-category/panels/",
            "phrases": ["decorative panel", "metal panel", "mounting panel", "sheet metal panel", "panel"],
        },
        {
            "url": "https://yushengco.com/product-category/tubes/",
            "phrases": ["telescopic tube", "lamp tube", "aluminum tube", "steel tube", "structural tube", "tube"],
        },
        {
            "url": "https://yushengco.com/product-category/universal-joints/",
            "phrases": ["universal joint", "joint connector", "coupling", "rotating joint", "swivel joint"],
        },
        {
            "url": "https://yushengco.com/product-category/machined-parts/",
            "phrases": ["precision parts", "machined parts", "CNC parts", "turning parts", "milling parts", "precision hardware"],
        },
        {
            "url": "https://yushengco.com/services/",
            "phrases": ["OEM customization", "ODM solutions", "custom manufacturing services", "custom manufacturing", "design support", "prototyping", "QC service", "supply chain support", "after-sales service", "deep cooperation", "project consultation", "solution", "OEM", "ODM"],
        },
        {
            "url": "https://yushengco.com/about-us/",
            "phrases": ["company profile", "factory profile", "manufacturing experience", "production capacity", "certificates", "patents", "quality control", "factory strength", "company background", "about us", "26 years experience"],
        },
        {
            "url": "https://yushengco.com/",
            "phrases": ["Yusheng hardware manufacturer", "Zhongshan Yusheng", "our factory", "lighting hardware manufacturer", "hardware craft company", "custom lighting hardware", "manufacturer", "supplier", "home"],
        },
    ]
