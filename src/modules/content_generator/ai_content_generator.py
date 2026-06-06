"""
AI content generation module for the SEO workflow.
"""

import html
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from config.internal_links_config import (
    get_default_internal_link_rules,
    resolve_internal_link_targets,
)
from src.core import AINode
from src.utils import (
    AIError,
    AIMessage,
    config_manager,
    create_system_message,
    create_user_message,
    get_ai_client,
    get_logger,
)


@dataclass
class ContentGenerationResult:
    original_inputs: List[Dict[str, str]]
    generated_contents: List[str]
    content_sources: Dict[str, str]
    confidence_scores: Dict[str, float]
    metadata: Dict[str, Any]


class AIContentGenerator(AINode):
    """Generate article content from keyword/title inputs."""

    CTA_TEXT_BY_TARGET = {
        "Services": "lighting hardware sourcing support",
        "About Us": "factory capability overview",
        "Contact": "project consultation",
        "Home": "main company website",
        "Floor Lamp Sets": "floor lamp sets",
        "Wall Lamp Sets": "wall lamp sets",
        "Table Lamp Sets": "table lamp sets",
        "Custom Hotel Parts": "custom hotel parts",
        "Custom Made Parts": "custom manufacturing support",
        "Panels": "panel fabrication capability",
        "Tubes": "tube processing capability",
        "Universal Joints": "universal joint capability",
        "Machined Parts": "machined parts capability",
    }

    INTERNAL_LINK_STYLE = (
        "color: #e36d2d; "
        "font-weight: 700; "
        "text-decoration: underline; "
        "text-decoration-thickness: 2px; "
        "text-underline-offset: 2px;"
    )

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(node_id, "content_generator", config)

        self.batch_size = config.get("batch_size", 5)
        self.max_content_per_input = config.get("max_content_per_input", 1)
        self.target_word_count = config.get("target_word_count", 1500)
        self.enable_fallback = config.get("enable_fallback", True)
        self.language = config.get("language", "en")
        self.industry = config.get(
            "industry", "Metal Hardware & Lighting Accessories Processing"
        )
        self.html_format = config.get("html_format", True)
        self.include_subheadings = config.get("include_subheadings", True)
        self.include_bullet_points = config.get("include_bullet_points", True)
        self.internal_linking_enabled = config.get("internal_linking_enabled", True)
        self.max_internal_links_per_article = config.get(
            "max_internal_links_per_article", 4
        )
        self.internal_link_rules = config.get(
            "internal_link_rules", get_default_internal_link_rules()
        )
        self.prompt_template = self._load_prompt_template()
        self._article_meta: Dict[str, Dict[str, str]] = {}

        self.stats = {
            "total_inputs": 0,
            "contents_generated": 0,
            "inputs_processed": 0,
            "inputs_failed": 0,
            "batches_processed": 0,
            "ai_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_word_count": 0,
        }

        self.logger = get_logger(f"content_generator.{node_id}")

    def _load_prompt_template(self) -> Dict[str, Any]:
        try:
            prompt_name = "content_generator"
            version = config_manager.get_current_prompt_version(prompt_name)
            return config_manager.get_prompt_template(prompt_name, version)
        except Exception:
            return {
                "system": (
                    "You are an SEO specialist and professional content writer "
                    "specializing in the Metal Hardware & Lighting Accessories "
                    "Processing industry."
                ),
                "user": (
                    "Write a comprehensive article about '{keyword}' with the title "
                    "'{title}'. Target around {word_count} words and output HTML only."
                ),
                "parameters": {"temperature": 0.7, "max_tokens": 4000},
            }

    def execute_impl(self, input_data: Any) -> Any:
        inputs = self._validate_and_prepare_input(input_data)
        all_contents: List[str] = []
        content_sources: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}

        for batch in self._create_batches(inputs):
            try:
                batch_result = self._process_batch(batch)
                all_contents.extend(batch_result.generated_contents)
                content_sources.update(batch_result.content_sources)
                confidence_scores.update(batch_result.confidence_scores)
                self.stats["batches_processed"] += 1
                self.stats["inputs_processed"] += len(batch)
            except Exception:
                fallback_contents = self._generate_default_contents(batch)
                all_contents.extend(fallback_contents)
                for item, content in zip(batch, fallback_contents):
                    content_sources[content] = item["keyword"]
                    confidence_scores[content] = 0.5
                self.stats["inputs_failed"] += len(batch)

        if all_contents:
            total_words = sum(len(content.split()) for content in all_contents)
            self.stats["average_word_count"] = total_words / len(all_contents)

        self._log_statistics(all_contents)
        return all_contents

    def _validate_and_prepare_input(self, input_data: Any) -> List[Dict[str, str]]:
        inputs: List[Dict[str, str]] = []

        def build_input(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
            keyword = str(item.get("keyword", item.get("keywords", ""))).strip()
            if not keyword:
                return None

            title = str(item.get("title", "")).strip() or f"Complete Guide to {keyword}"
            direction = str(
                item.get("direction", item.get("title_angle", item.get("pillar_direction", "")))
            ).strip()
            lane = str(item.get("lane", "")).strip()
            priority = str(item.get("priority", "")).strip()
            cluster = str(item.get("cluster", "")).strip()
            category = str(item.get("category", "")).strip()
            internal_link_targets = str(item.get("internal_link_targets", "")).strip()

            return {
                "keyword": keyword,
                "title": title,
                "category": category,
                "direction": direction,
                "lane": lane,
                "priority": priority,
                "cluster": cluster,
                "internal_link_targets": internal_link_targets,
            }

        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    built = build_input(item)
                    if built:
                        inputs.append(built)
                elif isinstance(item, str) and item.strip():
                    inputs.append(build_input({"keyword": item}) or {})
        elif isinstance(input_data, dict):
            built = build_input(input_data)
            if built:
                inputs.append(built)
        elif isinstance(input_data, str):
            if input_data.startswith("[") and input_data.endswith("]"):
                try:
                    return self._validate_and_prepare_input(json.loads(input_data))
                except json.JSONDecodeError:
                    pass
            built = build_input({"keyword": input_data})
            if built:
                inputs.append(built)
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")

        inputs = [item for item in inputs if item]
        if not inputs:
            raise ValueError("Input data is empty or invalid")

        self.stats["total_inputs"] = len(inputs)
        return inputs

    def _create_batches(self, inputs: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        batch_size = min(self.batch_size, 10)
        return [inputs[i : i + batch_size] for i in range(0, len(inputs), batch_size)]

    def _process_batch(self, batch: List[Dict[str, str]]) -> ContentGenerationResult:
        generated_contents: List[str] = []
        content_sources: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}

        for input_item in batch:
            keyword = input_item["keyword"]
            try:
                contents = self._generate_content_for_input(
                    keyword=keyword,
                    title=input_item["title"],
                    category=input_item.get("category", ""),
                    direction=input_item.get("direction", ""),
                    lane=input_item.get("lane", ""),
                    priority=input_item.get("priority", ""),
                    cluster=input_item.get("cluster", ""),
                    internal_link_targets=input_item.get("internal_link_targets", ""),
                )
            except Exception:
                contents = [
                    self._generate_default_content(
                        keyword=keyword,
                        title=input_item["title"],
                        direction=input_item.get("direction", ""),
                        lane=input_item.get("lane", ""),
                        priority=input_item.get("priority", ""),
                        cluster=input_item.get("cluster", ""),
                        internal_link_targets=input_item.get("internal_link_targets", ""),
                    )
                ]

            generated_contents.extend(contents)
            for content in contents:
                content_sources[content] = keyword
                confidence_scores[content] = 0.9
            self.stats["contents_generated"] += len(contents)

        return ContentGenerationResult(
            original_inputs=batch,
            generated_contents=generated_contents,
            content_sources=content_sources,
            confidence_scores=confidence_scores,
            metadata={},
        )

    def _process_batch_with_fallback(
        self, batch: List[Dict[str, str]]
    ) -> ContentGenerationResult:
        return self._process_batch(batch)

    def _generate_content_for_input(
        self,
        keyword: str,
        title: str,
        category: str = "",
        direction: str = "",
        lane: str = "",
        priority: str = "",
        cluster: str = "",
        internal_link_targets: str = "",
    ) -> List[str]:
        messages = self._prepare_messages(
            keyword=keyword,
            title=title,
            category=category,
            direction=direction,
            lane=lane,
            priority=priority,
            cluster=cluster,
            internal_link_targets=internal_link_targets,
        )
        prompt_tpl = self._get_prompt_for_category(category)
        ai_client = get_ai_client("content_generator", use_fallback=False)
        response = ai_client.chat_completion(
            messages=messages,
            temperature=prompt_tpl.get("parameters", {}).get("temperature", 0.7),
            max_tokens=prompt_tpl.get("parameters", {}).get("max_tokens", 4000),
        )

        self.stats["ai_calls"] += 1
        self.stats["total_tokens"] += response.usage.get("total_tokens", 0)
        self.stats["total_cost"] += response.cost

        content = self._parse_ai_response(
            response.content,
            internal_link_targets=internal_link_targets,
            lane=lane,
        )
        return [content][: self.max_content_per_input]

    def _prepare_messages(
        self,
        keyword: str,
        title: str,
        category: str = "",
        direction: str = "",
        lane: str = "",
        priority: str = "",
        cluster: str = "",
        internal_link_targets: str = "",
    ) -> List[AIMessage]:
        prompt_tpl = self._get_prompt_for_category(category)
        cta_destination = self._get_cta_destination(lane, internal_link_targets)
        user_prompt = prompt_tpl.get("user", "").format(
            keyword=keyword,
            title=title,
            word_count=self.target_word_count,
            industry=self.industry,
            language=self.language,
            direction=direction,
            title_angle=direction,
            lane=lane,
            priority=priority,
            cluster=cluster,
            internal_link_targets=internal_link_targets,
            cta_destination=cta_destination,
            target_audience=(
                "procurement teams, sourcing managers, product managers, engineers, "
                "and B2B buyers comparing manufacturing partners"
            ),
        )

        context_lines = []
        if lane:
            context_lines.append(f"- Lane: {lane}")
        if priority:
            context_lines.append(f"- Priority: {priority}")
        if cluster:
            context_lines.append(f"- Cluster: {cluster}")
        if direction:
            context_lines.append(f"- Direction: {direction}")
        if internal_link_targets:
            context_lines.append(f"- Preferred internal-link targets: {internal_link_targets}")
        if cta_destination:
            context_lines.append(f"- CTA destination hint: {cta_destination}")
        if lane.lower() == "pillar":
            context_lines.append(
                "- Writing mode: emphasize supplier comparison, sourcing fit, decision confidence, and factory capability proof."
            )
        elif lane:
            context_lines.append(
                "- Writing mode: keep the article tighter, more specific, and focused on one technical or sourcing subtopic."
            )
        if priority.upper() == "A":
            context_lines.append(
                "- Commercial emphasis: high. Use stronger buyer-intent, pre-order verification, and conversion-aware framing."
            )
        elif priority.upper() in {"B", "C"}:
            context_lines.append(
                "- Commercial emphasis: moderate. Balance coverage, depth, and SEO support value."
            )
        if cluster:
            context_lines.append(
                "- Differentiate this article from other posts in the same cluster. Avoid repeating generic intros, headings, and conclusions."
            )
        if direction:
            context_lines.append(
                "- Keep the entire article centered on the current direction and do not drift into broad generic education."
            )

        if context_lines:
            user_prompt += "\n\n# Workflow Context\n" + "\n".join(context_lines)

        return [
            create_system_message(prompt_tpl.get("system", "")),
            create_user_message(user_prompt),
        ]

    def _get_prompt_for_category(self, category: str) -> Dict[str, Any]:
        try:
            from config.prompts_config import CATEGORY_PROMPTS

            if category and category in CATEGORY_PROMPTS:
                return CATEGORY_PROMPTS[category]
        except ImportError:
            pass
        return self.prompt_template

    def _get_cta_destination(self, lane: str, internal_link_targets: str) -> str:
        target_names = [part.strip() for part in internal_link_targets.split(";") if part.strip()]
        if lane.lower() == "pillar":
            for preferred in ["Services", "About Us", "Contact", "Home"]:
                if preferred in target_names:
                    return preferred
            return "Services or Contact"
        if target_names:
            return ", ".join(target_names[:2])
        return "relevant product or service page"

    def _get_cta_target_names(
        self, lane: str, internal_link_targets: str
    ) -> List[str]:
        target_names = [part.strip() for part in internal_link_targets.split(";") if part.strip()]
        if lane.lower() == "pillar":
            prioritized: List[str] = []
            for preferred in ["Services", "About Us", "Contact", "Home"]:
                if preferred in target_names and preferred not in prioritized:
                    prioritized.append(preferred)
            return prioritized[:2] or ["Services", "Contact"]
        return target_names[:2] or ["Services"]

    def _parse_ai_response(
        self,
        ai_response: str,
        internal_link_targets: str = "",
        lane: str = "",
    ) -> str:
        content = ai_response.strip()
        extracted_slug = ""
        extracted_excerpt = ""

        try:
            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start != -1 and json_end != -1 and json_end > json_start:
                data = json.loads(content[json_start : json_end + 1])
                if isinstance(data, dict) and "content" in data:
                    content = str(data.get("content", "")).strip()
                    extracted_slug = str(data.get("slug", "")).strip()
                    extracted_excerpt = str(data.get("excerpt", "")).strip()
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        body_match = re.search(r"<body[^>]*>(.*?)</body>", content, re.I | re.S)
        if body_match:
            content = body_match.group(1).strip()
        else:
            html_match = re.search(r"<html[^>]*>(.*?)</html>", content, re.I | re.S)
            if html_match:
                content = html_match.group(1).strip()

        content = self._sanitize_ai_authored_internal_links(content)
        content = self._clean_html_content(content)
        if self.html_format:
            if not content.startswith("<"):
                content = f"<article>{content}</article>"
            elif not re.search(r"<html|<body|<article|<div|<h\d|<p|<ul|<ol", content, re.I):
                content = f"<article>{content}</article>"

        content = self._apply_internal_links(
            content, internal_link_targets=internal_link_targets
        )
        content = self._ensure_cta_section(
            content,
            internal_link_targets=internal_link_targets,
            lane=lane,
        )
        content = self._link_cta_targets(
            content,
            lane=lane,
            internal_link_targets=internal_link_targets,
        )

        if extracted_slug or extracted_excerpt:
            self._article_meta[content] = {
                "slug": extracted_slug,
                "excerpt": extracted_excerpt,
            }

        return content

    def _apply_internal_links(
        self, content: str, internal_link_targets: str = ""
    ) -> str:
        if not self.internal_linking_enabled or not self.html_format or not content:
            return content

        tokens = re.split(r"(<[^>]+>)", content)
        explicit_rules = resolve_internal_link_targets(internal_link_targets)
        used_urls = set()
        inserted_count = 0
        in_anchor = False

        for index, token in enumerate(tokens):
            if token.startswith("<"):
                lowered = token.lower()
                if lowered.startswith("<a ") or lowered.startswith("<a>"):
                    in_anchor = True
                elif lowered.startswith("</a"):
                    in_anchor = False
                continue

            if in_anchor or inserted_count >= self.max_internal_links_per_article:
                continue

            updated_token = token
            for rule in explicit_rules:
                url = rule.get("url", "")
                if not url or url in used_urls:
                    continue
                updated_token, replaced = self._replace_first_internal_link(updated_token, rule)
                if replaced:
                    used_urls.add(url)
                    inserted_count += 1
                if inserted_count >= self.max_internal_links_per_article:
                    break

            if inserted_count < self.max_internal_links_per_article:
                for rule in self.internal_link_rules:
                    url = rule.get("url", "")
                    if not url or url in used_urls:
                        continue
                    updated_token, replaced = self._replace_first_internal_link(updated_token, rule)
                    if replaced:
                        used_urls.add(url)
                        inserted_count += 1
                    if inserted_count >= self.max_internal_links_per_article:
                        break

            tokens[index] = updated_token
            if inserted_count >= self.max_internal_links_per_article:
                break

        content_with_links = "".join(tokens)
        if "https://yushengco.com/" not in content_with_links:
            content_with_links += (
                '<p style="line-height: 2; font-size: 16px;">'
                f'Learn more from our {self._build_internal_link_html("https://yushengco.com/", "home page")}.'
                "</p>"
            )
        return content_with_links

    def _build_internal_link_html(self, url: str, text: str) -> str:
        return f'<a href="{url}" style="{self.INTERNAL_LINK_STYLE}">{text}</a>'

    def _replace_first_internal_link(
        self, text: str, rule: Dict[str, Any]
    ) -> Tuple[str, bool]:
        url = str(rule.get("url", "")).strip()
        phrases = [phrase for phrase in rule.get("phrases", []) if phrase]
        if not url or not phrases:
            return text, False

        for phrase in sorted(phrases, key=len, reverse=True):
            pattern = re.compile(rf"(?<!\w)({re.escape(phrase)})(?!\w)", re.I)

            def _replacement(match: re.Match) -> str:
                return self._build_internal_link_html(url, match.group(1))

            replaced_text, count = pattern.subn(_replacement, text, count=1)
            if count > 0:
                return replaced_text, True

        return text, False

    def _sanitize_ai_authored_internal_links(self, content: str) -> str:
        if not content:
            return content

        content = re.sub(
            r'<a\b[^>]*href\s*=\s*["\'](?:https?://(?:www\.)?yushengco\.com[^"\']*|/[^"\']*)["\'][^>]*>(.*?)</a>',
            r"\1",
            content,
            flags=re.I | re.S,
        )
        content = re.sub(
            r"https?://(?:www\.)?yushengco\.com[^\s<>\"]*",
            "",
            content,
            flags=re.I,
        )
        content = re.sub(
            r'(?<!["\'])/(?:about-us|services|our-contacts|contact-us|contact|products?|product-category/[^/\s<>\"]+)(?:/[^\s<>\"]*)?',
            "",
            content,
            flags=re.I,
        )
        content = re.sub(r"\(\s*\)", "", content)
        content = re.sub(r"\s{2,}", " ", content)
        return content.strip()

    def _build_cta_paragraph(self, lane: str, internal_link_targets: str) -> str:
        linked_phrases: List[str] = []
        for target_name in self._get_cta_target_names(lane, internal_link_targets):
            resolved_rules = resolve_internal_link_targets(target_name)
            if not resolved_rules:
                continue
            url = str(resolved_rules[0].get("url", "")).strip()
            if not url:
                continue
            anchor_text = self.CTA_TEXT_BY_TARGET.get(target_name, target_name.lower())
            linked_phrases.append(self._build_internal_link_html(url, anchor_text))

        if not linked_phrases:
            linked_phrases.append(
                self._build_internal_link_html(
                    "https://yushengco.com/services/",
                    "lighting hardware sourcing support",
                )
            )

        if lane.lower() == "pillar":
            intro = (
                "If you are comparing suppliers or preparing a new sourcing program, "
                "the next useful step is to review"
            )
        else:
            intro = (
                "If your project involves finish, tolerance, or custom production questions, "
                "the next useful step is to review"
            )

        linked_text = (
            linked_phrases[0]
            if len(linked_phrases) == 1
            else f"{linked_phrases[0]} and {linked_phrases[1]}"
        )
        return (
            '<p style="line-height: 2; font-size: 16px;">'
            f"{intro} {linked_text} before finalizing drawings, samples, or mass-production requirements."
            "</p>"
        )

    def _link_named_targets_in_fragment(
        self, fragment: str, target_names: List[str]
    ) -> str:
        if not fragment or not target_names:
            return fragment

        tokens = re.split(r"(<[^>]+>)", fragment)
        in_anchor = False
        remaining_targets = list(target_names)

        for index, token in enumerate(tokens):
            if token.startswith("<"):
                lowered = token.lower()
                if lowered.startswith("<a ") or lowered.startswith("<a>"):
                    in_anchor = True
                elif lowered.startswith("</a"):
                    in_anchor = False
                continue

            if in_anchor or not remaining_targets:
                continue

            updated_token = token
            consumed_targets: List[str] = []
            for target_name in remaining_targets:
                resolved_rules = resolve_internal_link_targets(target_name)
                if not resolved_rules:
                    continue
                url = str(resolved_rules[0].get("url", "")).strip()
                if not url or target_name not in updated_token:
                    continue
                updated_token = updated_token.replace(
                    target_name,
                    self._build_internal_link_html(url, target_name),
                    1,
                )
                consumed_targets.append(target_name)

            if consumed_targets:
                tokens[index] = updated_token
                remaining_targets = [
                    target_name
                    for target_name in remaining_targets
                    if target_name not in consumed_targets
                ]

        return "".join(tokens)

    def _link_cta_targets(
        self, content: str, lane: str = "", internal_link_targets: str = ""
    ) -> str:
        if not self.html_format or not content:
            return content

        paragraphs = list(
            re.finditer(r"<p\b[^>]*>.*?</p>", content, flags=re.I | re.S)
        )
        if not paragraphs:
            return content

        cta_target_names = self._get_cta_target_names(lane, internal_link_targets)
        if not cta_target_names:
            return content

        cta_markers = (
            "if your project involves",
            "if you are comparing suppliers",
            "the next practical step",
            "the next useful step",
            "review services",
            "review about us",
            "use contact",
        )

        for match in reversed(paragraphs[-3:]):
            paragraph_html = match.group(0)
            if not any(marker in paragraph_html.lower() for marker in cta_markers):
                continue
            linked_paragraph = self._link_named_targets_in_fragment(
                paragraph_html, cta_target_names
            )
            if linked_paragraph != paragraph_html:
                return (
                    content[: match.start()]
                    + linked_paragraph
                    + content[match.end() :]
                )

        return content

    def _ensure_cta_section(
        self, content: str, internal_link_targets: str = "", lane: str = ""
    ) -> str:
        if not self.html_format or not content:
            return content

        lowered_tail = content[-1200:].lower()
        has_cta_language = any(
            phrase in lowered_tail
            for phrase in [
                "if your project involves",
                "if you are comparing suppliers",
                "the next useful step is to review",
                "before finalizing drawings",
                "before placing an order",
            ]
        )
        resolved_lane = lane.strip().lower()
        if not resolved_lane:
            lane_match = re.search(r"Lane:\s*(pillar|ordinary)", content, re.I)
            resolved_lane = lane_match.group(1).strip().lower() if lane_match else ""

        if has_cta_language:
            return content

        return content + self._build_cta_paragraph(resolved_lane, internal_link_targets)

    def _clean_html_content(self, content: str) -> str:
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r">\s+<", "><", content)
        content = html.escape(content) if "<" not in content else content
        return content.strip()

    def _generate_default_content(
        self,
        keyword: str,
        title: str,
        direction: str = "",
        lane: str = "",
        priority: str = "",
        cluster: str = "",
        internal_link_targets: str = "",
    ) -> str:
        if self.html_format:
            content = f"""<article>
    <h1>{title}</h1>
    <p>Buyers evaluating {keyword} often need more than a simple product overview. They need to understand how the choice affects production consistency, finish quality, assembly fit, and sourcing risk across real manufacturing projects.</p>
    <p>Content angle: {direction or "general"}. Lane: {lane or "standard"}. Priority: {priority or "N/A"}. Cluster: {cluster or "general"}.</p>

    <h2>Why {keyword} Matters in Production</h2>
    <p>In {self.industry.lower()}, small mistakes around materials, tolerances, finishing, or process control can create expensive downstream issues. A reliable supplier should be able to explain how {keyword.lower()} fits into production requirements instead of only providing a quotation.</p>

    <h2>Common Risks Buyers Should Watch</h2>
    <p>Common failure points include material substitution, inconsistent finishing, dimensional drift, assembly mismatch, weak inspection records, and unclear responsibility between sampling and mass production. These are the issues buyers should surface early.</p>

    <h2>What to Verify Before Ordering</h2>
    <ul>
        <li>Confirm materials, finishes, and process route in writing.</li>
        <li>Ask for inspection standards, dimensional checkpoints, and sample approval criteria.</li>
        <li>Check whether the supplier can explain production risks before mass production starts.</li>
        <li>Verify how the factory handles corrective action if defects appear.</li>
    </ul>

    <h2>How a Reliable Factory Should Support the Project</h2>
    <p>A capable factory should provide practical guidance on fit, finish, manufacturability, and QC expectations. It should also help the buyer confirm what matters most before tooling, before sample approval, and before batch release.</p>

    <h2>Conclusion</h2>
    <p>{keyword} should be evaluated as part of a broader sourcing and production decision, not as an isolated specification item. Buyers should confirm capability evidence early so that material, finish, and production-control issues do not appear after sampling or during mass production.</p>
</article>"""
        else:
            content = f"""{title}

Buyers evaluating {keyword} often need more than a simple product overview. They need to understand how the choice affects production consistency, finish quality, assembly fit, and sourcing risk.

Why {keyword} Matters in Production
In {self.industry.lower()}, small mistakes around materials, tolerances, finishing, or process control can create expensive downstream issues.

Common Risks Buyers Should Watch
Common failure points include material substitution, inconsistent finishing, dimensional drift, assembly mismatch, weak inspection records, and unclear responsibility between sampling and mass production.

What to Verify Before Ordering
- Confirm materials, finishes, and process route in writing.
- Ask for inspection standards, dimensional checkpoints, and sample approval criteria.
- Check whether the supplier can explain production risks before mass production starts.
- Verify how the factory handles corrective action if defects appear.

How a Reliable Factory Should Support the Project
A capable factory should provide practical guidance on fit, finish, manufacturability, and QC expectations.

Conclusion
{keyword} should be evaluated as part of a broader sourcing and production decision. Buyers should confirm capability evidence early so that material, finish, and production-control issues do not appear after sampling or during mass production."""

        content = self._apply_internal_links(
            content, internal_link_targets=internal_link_targets
        )
        content = self._ensure_cta_section(
            content,
            internal_link_targets=internal_link_targets,
            lane=lane,
        )
        return self._link_cta_targets(
            content,
            lane=lane,
            internal_link_targets=internal_link_targets,
        )

    def _generate_default_contents(self, inputs: List[Dict[str, str]]) -> List[str]:
        return [
            self._generate_default_content(
                inp["keyword"],
                inp["title"],
                direction=inp.get("direction", ""),
                lane=inp.get("lane", ""),
                priority=inp.get("priority", ""),
                cluster=inp.get("cluster", ""),
                internal_link_targets=inp.get("internal_link_targets", ""),
            )
            for inp in inputs
        ]

    def _log_statistics(self, contents: List[str]) -> None:
        total_words = sum(len(content.split()) for content in contents) if contents else 0
        self.logger.info(
            "AI content generation stats",
            total_inputs=self.stats["total_inputs"],
            contents_generated=self.stats["contents_generated"],
            inputs_processed=self.stats["inputs_processed"],
            inputs_failed=self.stats["inputs_failed"],
            batches_processed=self.stats["batches_processed"],
            ai_calls=self.stats["ai_calls"],
            total_tokens=self.stats["total_tokens"],
            total_cost=f"${self.stats['total_cost']:.4f}",
            total_words=total_words,
            average_word_count=f"{self.stats['average_word_count']:.1f}",
        )

    def get_statistics(self) -> Dict[str, Any]:
        return self.stats.copy()

    def validate_input(self, input_data: Any) -> bool:
        try:
            return len(self._validate_and_prepare_input(input_data)) > 0
        except Exception:
            return False

    def validate_output(self, output_data: Any) -> bool:
        if not isinstance(output_data, list) or not output_data:
            return False
        return all(isinstance(item, str) and item.strip() for item in output_data)

    def pre_execute(self, input_data: Any) -> Any:
        self.stats = {key: 0 for key in self.stats}
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        return output_data


def generate_content_with_ai(
    inputs: List[Dict[str, str]],
    batch_size: int = 5,
    target_word_count: int = 1500,
    **kwargs,
) -> Tuple[List[str], Dict[str, Any]]:
    generator = AIContentGenerator(
        node_id="content_generator_tool",
        config={
            "batch_size": batch_size,
            "target_word_count": target_word_count,
            **kwargs,
        },
    )
    contents = generator.execute_impl(inputs)
    return contents, generator.get_statistics()


__all__ = [
    "ContentGenerationResult",
    "AIContentGenerator",
    "generate_content_with_ai",
]
