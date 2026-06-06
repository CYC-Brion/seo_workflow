"""
AI title generation module for the SEO workflow.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.core import AINode
from src.utils import (
    AIMessage,
    config_manager,
    create_system_message,
    create_user_message,
    get_ai_client,
    get_logger,
)


@dataclass
class TitleGenerationResult:
    original_keywords: List[Dict[str, str]]
    generated_titles: List[str]
    title_sources: Dict[str, str]
    confidence_scores: Dict[str, float]
    metadata: Dict[str, Any]


class AITitleGenerator(AINode):
    """Generate article titles from keyword inputs."""

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(node_id, "title_generator", config)

        self.batch_size = config.get("batch_size", 10)
        self.max_titles_per_keyword = config.get("max_titles_per_keyword", 1)
        self.title_length_range = config.get("title_length_range", [5, 15])
        self.enable_fallback = config.get("enable_fallback", True)
        self.language = config.get("language", "en")
        self.industry = config.get(
            "industry", "Metal Hardware & Lighting Accessories Processing"
        )
        self.prompt_template = self._load_prompt_template()
        self.stats = {
            "total_keywords": 0,
            "titles_generated": 0,
            "keywords_processed": 0,
            "keywords_failed": 0,
            "batches_processed": 0,
            "ai_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }
        self.logger = get_logger(f"title_generator.{node_id}")

    def _load_prompt_template(self) -> Dict[str, Any]:
        try:
            prompt_name = "title_generator"
            version = config_manager.get_current_prompt_version(prompt_name)
            return config_manager.get_prompt_template(prompt_name, version)
        except Exception:
            return {
                "system": (
                    "You are an SEO specialist and professional content writer. "
                    "Generate SEO titles for the Metal Hardware & Lighting Accessories "
                    "Processing industry."
                ),
                "user": (
                    "Generate {max_titles} SEO title(s) for '{keyword}'. Keep the title "
                    "engaging and between {min_words} and {max_words} words."
                ),
                "parameters": {"temperature": 0.7, "max_tokens": 500},
            }

    def execute_impl(self, input_data: Any) -> Any:
        keywords = self._validate_and_prepare_input(input_data)
        all_titles: List[str] = []
        title_sources: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}

        for batch in self._create_batches(keywords):
            batch_result = self._process_batch(batch)
            all_titles.extend(batch_result.generated_titles)
            title_sources.update(batch_result.title_sources)
            confidence_scores.update(batch_result.confidence_scores)
            self.stats["batches_processed"] += 1
            self.stats["keywords_processed"] += len(batch)

        self._log_statistics(all_titles)
        return all_titles

    def _validate_and_prepare_input(self, input_data: Any) -> List[Dict[str, str]]:
        keywords: List[Dict[str, str]] = []

        def build_keyword(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
            keyword = str(item.get("keyword", item.get("keywords", ""))).strip()
            if not keyword:
                return None
            return {
                "keyword": keyword,
                "direction": str(
                    item.get("direction", item.get("title_angle", item.get("pillar_direction", "")))
                ).strip(),
                "lane": str(item.get("lane", "")).strip(),
                "priority": str(item.get("priority", "")).strip(),
                "cluster": str(item.get("cluster", "")).strip(),
                "internal_link_targets": str(item.get("internal_link_targets", "")).strip(),
            }

        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    built = build_keyword(item)
                    if built:
                        keywords.append(built)
                elif isinstance(item, str) and item.strip():
                    built = build_keyword({"keyword": item})
                    if built:
                        keywords.append(built)
        elif isinstance(input_data, str):
            if input_data.startswith("[") and input_data.endswith("]"):
                try:
                    return self._validate_and_prepare_input(json.loads(input_data))
                except json.JSONDecodeError:
                    pass
            parts = re.split(r"[,\n]", input_data)
            for part in parts:
                built = build_keyword({"keyword": part})
                if built:
                    keywords.append(built)
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")

        if not keywords:
            raise ValueError("Keyword input is empty")

        self.stats["total_keywords"] = len(keywords)
        return keywords

    def _create_batches(self, keywords: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        batch_size = min(self.batch_size, 20)
        return [keywords[i : i + batch_size] for i in range(0, len(keywords), batch_size)]

    def _process_batch(self, batch: List[Dict[str, str]]) -> TitleGenerationResult:
        generated_titles: List[str] = []
        title_sources: Dict[str, str] = {}
        confidence_scores: Dict[str, float] = {}

        for input_item in batch:
            keyword = input_item["keyword"]
            try:
                titles = self._generate_titles_for_keyword(
                    keyword=keyword,
                    direction=input_item.get("direction", ""),
                    lane=input_item.get("lane", ""),
                    priority=input_item.get("priority", ""),
                    cluster=input_item.get("cluster", ""),
                    internal_link_targets=input_item.get("internal_link_targets", ""),
                )
            except Exception:
                titles = [
                    self._generate_default_title(
                        keyword,
                        direction=input_item.get("direction", ""),
                        lane=input_item.get("lane", ""),
                        priority=input_item.get("priority", ""),
                    )
                ]

            generated_titles.extend(titles)
            for title in titles:
                title_sources[title] = keyword
                confidence_scores[title] = 0.9
            self.stats["titles_generated"] += len(titles)

        return TitleGenerationResult(
            original_keywords=batch,
            generated_titles=generated_titles,
            title_sources=title_sources,
            confidence_scores=confidence_scores,
            metadata={},
        )

    def _process_batch_with_fallback(
        self, batch: List[Dict[str, str]]
    ) -> TitleGenerationResult:
        return self._process_batch(batch)

    def _generate_titles_for_keyword(
        self,
        keyword: str,
        direction: str = "",
        lane: str = "",
        priority: str = "",
        cluster: str = "",
        internal_link_targets: str = "",
    ) -> List[str]:
        messages = self._prepare_messages(
            keyword=keyword,
            direction=direction,
            lane=lane,
            priority=priority,
            cluster=cluster,
            internal_link_targets=internal_link_targets,
        )
        response = get_ai_client("title_generator", use_fallback=False).chat_completion(
            messages=messages,
            temperature=self.prompt_template.get("parameters", {}).get("temperature", 0.7),
            max_tokens=self.prompt_template.get("parameters", {}).get("max_tokens", 500),
        )

        self.stats["ai_calls"] += 1
        self.stats["total_tokens"] += response.usage.get("total_tokens", 0)
        self.stats["total_cost"] += response.cost

        titles = self._parse_ai_response(response.content)
        return titles[: self.max_titles_per_keyword]

    def _prepare_messages(
        self,
        keyword: str,
        direction: str = "",
        lane: str = "",
        priority: str = "",
        cluster: str = "",
        internal_link_targets: str = "",
    ) -> List[AIMessage]:
        min_words, max_words = self.title_length_range
        user_prompt = self.prompt_template.get("user", "").format(
            keyword=keyword,
            max_titles=self.max_titles_per_keyword,
            min_words=min_words,
            max_words=max_words,
            direction=direction,
            title_angle=direction,
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
            context_lines.append(
                f"- Relevant downstream pages or CTA targets: {internal_link_targets}"
            )
        if lane.lower() == "pillar":
            context_lines.append(
                "- Angle preference: supplier comparison, sourcing checklist, buyer mistakes, decision confidence, or factory capability review."
            )
        elif lane:
            context_lines.append(
                "- Angle preference: specific technical subtopic, specs, process, QC, finish, tolerance, or application."
            )
        if priority.upper() == "A":
            context_lines.append(
                "- Commercial emphasis: high. Prefer stronger buyer-intent, evaluation, and sourcing-decision framing."
            )
        if cluster:
            context_lines.append(
                "- Differentiate this title from other content in the same cluster. Avoid generic repeated headline patterns."
            )

        if context_lines:
            user_prompt += "\n\n# Workflow Context\n" + "\n".join(context_lines)

        return [
            create_system_message(self.prompt_template.get("system", "")),
            create_user_message(user_prompt),
        ]

    def _parse_ai_response(self, ai_response: str) -> List[str]:
        titles: List[str] = []
        for pattern in [r"```json\n(.*?)\n```", r"\[.*?\]"]:
            matches = re.findall(pattern, ai_response, re.S)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        titles.extend(str(item).strip() for item in data)
                except json.JSONDecodeError:
                    pass

        if not titles:
            matches = re.findall(r"(?:^|\n)[\-*\d\.]+\.?\s*(.+?)(?=\n|$)", ai_response, re.M)
            titles.extend(match.strip() for match in matches)

        if not titles:
            for line in ai_response.strip().split("\n"):
                line = re.sub(r"^[\-*\d\.]+\.?\s*", "", line.strip())
                if line and not line.startswith("#"):
                    titles.append(line)

        unique_titles: List[str] = []
        seen = set()
        for title in titles:
            cleaned = re.sub(r"^\*{1,2}(.+?)\*{1,2}$", r"\1", title.strip().strip("\"'"))
            cleaned = cleaned.strip("* \t")
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                unique_titles.append(cleaned)
        return unique_titles

    def _generate_default_title(
        self,
        keyword: str,
        direction: str = "",
        lane: str = "",
        priority: str = "",
    ) -> str:
        if lane.lower() == "pillar":
            if direction:
                return f"How to Evaluate {keyword}: {direction}"
            return f"How to Choose the Right {keyword} for Your Project"
        if priority.upper() == "A":
            if direction:
                return f"{keyword}: {direction} Before You Place an Order"
            return f"What Buyers Should Check Before Ordering {keyword}"
        if direction:
            return f"{keyword}: {direction}"
        return f"Practical Guide to {keyword}"

    def _generate_default_titles(self, keywords: List[Dict[str, str]]) -> List[str]:
        return [
            self._generate_default_title(
                item["keyword"],
                item.get("direction", ""),
                lane=item.get("lane", ""),
                priority=item.get("priority", ""),
            )
            for item in keywords
        ]

    def _log_statistics(self, titles: List[str]) -> None:
        self.logger.info(
            "AI title generation stats",
            total_keywords=self.stats["total_keywords"],
            titles_generated=self.stats["titles_generated"],
            keywords_processed=self.stats["keywords_processed"],
            keywords_failed=self.stats["keywords_failed"],
            batches_processed=self.stats["batches_processed"],
            ai_calls=self.stats["ai_calls"],
            total_tokens=self.stats["total_tokens"],
            total_cost=f"${self.stats['total_cost']:.4f}",
            final_titles=len(titles),
        )

    def get_statistics(self) -> Dict[str, Any]:
        return self.stats.copy()

    def validate_input(self, input_data: Any) -> bool:
        try:
            return len(self._validate_and_prepare_input(input_data)) > 0
        except Exception:
            return False

    def validate_output(self, output_data: Any) -> bool:
        if not isinstance(output_data, list):
            return False
        return all(isinstance(item, str) and item.strip() for item in output_data)

    def pre_execute(self, input_data: Any) -> Any:
        self.stats = {key: 0 for key in self.stats}
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        return output_data


def generate_titles_with_ai(
    keywords: List[Any],
    batch_size: int = 10,
    max_titles_per_keyword: int = 1,
    **kwargs,
) -> Tuple[List[str], Dict[str, Any]]:
    generator = AITitleGenerator(
        node_id="title_generator_tool",
        config={
            "batch_size": batch_size,
            "max_titles_per_keyword": max_titles_per_keyword,
            **kwargs,
        },
    )
    titles = generator.execute_impl(keywords)
    return titles, generator.get_statistics()


__all__ = [
    "TitleGenerationResult",
    "AITitleGenerator",
    "generate_titles_with_ai",
]
