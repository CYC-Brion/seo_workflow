"""
AI关键词筛选器
使用AI模型筛选与五金灯饰配件行业相关的关键词
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

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
class KeywordFilterResult:
    """关键词筛选结果"""
    relevant_keywords: List[str]  # 相关关键词
    irrelevant_keywords: List[str]  # 不相关关键词
    confidence_scores: Dict[str, float]  # 关键词 -> 置信度分数 (0-1)
    filter_reasons: Dict[str, str]  # 关键词 -> 过滤原因
    metadata: Dict[str, Any]  # 元数据
    # AI 调用失败时按兜底策略保留的关键词：这些词没有真实置信度，
    # 必须绕过 confidence_threshold，否则会被当成低置信度刷掉。
    fallback_keywords: set = field(default_factory=set)


class AIKeywordFilter(AINode):
    """AI关键词筛选器"""

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化AI关键词筛选器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - batch_size: 批量处理大小（默认: 50）
                - confidence_threshold: 置信度阈值（默认: 0.7）
                - max_keywords_per_request: 每个请求最大关键词数（默认: 100）
                - enable_fallback: 是否启用备用模型（默认: True）
                - language: 关键词语言（默认: "en"）
                - industry: 目标行业（默认: "Metal Hardware & Lighting Accessories Processing"）
        """
        config = config or {}
        super().__init__(node_id, "keyword_filter", config)

        # 配置参数
        self.batch_size = config.get("batch_size", 50)
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.max_keywords_per_request = config.get("max_keywords_per_request", 100)
        self.enable_fallback = config.get("enable_fallback", True)
        self.language = config.get("language", "en")
        self.industry = config.get("industry", "Metal Hardware & Lighting Accessories Processing")

        # 从配置获取Prompt模板
        self.prompt_template = self._load_prompt_template()

        # 统计数据
        self.stats = {
            "total_keywords": 0,
            "relevant_keywords": 0,
            "irrelevant_keywords": 0,
            "low_confidence_keywords": 0,
            "batches_processed": 0,
            "ai_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

        self.logger.info(
            f"AI关键词筛选器初始化: {node_id}",
            config={
                "batch_size": self.batch_size,
                "confidence_threshold": self.confidence_threshold,
                "enable_fallback": self.enable_fallback,
                "language": self.language,
            }
        )

    def _load_prompt_template(self) -> Dict[str, Any]:
        """加载Prompt模板"""
        try:
            prompt_name = "keyword_filter"
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
                "system": "You are an SEO specialist and professional content writer. Your main task is to extract search keywords for search engines that match Metal Hardware & Lighting Accessories Processing.",
                "user": "Please filter the following keywords and remove any that are not relevant to Metal Hardware & Lighting Accessories Processing. Return only the relevant keywords in a list format.\n\nKeywords: {keywords}",
                "parameters": {
                    "temperature": 0.3,
                    "max_tokens": 1000,
                }
            }

    def execute_impl(self, input_data: Any) -> Any:
        """执行关键词筛选

        Args:
            input_data: 输入数据，应为关键词列表

        Returns:
            筛选后的关键词列表
        """
        # 验证输入数据
        keywords = self._validate_and_prepare_input(input_data)

        # 分批处理
        all_results = KeywordFilterResult([], [], {}, {}, {})
        batches = self._create_batches(keywords)

        for i, batch in enumerate(batches):
            self.logger.info(
                f"处理批次 {i + 1}/{len(batches)}",
                batch_size=len(batch),
                total_keywords=len(keywords)
            )

            try:
                batch_result = self._process_batch(batch)
                all_results = self._merge_results(all_results, batch_result)

                self.stats["batches_processed"] += 1

            except Exception as e:
                self.logger.error(
                    f"[AI调用失败] 关键词筛选节点无法连接 AI 服务。"
                    f"请检查 .env 中的 AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT 或 OPENAI_API_KEY 是否正确。"
                    f"原始错误: {e}"
                )
                # 如果启用备用模型，尝试使用备用模型
                if self.enable_fallback:
                    self.logger.info("尝试使用备用模型")
                    try:
                        batch_result = self._process_batch_with_fallback(batch)
                        all_results = self._merge_results(all_results, batch_result)
                        self.stats["batches_processed"] += 1
                    except Exception as fallback_error:
                        self.logger.error(
                            f"[备用模型失败] 未配置 Anthropic 等备用模型，使用默认策略（保留所有关键词）。"
                            f"如需备用模型，请在 config/ai_models_config.py 的 FALLBACK_MODELS 中配置。"
                        )
                        # 保留所有关键词作为相关关键词（跳过筛选）
                        all_results.relevant_keywords.extend(batch)
                        for kw in batch:
                            all_results.confidence_scores[kw] = 0.5
                            all_results.filter_reasons[kw] = "AI 调用失败，默认保留"
                            all_results.fallback_keywords.add(kw)
                else:
                    # 保留所有关键词作为相关关键词
                    all_results.relevant_keywords.extend(batch)
                    for kw in batch:
                        all_results.confidence_scores[kw] = 0.5
                        all_results.filter_reasons[kw] = "AI 调用失败，默认保留"
                        all_results.fallback_keywords.add(kw)

        # 应用置信度阈值
        filtered_keywords = self._apply_confidence_threshold(all_results)

        # 记录统计信息
        self._log_statistics(all_results, filtered_keywords)

        return filtered_keywords

    def _validate_and_prepare_input(self, input_data: Any) -> List[str]:
        """验证和准备输入数据"""
        if isinstance(input_data, list):
            keywords = [str(kw).strip() for kw in input_data if str(kw).strip()]
        elif isinstance(input_data, str):
            # 尝试解析字符串为列表
            if input_data.startswith("[") and input_data.endswith("]"):
                try:
                    keywords = json.loads(input_data)
                    keywords = [str(kw).strip() for kw in keywords if str(kw).strip()]
                except json.JSONDecodeError:
                    keywords = [input_data.strip()]
            else:
                # 按逗号或换行分割
                keywords = re.split(r'[,\n]', input_data)
                keywords = [kw.strip() for kw in keywords if kw.strip()]
        else:
            raise ValueError(f"不支持的输入数据类型: {type(input_data)}")

        if not keywords:
            raise ValueError("输入关键词列表为空")

        self.stats["total_keywords"] = len(keywords)
        self.logger.info(f"输入验证通过，共 {len(keywords)} 个关键词")
        return keywords

    def _create_batches(self, keywords: List[str]) -> List[List[str]]:
        """创建处理批次"""
        batch_size = min(self.batch_size, self.max_keywords_per_request)
        batches = []

        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]
            batches.append(batch)

        self.logger.debug(f"创建 {len(batches)} 个批次，每批最多 {batch_size} 个关键词")
        return batches

    def _process_batch(self, batch: List[str]) -> KeywordFilterResult:
        """处理单个批次"""
        # 准备消息
        messages = self._prepare_messages(batch)

        # 获取AI客户端
        ai_client = get_ai_client("keyword_filter", use_fallback=False)

        # 获取模型参数
        temperature = self.prompt_template.get("parameters", {}).get("temperature", 0.3)
        max_tokens = self.prompt_template.get("parameters", {}).get("max_tokens", 1000)

        # 调用AI
        self.logger.debug(f"调用AI筛选 {len(batch)} 个关键词")
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
        result = self._parse_ai_response(batch, response.content)

        self.logger.debug(
            f"批次处理完成",
            relevant_count=len(result.relevant_keywords),
            irrelevant_count=len(result.irrelevant_keywords),
            tokens_used=response.usage.get("total_tokens", 0),
            cost=response.cost
        )

        return result

    def _process_batch_with_fallback(self, batch: List[str]) -> KeywordFilterResult:
        """使用备用模型处理批次"""
        # 准备消息（与主模型相同）
        messages = self._prepare_messages(batch)

        # 获取备用AI客户端
        ai_client = get_ai_client("keyword_filter", use_fallback=True)

        # 获取备用模型参数（从配置）
        fallback_config = config_manager.get_fallback_model_config("keyword_filter")
        temperature = getattr(fallback_config, "temperature", 0.3)
        max_tokens = getattr(fallback_config, "max_tokens", 1000)

        # 调用AI
        self.logger.debug(f"调用备用AI筛选 {len(batch)} 个关键词")
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
        result = self._parse_ai_response(batch, response.content)

        self.logger.debug(
            f"备用模型批次处理完成",
            relevant_count=len(result.relevant_keywords),
            irrelevant_count=len(result.irrelevant_keywords),
            model=ai_client.model,
            tokens_used=response.usage.get("total_tokens", 0),
            cost=response.cost
        )

        return result

    def _prepare_messages(self, keywords: List[str]) -> List[AIMessage]:
        """准备AI消息"""
        # 获取Prompt模板
        system_prompt = self.prompt_template.get("system", "")
        user_prompt_template = self.prompt_template.get("user", "")

        # 格式化用户提示
        keywords_text = "\n".join(f"- {kw}" for kw in keywords)
        user_prompt = user_prompt_template.format(keywords=keywords_text)

        # 创建消息
        messages = [
            create_system_message(system_prompt),
            create_user_message(user_prompt)
        ]

        return messages

    def _parse_ai_response(
        self,
        original_keywords: List[str],
        ai_response: str
    ) -> KeywordFilterResult:
        """解析AI响应"""
        relevant_keywords = []
        irrelevant_keywords = []
        confidence_scores = {}
        filter_reasons = {}

        # 尝试多种格式解析
        parsed_keywords = self._extract_keywords_from_response(ai_response)

        # 匹配原始关键词
        for original_kw in original_keywords:
            original_lower = original_kw.lower()

            # 检查是否在解析出的相关关键词中
            is_relevant = False
            for parsed_kw in parsed_keywords:
                if original_lower in parsed_kw.lower() or parsed_kw.lower() in original_lower:
                    is_relevant = True
                    break

            if is_relevant:
                relevant_keywords.append(original_kw)
                confidence_scores[original_kw] = 0.9  # 高置信度
                filter_reasons[original_kw] = "与行业相关"
            else:
                irrelevant_keywords.append(original_kw)
                confidence_scores[original_kw] = 0.2  # 低置信度
                filter_reasons[original_kw] = "与行业不相关"

        return KeywordFilterResult(
            relevant_keywords=relevant_keywords,
            irrelevant_keywords=irrelevant_keywords,
            confidence_scores=confidence_scores,
            filter_reasons=filter_reasons,
            metadata={
                "ai_response_preview": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
                "parsed_keywords_count": len(parsed_keywords),
            }
        )

    def _extract_keywords_from_response(self, response: str) -> List[str]:
        """从AI响应中提取关键词"""
        keywords = []

        # 尝试解析JSON格式
        json_patterns = [
            r'```json\n(.*?)\n```',  # 代码块中的JSON
            r'\[.*?\]',  # 简单的JSON数组
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        keywords.extend([str(item).strip() for item in data])
                    elif isinstance(data, dict):
                        # 尝试从字典中提取
                        for key, value in data.items():
                            if isinstance(value, (str, list)):
                                keywords.append(str(key).strip())
                except json.JSONDecodeError:
                    pass

        # 尝试解析列表格式（每行以 -、* 或数字开头）
        if not keywords:
            list_pattern = r'(?:^|\n)[\-*\d\.]+\.?\s*(.+?)(?=\n|$)'
            matches = re.findall(list_pattern, response, re.MULTILINE)
            keywords.extend([match.strip() for match in matches])

        # 如果还是没找到，按行分割并清理
        if not keywords:
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 移除标记符号
                line = re.sub(r'^[\-*\d\.]+\.?\s*', '', line)
                if line and len(line) > 2 and not line.startswith('#'):
                    keywords.append(line)

        # 去重和清理
        unique_keywords = []
        seen = set()
        for kw in keywords:
            kw_clean = kw.strip().strip('"\'')
            if kw_clean and kw_clean.lower() not in seen:
                seen.add(kw_clean.lower())
                unique_keywords.append(kw_clean)

        return unique_keywords

    def _merge_results(
        self,
        result1: KeywordFilterResult,
        result2: KeywordFilterResult
    ) -> KeywordFilterResult:
        """合并两个筛选结果"""
        return KeywordFilterResult(
            relevant_keywords=result1.relevant_keywords + result2.relevant_keywords,
            irrelevant_keywords=result1.irrelevant_keywords + result2.irrelevant_keywords,
            confidence_scores={**result1.confidence_scores, **result2.confidence_scores},
            filter_reasons={**result1.filter_reasons, **result2.filter_reasons},
            fallback_keywords=result1.fallback_keywords | result2.fallback_keywords,
            metadata={
                **result1.metadata,
                **result2.metadata,
                "merged_batches": result1.metadata.get("merged_batches", 0) + 1
            }
        )

    def _apply_confidence_threshold(
        self,
        result: KeywordFilterResult
    ) -> List[str]:
        """应用置信度阈值"""
        filtered_keywords = []

        for kw in result.relevant_keywords:
            confidence = result.confidence_scores.get(kw, 0.5)
            # 兜底保留的词没有真实置信度，不能被阈值刷掉
            if kw in result.fallback_keywords or confidence >= self.confidence_threshold:
                filtered_keywords.append(kw)
            else:
                result.irrelevant_keywords.append(kw)
                result.filter_reasons[kw] = f"置信度过低 ({confidence:.2f} < {self.confidence_threshold})"
                self.stats["low_confidence_keywords"] += 1

        # 更新相关关键词列表
        result.relevant_keywords = filtered_keywords

        return filtered_keywords

    def _log_statistics(
        self,
        result: KeywordFilterResult,
        filtered_keywords: List[str]
    ) -> None:
        """记录统计信息"""
        self.stats["relevant_keywords"] = len(result.relevant_keywords)
        self.stats["irrelevant_keywords"] = len(result.irrelevant_keywords)

        # 计算筛选率
        if self.stats["total_keywords"] > 0:
            relevance_rate = self.stats["relevant_keywords"] / self.stats["total_keywords"] * 100
            filter_rate = self.stats["irrelevant_keywords"] / self.stats["total_keywords"] * 100
        else:
            relevance_rate = 0
            filter_rate = 0

        self.logger.info(
            "AI关键词筛选统计",
            total_keywords=self.stats["total_keywords"],
            relevant_keywords=self.stats["relevant_keywords"],
            irrelevant_keywords=self.stats["irrelevant_keywords"],
            low_confidence_keywords=self.stats["low_confidence_keywords"],
            relevance_rate=f"{relevance_rate:.1f}%",
            filter_rate=f"{filter_rate:.1f}%",
            batches_processed=self.stats["batches_processed"],
            ai_calls=self.stats["ai_calls"],
            total_tokens=self.stats["total_tokens"],
            total_cost=f"${self.stats['total_cost']:.4f}",
            final_keywords=len(filtered_keywords)
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
        self.logger.info("开始AI关键词筛选")
        self.stats = {k: 0 for k in self.stats}  # 重置统计
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.info(f"AI关键词筛选完成，保留 {len(output_data)} 个关键词")
        return output_data


# 工具函数
def filter_keywords_with_ai(
    keywords: List[str],
    batch_size: int = 50,
    confidence_threshold: float = 0.7,
    **kwargs
) -> Tuple[List[str], Dict[str, Any]]:
    """
    使用AI筛选关键词的便捷函数

    Args:
        keywords: 关键词列表
        batch_size: 批量大小
        confidence_threshold: 置信度阈值
        **kwargs: 其他AIKeywordFilter配置参数

    Returns:
        (筛选后的关键词列表, 统计信息字典)
    """
    filter_node = AIKeywordFilter(
        node_id="keyword_filter_tool",
        config={
            "batch_size": batch_size,
            "confidence_threshold": confidence_threshold,
            **kwargs
        }
    )

    filtered_keywords = filter_node.execute_impl(keywords)
    stats = filter_node.get_statistics()

    return filtered_keywords, stats


__all__ = [
    "KeywordFilterResult",
    "AIKeywordFilter",
    "filter_keywords_with_ai",
]