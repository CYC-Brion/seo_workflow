"""
AI文章标题生成器
基于关键词生成SEO优化的文章标题
"""

import json
import re
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


@dataclass
class TitleGenerationResult:
    """标题生成结果"""
    original_keywords: List[str]  # 原始关键词
    generated_titles: List[str]  # 生成的标题
    title_sources: Dict[str, str]  # 标题 -> 来源关键词
    confidence_scores: Dict[str, float]  # 标题 -> 置信度分数 (0-1)
    metadata: Dict[str, Any]  # 元数据


class AITitleGenerator(AINode):
    """AI文章标题生成器"""

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化AI标题生成器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - batch_size: 批量处理大小（默认: 10）
                - max_titles_per_keyword: 每个关键词最大标题数（默认: 1）
                - title_length_range: 标题长度范围，如 [5, 15] 表示5-15个单词
                - enable_fallback: 是否启用备用模型（默认: True）
                - language: 标题语言（默认: "en"）
                - industry: 目标行业（默认: "Metal Hardware & Lighting Accessories Processing"）
        """
        config = config or {}
        super().__init__(node_id, "title_generator", config)

        # 配置参数
        self.batch_size = config.get("batch_size", 10)
        self.max_titles_per_keyword = config.get("max_titles_per_keyword", 1)
        self.title_length_range = config.get("title_length_range", [5, 15])
        self.enable_fallback = config.get("enable_fallback", True)
        self.language = config.get("language", "en")
        self.industry = config.get("industry", "Metal Hardware & Lighting Accessories Processing")

        # 从配置获取Prompt模板
        self.prompt_template = self._load_prompt_template()

        # 统计数据
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

        self.logger.info(
            f"AI标题生成器初始化: {node_id}",
            config={
                "batch_size": self.batch_size,
                "max_titles_per_keyword": self.max_titles_per_keyword,
                "enable_fallback": self.enable_fallback,
                "language": self.language,
            }
        )

    def _load_prompt_template(self) -> Dict[str, Any]:
        """加载Prompt模板"""
        try:
            prompt_name = "title_generator"
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
                "system": "You are an SEO specialist and professional content writer. Your main task is to generate SEO-optimized article titles for the Metal Hardware & Lighting Accessories Processing industry.",
                "user": "Please generate {max_titles} SEO-optimized article title(s) for the following keyword: '{keyword}'. The title should be engaging, include the keyword naturally, and be between {min_words} and {max_words} words. Return only the title(s) as a list.",
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 500,
                }
            }

    def execute_impl(self, input_data: Any) -> Any:
        """执行标题生成

        Args:
            input_data: 输入数据，应为关键词列表

        Returns:
            生成的标题列表
        """
        # 验证输入数据
        keywords = self._validate_and_prepare_input(input_data)

        # 分批处理
        all_titles = []
        title_sources = {}
        confidence_scores = {}
        batches = self._create_batches(keywords)

        for i, batch in enumerate(batches):
            self.logger.info(
                f"处理批次 {i + 1}/{len(batches)}",
                batch_size=len(batch),
                total_keywords=len(keywords)
            )

            try:
                batch_result = self._process_batch(batch)
                all_titles.extend(batch_result.generated_titles)
                title_sources.update(batch_result.title_sources)
                confidence_scores.update(batch_result.confidence_scores)

                self.stats["batches_processed"] += 1
                self.stats["keywords_processed"] += len(batch)

            except Exception as e:
                self.logger.error(
                    f"[AI调用失败] 标题生成节点无法连接 AI 服务。"
                    f"请检查 .env 中的 AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT 或 OPENAI_API_KEY 是否正确。"
                    f"原始错误: {e}"
                )
                # 如果启用备用模型，尝试使用备用模型
                if self.enable_fallback:
                    self.logger.info("尝试使用备用模型")
                    try:
                        batch_result = self._process_batch_with_fallback(batch)
                        all_titles.extend(batch_result.generated_titles)
                        title_sources.update(batch_result.title_sources)
                        confidence_scores.update(batch_result.confidence_scores)
                        self.stats["batches_processed"] += 1
                        self.stats["keywords_processed"] += len(batch)
                    except Exception as fallback_error:
                        self.logger.error(
                            f"[备用模型失败] 未配置 Anthropic 等备用模型，使用默认标题。"
                            f"如需备用模型，请在 config/ai_models_config.py 的 FALLBACK_MODELS 中配置。"
                        )
                        # 生成默认标题
                        default_titles = self._generate_default_titles(batch)
                        all_titles.extend(default_titles)
                        for kw, title in zip(batch, default_titles):
                            title_sources[title] = kw
                            confidence_scores[title] = 0.5
                        self.stats["keywords_failed"] += len(batch)
                else:
                    # 生成默认标题
                    default_titles = self._generate_default_titles(batch)
                    all_titles.extend(default_titles)
                    for kw, title in zip(batch, default_titles):
                        title_sources[title] = kw
                        confidence_scores[title] = 0.5
                    self.stats["keywords_failed"] += len(batch)

        # 记录统计信息
        self._log_statistics(all_titles)

        # 创建结果对象
        result = TitleGenerationResult(
            original_keywords=keywords,
            generated_titles=all_titles,
            title_sources=title_sources,
            confidence_scores=confidence_scores,
            metadata={
                "batches_processed": self.stats["batches_processed"],
                "ai_calls": self.stats["ai_calls"],
                "total_tokens": self.stats["total_tokens"],
                "total_cost": self.stats["total_cost"],
            }
        )

        return all_titles

    def _validate_and_prepare_input(self, input_data: Any) -> List[Dict[str, str]]:
        """验证和准备输入数据"""
        keywords: List[Dict[str, str]] = []
        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    keyword = str(item.get("keyword", item.get("keywords", ""))).strip()
                    if not keyword:
                        continue
                    keywords.append({
                        "keyword": keyword,
                        "direction": str(item.get("direction", item.get("title_angle", item.get("pillar_direction", "")))).strip(),
                    })
                else:
                    keyword = str(item).strip()
                    if keyword:
                        keywords.append({"keyword": keyword, "direction": ""})
        elif isinstance(input_data, str):
            # 尝试解析字符串为列表
            if input_data.startswith("[") and input_data.endswith("]"):
                try:
                    parsed = json.loads(input_data)
                    return self._validate_and_prepare_input(parsed)
                except json.JSONDecodeError:
                    keyword = input_data.strip()
                    if keyword:
                        keywords = [{"keyword": keyword, "direction": ""}]
            else:
                # 按逗号或换行分割
                parts = re.split(r'[,\n]', input_data)
                keywords = [{"keyword": kw.strip(), "direction": ""} for kw in parts if kw.strip()]
        else:
            raise ValueError(f"不支持的输入数据类型: {type(input_data)}")

        if not keywords:
            raise ValueError("输入关键词列表为空")

        self.stats["total_keywords"] = len(keywords)
        self.logger.info(f"输入验证通过，共 {len(keywords)} 个关键词")
        return keywords

    def _create_batches(self, keywords: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """创建处理批次"""
        batch_size = min(self.batch_size, 20)  # 限制最大批次大小
        batches = []

        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]
            batches.append(batch)

        self.logger.debug(f"创建 {len(batches)} 个批次，每批最多 {batch_size} 个关键词")
        return batches

    def _process_batch(self, batch: List[Dict[str, str]]) -> TitleGenerationResult:
        """处理单个批次"""
        generated_titles = []
        title_sources = {}
        confidence_scores = {}

        for input_item in batch:
            keyword = input_item["keyword"]
            direction = input_item.get("direction", "")
            try:
                # 为每个关键词生成标题
                titles = self._generate_titles_for_keyword(keyword, direction=direction)

                if titles:
                    generated_titles.extend(titles)
                    for title in titles:
                        title_sources[title] = keyword
                        confidence_scores[title] = 0.9  # 高置信度
                    self.stats["titles_generated"] += len(titles)
                else:
                    # 生成默认标题
                    default_title = self._generate_default_title(keyword, direction=direction)
                    generated_titles.append(default_title)
                    title_sources[default_title] = keyword
                    confidence_scores[default_title] = 0.5  # 中等置信度
                    self.logger.warning(f"AI标题生成失败，使用默认标题: {keyword}")

            except Exception as e:
                self.logger.error(f"关键词标题生成失败: {keyword}, 错误: {e}")
                # 生成默认标题
                default_title = self._generate_default_title(keyword, direction=direction)
                generated_titles.append(default_title)
                title_sources[default_title] = keyword
                confidence_scores[default_title] = 0.3  # 低置信度

        return TitleGenerationResult(
            original_keywords=batch,
            generated_titles=generated_titles,
            title_sources=title_sources,
            confidence_scores=confidence_scores,
            metadata={}
        )

    def _process_batch_with_fallback(self, batch: List[Dict[str, str]]) -> TitleGenerationResult:
        """使用备用模型处理批次"""
        # 当前实现与主模型相同，但使用备用AI客户端
        # 在实际应用中，这里可以调用不同的AI模型
        return self._process_batch(batch)

    def _generate_titles_for_keyword(self, keyword: str, direction: str = "") -> List[str]:
        """为单个关键词生成标题"""
        # 准备消息
        messages = self._prepare_messages(keyword, direction=direction)

        # 获取AI客户端
        ai_client = get_ai_client("title_generator", use_fallback=False)

        # 获取模型参数
        temperature = self.prompt_template.get("parameters", {}).get("temperature", 0.7)
        max_tokens = self.prompt_template.get("parameters", {}).get("max_tokens", 500)

        # 调用AI
        self.logger.debug(f"调用AI生成标题: {keyword}", direction=direction)
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
        titles = self._parse_ai_response(response.content)

        # 限制标题数量
        if len(titles) > self.max_titles_per_keyword:
            titles = titles[:self.max_titles_per_keyword]

        self.logger.debug(
            f"标题生成完成",
            keyword=keyword,
            direction=direction,
            titles_count=len(titles),
            titles_preview=titles[:2] if titles else [],
            tokens_used=response.usage.get("total_tokens", 0),
            cost=response.cost
        )

        return titles

    def _prepare_messages(self, keyword: str, direction: str = "") -> List[AIMessage]:
        """准备AI消息"""
        # 获取Prompt模板
        system_prompt = self.prompt_template.get("system", "")
        user_prompt_template = self.prompt_template.get("user", "")

        # 格式化用户提示
        min_words, max_words = self.title_length_range
        user_prompt = user_prompt_template.format(
            keyword=keyword,
            max_titles=self.max_titles_per_keyword,
            min_words=min_words,
            max_words=max_words,
            direction=direction,
            title_angle=direction,
        )

        # 创建消息
        messages = [
            create_system_message(system_prompt),
            create_user_message(user_prompt)
        ]

        return messages

    def _parse_ai_response(self, ai_response: str) -> List[str]:
        """解析AI响应"""
        titles = []

        # 尝试解析JSON格式
        json_patterns = [
            r'```json\n(.*?)\n```',  # 代码块中的JSON
            r'\[.*?\]',  # 简单的JSON数组
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, ai_response, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        titles.extend([str(item).strip() for item in data])
                    elif isinstance(data, dict):
                        # 尝试从字典中提取
                        for key, value in data.items():
                            if isinstance(value, (str, list)):
                                titles.append(str(key).strip())
                except json.JSONDecodeError:
                    pass

        # 尝试解析列表格式（每行以 -、* 或数字开头）
        if not titles:
            list_pattern = r'(?:^|\n)[\-*\d\.]+\.?\s*(.+?)(?=\n|$)'
            matches = re.findall(list_pattern, ai_response, re.MULTILINE)
            titles.extend([match.strip() for match in matches])

        # 如果还是没找到，按行分割并清理
        if not titles:
            lines = ai_response.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 移除标记符号
                line = re.sub(r'^[\-*\d\.]+\.?\s*', '', line)
                if line and len(line) > 2 and not line.startswith('#'):
                    titles.append(line)

        # 去重和清理
        unique_titles = []
        seen = set()
        for title in titles:
            title_clean = title.strip().strip('"\'')
            # 移除 markdown 加粗标记 ** 和 *
            title_clean = re.sub(r'^\*{1,2}(.+?)\*{1,2}$', r'\1', title_clean)
            # 移除残留的首尾 * 和空格
            title_clean = title_clean.strip('* \t')
            if title_clean and title_clean.lower() not in seen:
                seen.add(title_clean.lower())
                unique_titles.append(title_clean)

        return unique_titles

    def _generate_default_title(self, keyword: str, direction: str = "") -> str:
        """生成默认标题"""
        # 简单的标题模板
        if direction:
            templates = [
                f"Complete Guide to {keyword}: {direction}",
                f"{keyword}: {direction}",
                f"The Ultimate {keyword} Handbook for {direction}",
                f"Professional Guide to {keyword} for {direction}",
                f"{keyword} Solutions and Applications: {direction}",
            ]
        else:
            templates = [
                f"Complete Guide to {keyword}",
                f"{keyword}: Everything You Need to Know",
                f"The Ultimate {keyword} Handbook",
                f"Professional Guide to {keyword}",
                f"{keyword} Solutions and Applications",
            ]

        # 选择第一个模板
        default_title = templates[0]
        self.logger.debug(f"生成默认标题: {keyword} -> {default_title}", direction=direction)
        return default_title

    def _generate_default_titles(self, keywords: List[Dict[str, str]]) -> List[str]:
        """为关键词列表生成默认标题"""
        return [self._generate_default_title(item["keyword"], item.get("direction", "")) for item in keywords]

    def _log_statistics(self, titles: List[str]) -> None:
        """记录统计信息"""
        # 计算成功率
        if self.stats["total_keywords"] > 0:
            success_rate = self.stats["keywords_processed"] / self.stats["total_keywords"] * 100
        else:
            success_rate = 0

        self.logger.info(
            "AI标题生成统计",
            total_keywords=self.stats["total_keywords"],
            titles_generated=self.stats["titles_generated"],
            keywords_processed=self.stats["keywords_processed"],
            keywords_failed=self.stats["keywords_failed"],
            success_rate=f"{success_rate:.1f}%",
            batches_processed=self.stats["batches_processed"],
            ai_calls=self.stats["ai_calls"],
            total_tokens=self.stats["total_tokens"],
            total_cost=f"${self.stats['total_cost']:.4f}",
            final_titles=len(titles)
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        try:
            keywords = self._validate_and_prepare_input(input_data)
            return len(keywords) > 0
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
        self.logger.info("开始AI标题生成")
        self.stats = {k: 0 for k in self.stats}  # 重置统计
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.info(f"AI标题生成完成，生成 {len(output_data)} 个标题")
        return output_data


# 工具函数
def generate_titles_with_ai(
    keywords: List[Any],
    batch_size: int = 10,
    max_titles_per_keyword: int = 1,
    **kwargs
) -> Tuple[List[str], Dict[str, Any]]:
    """
    使用AI生成标题的便捷函数

    Args:
        keywords: 关键词列表
        batch_size: 批量大小
        max_titles_per_keyword: 每个关键词最大标题数
        **kwargs: 其他AITitleGenerator配置参数

    Returns:
        (生成的标题列表, 统计信息字典)
    """
    title_generator = AITitleGenerator(
        node_id="title_generator_tool",
        config={
            "batch_size": batch_size,
            "max_titles_per_keyword": max_titles_per_keyword,
            **kwargs
        }
    )

    generated_titles = title_generator.execute_impl(keywords)
    stats = title_generator.get_statistics()

    return generated_titles, stats


__all__ = [
    "TitleGenerationResult",
    "AITitleGenerator",
    "generate_titles_with_ai",
]