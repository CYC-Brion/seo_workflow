"""
Site internal-link rules and explicit target mapping.
"""

from typing import Any, Dict, List


def get_default_internal_link_rules() -> List[Dict[str, Any]]:
    """Return the default internal-link rules."""
    return [
        {
            "url": "https://yushengco.com/product-category/floor-lamp-sets/",
            "target_names": ["Floor Lamp Sets"],
            "phrases": ["floor lamp accessories", "floor lamp kit", "floor standing lamp", "standing lamp", "floor lamp"],
        },
        {
            "url": "https://yushengco.com/product-category/wall-lamp-sets/",
            "target_names": ["Wall Lamp Sets"],
            "phrases": ["wall lamp accessories", "wall lamp kit", "wall mounted lighting", "wall light", "wall lamp", "wall sconce"],
        },
        {
            "url": "https://yushengco.com/product-category/table-lamp-sets/",
            "target_names": ["Table Lamp Sets"],
            "phrases": ["table lamp accessories", "table lamp kit", "desk lamp", "bedside lamp", "table lamp"],
        },
        {
            "url": "https://yushengco.com/product-category/custom-hotel-parts/",
            "target_names": ["Custom Hotel Parts"],
            "phrases": ["hotel project", "hospitality lighting", "hotel room lighting", "hotel parts", "contract project"],
        },
        {
            "url": "https://yushengco.com/product-category/custom-made-parts/",
            "target_names": ["Custom Made Parts"],
            "phrases": ["custom metal parts", "custom parts", "bespoke parts", "OEM parts", "made-to-order parts"],
        },
        {
            "url": "https://yushengco.com/product-category/panels/",
            "target_names": ["Panels"],
            "phrases": ["decorative panel", "metal panel", "mounting panel", "sheet metal panel", "panel"],
        },
        {
            "url": "https://yushengco.com/product-category/tubes/",
            "target_names": ["Tubes"],
            "phrases": ["telescopic tube", "lamp tube", "aluminum tube", "steel tube", "structural tube", "tube"],
        },
        {
            "url": "https://yushengco.com/product-category/universal-joints/",
            "target_names": ["Universal Joints"],
            "phrases": ["universal joint", "joint connector", "coupling", "rotating joint", "swivel joint"],
        },
        {
            "url": "https://yushengco.com/product-category/machined-parts/",
            "target_names": ["Machined Parts"],
            "phrases": ["precision parts", "machined parts", "CNC parts", "turning parts", "milling parts", "precision hardware"],
        },
        {
            "url": "https://yushengco.com/services/",
            "target_names": ["Services"],
            # "services" / "our services" 必须显式列出：文章结语最常写的就是
            # "review our Services"，只给 service 的派生词会让句子里唯一该出链的
            # 位置反而没有链。单数 "service" 故意不加 —— 技术文里
            # "service life" / "service temperature" 是灯具参数，不该跳到服务页。
            "phrases": ["our services", "manufacturing services", "custom manufacturing services", "custom manufacturing service", "one-stop service", "services", "OEM customization", "ODM solutions", "custom manufacturing", "design support", "prototyping", "QC service", "supply chain support", "after-sales service", "deep cooperation", "project consultation", "solution", "OEM", "ODM"],
        },
        {
            "url": "https://yushengco.com/contact-us/",
            "target_names": ["Contact"],
            # 之前 get_internal_link_target_map() 里有 Contact -> /contact-us/，
            # 但规则表里没有对应条目，resolve_internal_link_targets() 取到的
            # phrases 是空列表，_replace_first_internal_link() 直接提前返回 ——
            # 工作簿里写了 Contact 也永远不出链。显式补上规则。
            # 同样避开裸词 "contact"：五金语境里 "contact" 可能是电接触点。
            "phrases": ["contact us", "contact our team", "get in touch", "reach out to us", "request a quote", "request a quotation", "get a quote", "send us your drawings", "send your inquiry", "submit your requirements", "RFQ"],
        },
        {
            "url": "https://yushengco.com/about-us/",
            "target_names": ["About Us"],
            "phrases": ["company profile", "factory profile", "manufacturing experience", "production capacity", "certificates", "patents", "quality control", "factory strength", "company background", "about us", "26 years experience"],
        },
        {
            "url": "https://yushengco.com/",
            "target_names": ["Home"],
            # 裸词 "manufacturer" / "supplier" / "home" 已移除：它们是最先被扫到的
            # 通用词，会抢走本该指向 /services/、/about-us/、产品页的锚文本。
            # 实测一篇讲工厂能力的文章里，"supplier" 被 Home 吃掉，而
            # "review our Services" 一个字都没链出去。首页只留品牌相关的具体说法。
            "phrases": ["Yusheng hardware manufacturer", "Zhongshan Yusheng", "our factory", "lighting hardware manufacturer", "hardware craft company", "custom lighting hardware"],
        },
    ]


