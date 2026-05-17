"""
AI文章内容生成器
基于关键词和标题生成SEO优化的文章内容
"""

import json
import re
import html
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.core import AINode
from src.utils import (
    get_logger,
    config_manager,
    get_ai_client,
    create_system_message,
    create_user_message,
    AIMessage,
    AIError,
)
from config.internal_links_config import get_default_internal_link_rules


@dataclass
class ContentGenerationResult:
    """内容生成结果"""
    original_inputs: List[Dict[str, str]]  # 原始输入列表，每个元素包含 keyword 和 title
    generated_contents: List[str]  # 生成的HTML内容列表
    content_sources: Dict[str, str]  # 内容 -> 来源关键词
    confidence_scores: Dict[str, float]  # 内容 -> 置信度分数 (0-1)
    metadata: Dict[str, Any]  # 元数据


class AIContentGenerator(AINode):
    """AI文章内容生成器"""

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化AI内容生成器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - batch_size: 批量处理大小（默认: 5）
                - max_content_per_input: 每个输入最大内容数（默认: 1）
                - target_word_count: 目标字数（默认: 1500）
                - enable_fallback: 是否启用备用模型（默认: True）
                - language: 文章语言（默认: "en"）
                - industry: 目标行业（默认: "Metal Hardware & Lighting Accessories Processing"）
                - html_format: 是否输出HTML格式（默认: True）
                - include_subheadings: 是否包含小标题（默认: True）
                - include_bullet_points: 是否包含要点列表（默认: True）
                - internal_linking_enabled: 是否启用站内链接自动插入（默认: True）
                - max_internal_links_per_article: 每篇文章最多插入多少个站内链接（默认: 4）
        """
        config = config or {}
        super().__init__(node_id, "content_generator", config)

        # 配置参数
        self.batch_size = config.get("batch_size", 5)
        self.max_content_per_input = config.get("max_content_per_input", 1)
        self.target_word_count = config.get("target_word_count", 1500)
        self.enable_fallback = config.get("enable_fallback", True)
        self.language = config.get("language", "en")
        self.industry = config.get("industry", "Metal Hardware & Lighting Accessories Processing")
        self.html_format = config.get("html_format", True)
        self.include_subheadings = config.get("include_subheadings", True)
        self.include_bullet_points = config.get("include_bullet_points", True)
        self.internal_linking_enabled = config.get("internal_linking_enabled", True)
        self.max_internal_links_per_article = config.get("max_internal_links_per_article", 4)
        self.internal_link_rules = config.get(
            "internal_link_rules",
            get_default_internal_link_rules(),
        )

        # 从配置获取Prompt模板
        self.prompt_template = self._load_prompt_template()

        # 文章元数据缓存（slug, excerpt），key 为 content 字符串
        self._article_meta: Dict[str, Dict[str, str]] = {}

        # 统计数据
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

        self.logger.info(
            f"AI内容生成器初始化: {node_id}",
            config={
                "batch_size": self.batch_size,
                "target_word_count": self.target_word_count,
                "max_content_per_input": self.max_content_per_input,
                "enable_fallback": self.enable_fallback,
                "language": self.language,
                "html_format": self.html_format,
                "internal_linking_enabled": self.internal_linking_enabled,
            }
        )

    def _load_prompt_template(self) -> Dict[str, Any]:
        """加载Prompt模板"""
        try:
            prompt_name = "content_generator"
            version = config_manager.get_current_prompt_version(prompt_name)
            template = config_manager.get_prompt_template(prompt_name, version)

            self.logger.debug(
                f"加载Prompt模板: {prompt_name}",
                version=version,
                description=template.get("description")
            )

            return template

        except Exception as e:
            self.logger.warning(f"加载Prompt模板失败，使用默认模板: {e}")
            # 返回默认模板
            return {
                "system": "You are an SEO specialist and professional content writer specializing in the Metal Hardware & Lighting Accessories Processing industry. Your task is to generate high-quality, informative articles.",
                "user": "Please write a comprehensive article about '{keyword}' with the title '{title}'. The article should be approximately {word_count} words, SEO-optimized, and informative. Include relevant subheadings, bullet points where appropriate, and provide practical information for industry professionals. Output the article in HTML format with proper heading tags (<h2> for subheadings, <p> for paragraphs, <ul> for bullet lists).",
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 4000,
                }
            }

    def execute_impl(self, input_data: Any) -> Any:
        """执行内容生成

        Args:
            input_data: 输入数据，应为关键词和标题的列表或字典

        Returns:
            生成的HTML内容列表
        """
        # 验证和准备输入数据
        inputs = self._validate_and_prepare_input(input_data)

        # 分批处理
        all_contents = []
        content_sources = {}
        confidence_scores = {}
        batches = self._create_batches(inputs)

        for i, batch in enumerate(batches):
            self.logger.info(
                f"处理批次 {i + 1}/{len(batches)}",
                batch_size=len(batch),
                total_inputs=len(inputs)
            )

            try:
                batch_result = self._process_batch(batch)
                all_contents.extend(batch_result.generated_contents)
                content_sources.update(batch_result.content_sources)
                confidence_scores.update(batch_result.confidence_scores)

                self.stats["batches_processed"] += 1
                self.stats["inputs_processed"] += len(batch)

            except Exception as e:
                self.logger.error(
                    f"[AI调用失败] 内容生成节点无法连接 AI 服务。"
                    f"请检查 .env 中的 AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT 或 OPENAI_API_KEY 是否正确。"
                    f"原始错误: {e}"
                )
                # 如果启用备用模型，尝试使用备用模型
                if self.enable_fallback:
                    self.logger.info("尝试使用备用模型")
                    try:
                        batch_result = self._process_batch_with_fallback(batch)
                        all_contents.extend(batch_result.generated_contents)
                        content_sources.update(batch_result.content_sources)
                        confidence_scores.update(batch_result.confidence_scores)
                        self.stats["batches_processed"] += 1
                        self.stats["inputs_processed"] += len(batch)
                    except Exception as fallback_error:
                        self.logger.error(
                            f"[备用模型失败] 未配置 Anthropic 等备用模型，使用默认内容。"
                            f"如需备用模型，请在 config/ai_models_config.py 的 FALLBACK_MODELS 中配置。"
                        )
                        # 生成默认内容
                        default_contents = self._generate_default_contents(batch)
                        all_contents.extend(default_contents)
                        for inp, content in zip(batch, default_contents):
                            content_sources[content] = inp["keyword"]
                            confidence_scores[content] = 0.5
                        self.stats["inputs_failed"] += len(batch)
                else:
                    # 生成默认内容
                    default_contents = self._generate_default_contents(batch)
                    all_contents.extend(default_contents)
                    for inp, content in zip(batch, default_contents):
                        content_sources[content] = inp["keyword"]
                        confidence_scores[content] = 0.5
                    self.stats["inputs_failed"] += len(batch)

        # 更新平均字数统计
        if all_contents:
            total_words = sum(len(content.split()) for content in all_contents)
            self.stats["average_word_count"] = total_words / len(all_contents)

        # 记录统计信息
        self._log_statistics(all_contents)

        # 创建结果对象
        result = ContentGenerationResult(
            original_inputs=inputs,
            generated_contents=all_contents,
            content_sources=content_sources,
            confidence_scores=confidence_scores,
            metadata={
                "batches_processed": self.stats["batches_processed"],
                "ai_calls": self.stats["ai_calls"],
                "total_tokens": self.stats["total_tokens"],
                "total_cost": self.stats["total_cost"],
                "average_word_count": self.stats["average_word_count"],
            }
        )

        return all_contents

    def _validate_and_prepare_input(self, input_data: Any) -> List[Dict[str, str]]:
        """验证和准备输入数据"""
        inputs = []

        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    # 期望包含 keyword 和 title
                    keyword = item.get("keyword", "")
                    title = item.get("title", "")
                    direction = item.get("direction", item.get("title_angle", item.get("pillar_direction", "")))
                    lane = item.get("lane", "")
                    internal_link_targets = item.get("internal_link_targets", "")
                    if keyword and title:
                        inputs.append({
                            "keyword": str(keyword).strip(),
                            "title": str(title).strip(),
                            "direction": str(direction).strip(),
                            "lane": str(lane).strip(),
                            "internal_link_targets": str(internal_link_targets).strip(),
                        })
                    elif keyword:
                        # 只有关键词，使用默认标题
                        default_title = f"Complete Guide to {keyword}"
                        inputs.append({
                            "keyword": str(keyword).strip(),
                            "title": default_title,
                            "direction": str(direction).strip(),
                            "lane": str(lane).strip(),
                            "internal_link_targets": str(internal_link_targets).strip(),
                        })
                    else:
                        self.logger.warning(f"跳过无效的字典项: {item}")
                elif isinstance(item, str):
                    # 只有关键词字符串
                    inputs.append({"keyword": item.strip(), "title": f"Complete Guide to {item.strip()}", "direction": "", "lane": "", "internal_link_targets": ""})
                else:
                    self.logger.warning(f"跳过不支持的类型: {type(item)}")

        elif isinstance(input_data, dict):
            # 单个字典输入
            keyword = input_data.get("keyword", "")
            title = input_data.get("title", "")
            direction = input_data.get("direction", input_data.get("title_angle", input_data.get("pillar_direction", "")))
            lane = input_data.get("lane", "")
            internal_link_targets = input_data.get("internal_link_targets", "")
            if keyword:
                inputs.append({
                    "keyword": str(keyword).strip(),
                    "title": str(title).strip() if title else f"Complete Guide to {keyword}",
                    "direction": str(direction).strip(),
                    "lane": str(lane).strip(),
                    "internal_link_targets": str(internal_link_targets).strip(),
                })

        elif isinstance(input_data, str):
            # 尝试解析JSON字符串
            if input_data.startswith("[") and input_data.endswith("]"):
                try:
                    data = json.loads(input_data)
                    return self._validate_and_prepare_input(data)
                except json.JSONDecodeError:
                    # 作为单个关键词处理
                    inputs.append({"keyword": input_data.strip(), "title": f"Complete Guide to {input_data.strip()}"})
            else:
                # 单个关键词字符串
                inputs.append({"keyword": input_data.strip(), "title": f"Complete Guide to {input_data.strip()}"})

        else:
            raise ValueError(f"不支持的输入数据类型: {type(input_data)}")

        if not inputs:
            raise ValueError("输入数据为空或无效")

        self.stats["total_inputs"] = len(inputs)
        self.logger.info(f"输入验证通过，共 {len(inputs)} 个输入")
        return inputs

    def _create_batches(self, inputs: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """创建处理批次"""
        batch_size = min(self.batch_size, 10)  # 限制最大批次大小（文章生成较耗时）
        batches = []

        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            batches.append(batch)

        self.logger.debug(f"创建 {len(batches)} 个批次，每批最多 {batch_size} 个输入")
        return batches

    def _process_batch(self, batch: List[Dict[str, str]]) -> ContentGenerationResult:
        """处理单个批次"""
        generated_contents = []
        content_sources = {}
        confidence_scores = {}

        for input_item in batch:
            keyword = input_item["keyword"]
            title = input_item["title"]
            category = input_item.get("category", "")
            direction = input_item.get("direction", "")
            lane = input_item.get("lane", "")
            internal_link_targets = input_item.get("internal_link_targets", "")

            try:
                # 为每个输入生成内容
                contents = self._generate_content_for_input(keyword, title, category, direction=direction, lane=lane, internal_link_targets=internal_link_targets)

                if contents:
                    generated_contents.extend(contents)
                    for content in contents:
                        content_sources[content] = keyword
                        confidence_scores[content] = 0.9  # 高置信度
                    self.stats["contents_generated"] += len(contents)
                else:
                    # 生成默认内容
                    default_content = self._generate_default_content(keyword, title, direction=direction, lane=lane)
                    generated_contents.append(default_content)
                    content_sources[default_content] = keyword
                    confidence_scores[default_content] = 0.5  # 中等置信度
                    self.logger.warning(f"AI内容生成失败，使用默认内容: {keyword}")

            except Exception as e:
                self.logger.error(f"内容生成失败: {keyword}, 错误: {e}")
                # 生成默认内容
                default_content = self._generate_default_content(keyword, title, direction=direction, lane=lane)
                generated_contents.append(default_content)
                content_sources[default_content] = keyword
                confidence_scores[default_content] = 0.3  # 低置信度

        return ContentGenerationResult(
            original_inputs=batch,
            generated_contents=generated_contents,
            content_sources=content_sources,
            confidence_scores=confidence_scores,
            metadata={}
        )

    def _process_batch_with_fallback(self, batch: List[Dict[str, str]]) -> ContentGenerationResult:
        """使用备用模型处理批次"""
        # 当前实现与主模型相同，但使用备用AI客户端
        # 在实际应用中，这里可以调用不同的AI模型
        return self._process_batch(batch)

    def _generate_content_for_input(self, keyword: str, title: str, category: str = "", direction: str = "", lane: str = "", internal_link_targets: str = "") -> List[str]:
        """为单个输入生成内容"""
        # 准备消息（根据分类选择 Prompt）
        messages = self._prepare_messages(keyword, title, category, direction=direction, lane=lane, internal_link_targets=internal_link_targets)

        # 获取分类对应的 prompt 模板参数
        prompt_tpl = self._get_prompt_for_category(category)

        # 获取AI客户端
        ai_client = get_ai_client("content_generator", use_fallback=False)

        # 获取模型参数
        temperature = prompt_tpl.get("parameters", {}).get("temperature", 0.7)
        max_tokens = prompt_tpl.get("parameters", {}).get("max_tokens", 4000)

        # 调用AI
        self.logger.debug(f"调用AI生成内容: {keyword} - {title}", direction=direction, lane=lane)
        response = ai_client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # 更新统计
        self.stats["ai_calls"] += 1
        self.stats["total_tokens"] += response.usage.get("total_tokens", 0)
        self.stats["total_cost"] += response.cost

        # 解析响应
        content = self._parse_ai_response(response.content)

        # 限制内容数量
        contents = [content]  # 目前每个输入只生成一个内容
        if len(contents) > self.max_content_per_input:
            contents = contents[:self.max_content_per_input]

        self.logger.debug(
            f"内容生成完成",
            keyword=keyword,
            title=title,
            word_count=len(content.split()),
            tokens_used=response.usage.get("total_tokens", 0),
            cost=response.cost
        )

        return contents

    def _prepare_messages(self, keyword: str, title: str, category: str = "", direction: str = "", lane: str = "", internal_link_targets: str = "") -> List[AIMessage]:
        """准备AI消息（根据分类选择 Prompt）"""
        prompt_tpl = self._get_prompt_for_category(category)
        system_prompt = prompt_tpl.get("system", "")
        user_prompt_template = prompt_tpl.get("user", "")

        # 格式化用户提示
        user_prompt = user_prompt_template.format(
            keyword=keyword,
            title=title,
            word_count=self.target_word_count,
            industry=self.industry,
            language=self.language,
            direction=direction,
            title_angle=direction,
            lane=lane,
            internal_link_targets=internal_link_targets,
        )

        # 创建消息
        messages = [
            create_system_message(system_prompt),
            create_user_message(user_prompt)
        ]

        return messages

    def _get_prompt_for_category(self, category: str) -> Dict[str, Any]:
        """根据分类名称获取对应的 Prompt 模板"""
        try:
            from config.prompts_config import CATEGORY_PROMPTS
            if category and category in CATEGORY_PROMPTS:
                return CATEGORY_PROMPTS[category]
        except ImportError:
            pass
        return self.prompt_template

    def _parse_ai_response(self, ai_response: str) -> str:
        """解析AI响应，提取HTML内容、slug和excerpt"""
        content = ai_response.strip()
        extracted_slug = ""
        extracted_excerpt = ""

        # 尝试解析JSON格式响应（prompt要求输出JSON）
        try:
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = content[json_start:json_end + 1]
                data = json.loads(json_str)
                if isinstance(data, dict) and "content" in data:
                    content = data.get("content", "").strip()
                    extracted_slug = data.get("slug", "").strip()
                    extracted_excerpt = data.get("excerpt", "").strip()
                    self.logger.debug(f"从JSON提取: slug={extracted_slug}, excerpt={extracted_excerpt[:50]}...")
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.debug(f"JSON解析失败，尝试HTML提取: {e}")

        # 尝试提取<body>标签内的内容
        body_pattern = r'<body[^>]*>(.*?)</body>'
        body_match = re.search(body_pattern, content, re.DOTALL | re.IGNORECASE)

        if body_match:
            content = body_match.group(1).strip()
        else:
            html_pattern = r'<html[^>]*>(.*?)</html>'
            html_match = re.search(html_pattern, content, re.DOTALL | re.IGNORECASE)
            if html_match:
                content = html_match.group(1).strip()

        # 清理内容
        content = self._clean_html_content(content)

        # 确保是有效的HTML
        if self.html_format:
            if not content.startswith('<'):
                content = f'<article>{content}</article>'
            elif not re.search(r'<html|<body|<article|<div|<h\d|<p|<ul|<ol', content, re.IGNORECASE):
                content = f'<article>{content}</article>'

        content = self._apply_internal_links(content)

        # 在最终内容上缓存 slug 和 excerpt（key 为最终返回的 content 字符串）
        if extracted_slug or extracted_excerpt:
            self._article_meta[content] = {
                "slug": extracted_slug,
                "excerpt": extracted_excerpt,
            }

        return content

    def _apply_internal_links(self, content: str) -> str:
        """根据内链规则自动插入站内链接"""
        if not self.internal_linking_enabled or not self.html_format or not content:
            return content

        tokens = re.split(r'(<[^>]+>)', content)
        used_urls: set = set()
        inserted_count = 0
        in_anchor = False

        for index, token in enumerate(tokens):
            if token.startswith("<"):
                token_lower = token.lower()
                if token_lower.startswith("<a ") or token_lower.startswith("<a>"):
                    in_anchor = True
                elif token_lower.startswith("</a"):
                    in_anchor = False
                continue

            if in_anchor or inserted_count >= self.max_internal_links_per_article:
                continue

            updated_token = token
            for rule in self.internal_link_rules:
                url = rule.get("url", "")
                if not url or url in used_urls:
                    continue

                replaced_token, replaced = self._replace_first_internal_link(updated_token, rule)
                if replaced:
                    updated_token = replaced_token
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
                'Learn more from our <a href="https://yushengco.com/">home page</a>.'
                '</p>'
            )

        return content_with_links

    def _replace_first_internal_link(self, text: str, rule: Dict[str, Any]) -> Tuple[str, bool]:
        """在文本中替换第一个命中的关键词为内链"""
        url = rule.get("url", "")
        phrases = rule.get("phrases", [])

        if not url or not phrases:
            return text, False

        ordered_phrases = sorted([phrase for phrase in phrases if phrase], key=len, reverse=True)

        for phrase in ordered_phrases:
            pattern = re.compile(rf'(?<!\w)({re.escape(phrase)})(?!\w)', re.IGNORECASE)

            def _replacement(match: re.Match) -> str:
                matched_text = match.group(1)
                return f'<a href="{url}">{matched_text}</a>'

            replaced_text, count = pattern.subn(_replacement, text, count=1)
            if count > 0:
                return replaced_text, True

        return text, False

    def _clean_html_content(self, content: str) -> str:
        """清理HTML内容"""
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'>\s+<', '><', content)

        # 确保HTML标签正确闭合（简单处理）
        # 这里可以添加更复杂的HTML清理逻辑

        # 转义特殊字符（如果未转义）
        content = html.escape(content) if '<' not in content else content

        return content.strip()

    def _generate_default_content(self, keyword: str, title: str, direction: str = "", lane: str = "") -> str:
        """生成默认内容"""
        # 简单的文章模板
        if self.html_format:
            content = f'''<article>
    <h1>{title}</h1>
    <p>This comprehensive guide provides detailed information about {keyword} in the {self.industry} industry.</p>
    <p>Content angle: {direction or "general"}. Lane: {lane or "standard"}.</p>

    <h2>Introduction to {keyword}</h2>
    <p>{keyword} plays a crucial role in modern {self.industry.lower()} applications. Understanding its features and applications is essential for industry professionals.</p>

    <h2>Key Features and Benefits</h2>
    <ul>
        <li>High durability and reliability</li>
        <li>Cost-effective solutions</li>
        <li>Wide range of applications</li>
        <li>Easy installation and maintenance</li>
    </ul>

    <h2>Applications in {self.industry}</h2>
    <p>{keyword} is widely used across various segments of the {self.industry} sector. Its versatility makes it suitable for multiple applications.</p>

    <h2>Selection Criteria</h2>
    <p>When selecting {keyword.lower()}, consider factors such as material quality, compatibility, and specific application requirements.</p>

    <h2>Maintenance and Care</h2>
    <p>Proper maintenance ensures optimal performance and longevity of {keyword.lower()} in industrial settings.</p>

    <h2>Conclusion</h2>
    <p>{keyword} remains an essential component in the {self.industry} industry, offering reliable performance and value for various applications.</p>
</article>'''
        else:
            content = f'''{title}

This comprehensive guide provides detailed information about {keyword} in the {self.industry} industry.

Introduction to {keyword}
{keyword} plays a crucial role in modern {self.industry.lower()} applications. Understanding its features and applications is essential for industry professionals.

Key Features and Benefits
- High durability and reliability
- Cost-effective solutions
- Wide range of applications
- Easy installation and maintenance

Applications in {self.industry}
{keyword} is widely used across various segments of the {self.industry} sector. Its versatility makes it suitable for multiple applications.

Selection Criteria
When selecting {keyword.lower()}, consider factors such as material quality, compatibility, and specific application requirements.

Maintenance and Care
Proper maintenance ensures optimal performance and longevity of {keyword.lower()} in industrial settings.

Conclusion
{keyword} remains an essential component in the {self.industry} industry, offering reliable performance and value for various applications.'''

        content = self._apply_internal_links(content)

        self.logger.debug(f"生成默认内容: {keyword} -> {title}", direction=direction, lane=lane)
        return content

    def _generate_default_contents(self, inputs: List[Dict[str, str]]) -> List[str]:
        """为输入列表生成默认内容"""
        return [self._generate_default_content(inp["keyword"], inp["title"]) for inp in inputs]

    def _log_statistics(self, contents: List[str]) -> None:
        """记录统计信息"""
        # 计算成功率
        if self.stats["total_inputs"] > 0:
            success_rate = self.stats["inputs_processed"] / self.stats["total_inputs"] * 100
        else:
            success_rate = 0

        # 计算总字数
        total_words = sum(len(content.split()) for content in contents) if contents else 0

        self.logger.info(
            "AI内容生成统计",
            total_inputs=self.stats["total_inputs"],
            contents_generated=self.stats["contents_generated"],
            inputs_processed=self.stats["inputs_processed"],
            inputs_failed=self.stats["inputs_failed"],
            success_rate=f"{success_rate:.1f}%",
            batches_processed=self.stats["batches_processed"],
            ai_calls=self.stats["ai_calls"],
            total_tokens=self.stats["total_tokens"],
            total_cost=f"${self.stats['total_cost']:.4f}",
            total_words=total_words,
            average_word_count=f"{self.stats['average_word_count']:.1f}",
            final_contents=len(contents)
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        try:
            inputs = self._validate_and_prepare_input(input_data)
            return len(inputs) > 0
        except Exception as e:
            self.logger.warning(f"输入验证失败: {e}")
            return False

    def validate_output(self, output_data: Any) -> bool:
        """验证输出数据"""
        if not isinstance(output_data, list):
            self.logger.warning(f"输出数据不是列表: {type(output_data)}")
            return False

        # 检查列表中的元素是否都是字符串
        for i, item in enumerate(output_data):
            if not isinstance(item, str):
                self.logger.warning(f"输出数据包含非字符串元素: 索引 {i}, 类型 {type(item)}")
                return False

            if not item.strip():
                self.logger.warning(f"输出数据包含空字符串: 索引 {i}")
                return False

        return True

    def pre_execute(self, input_data: Any) -> Any:
        """执行前处理"""
        self.logger.info("开始AI内容生成")
        self.stats = {k: 0 for k in self.stats}  # 重置统计
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.info(f"AI内容生成完成，生成 {len(output_data)} 个内容")
        return output_data


# 工具函数
def generate_content_with_ai(
    inputs: List[Dict[str, str]],
    batch_size: int = 5,
    target_word_count: int = 1500,
    **kwargs
) -> Tuple[List[str], Dict[str, Any]]:
    """
    使用AI生成内容的便捷函数

    Args:
        inputs: 输入列表，每个元素应包含 "keyword" 和 "title"
        batch_size: 批量大小
        target_word_count: 目标字数
        **kwargs: 其他AIContentGenerator配置参数

    Returns:
        (生成的HTML内容列表, 统计信息字典)
    """
    content_generator = AIContentGenerator(
        node_id="content_generator_tool",
        config={
            "batch_size": batch_size,
            "target_word_count": target_word_count,
            **kwargs
        }
    )

    generated_contents = content_generator.execute_impl(inputs)
    stats = content_generator.get_statistics()

    return generated_contents, stats


__all__ = [
    "ContentGenerationResult",
    "AIContentGenerator",
    "generate_content_with_ai",
]