def _normalize_target_name(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def get_internal_link_target_map() -> Dict[str, str]:
    """Return a normalized explicit target-name to URL map."""
    target_map: Dict[str, str] = {
        _normalize_target_name("Home"): "https://yushengco.com/",
        _normalize_target_name("About Us"): "https://yushengco.com/about-us/",
        _normalize_target_name("Services"): "https://yushengco.com/services/",
        _normalize_target_name("Contact"): "https://yushengco.com/contact-us/",
        _normalize_target_name("RFQ"): "https://yushengco.com/contact-us/",
        _normalize_target_name("Floor Lamp Sets"): "https://yushengco.com/product-category/floor-lamp-sets/",
        _normalize_target_name("Wall Lamp Sets"): "https://yushengco.com/product-category/wall-lamp-sets/",
        _normalize_target_name("Table Lamp Sets"): "https://yushengco.com/product-category/table-lamp-sets/",
        _normalize_target_name("Custom Hotel Parts"): "https://yushengco.com/product-category/custom-hotel-parts/",
        _normalize_target_name("Custom Made Parts"): "https://yushengco.com/product-category/custom-made-parts/",
        _normalize_target_name("Panels"): "https://yushengco.com/product-category/panels/",
        _normalize_target_name("Tubes"): "https://yushengco.com/product-category/tubes/",
        _normalize_target_name("Universal Joints"): "https://yushengco.com/product-category/universal-joints/",
        _normalize_target_name("Machined Parts"): "https://yushengco.com/product-category/machined-parts/",
    }

    for rule in get_default_internal_link_rules():
        url = str(rule.get("url", "")).strip()
        for target_name in rule.get("target_names", []):
            normalized = _normalize_target_name(target_name)
            if normalized and url:
                target_map[normalized] = url

    return target_map


def resolve_internal_link_targets(targets: str) -> List[Dict[str, Any]]:
    """Resolve semicolon- or comma-delimited target names into rules."""
    if not targets:
        return []

    target_map = get_internal_link_target_map()
    rule_by_url = {
        str(rule.get("url", "")).strip(): rule
        for rule in get_default_internal_link_rules()
        if str(rule.get("url", "")).strip()
    }

    resolved: List[Dict[str, Any]] = []
    seen_urls = set()
    for raw_name in str(targets).replace(",", ";").split(";"):
        target_name = raw_name.strip()
        normalized = _normalize_target_name(target_name)
        url = target_map.get(normalized, "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        base_rule = rule_by_url.get(url, {})
        phrases = [str(p).strip() for p in base_rule.get("phrases", []) if str(p).strip()]
        if not phrases:
            # 工作簿里明确声明了目标，却没有对应短语表时，至少用目标名本身当短语。
            # 否则 _replace_first_internal_link() 会因为 phrases 为空而静默返回，
            # 用户看到的是「我明明填了 Contact 但文章里没有 Contact 链接」。
            phrases = [target_name]
        resolved.append({
            "name": target_name,
            "url": url,
            "phrases": phrases,
        })

    return resolved
