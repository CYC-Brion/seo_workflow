"""
关键词扩展器
使用Google搜索API获取下拉推荐关键词
"""

import json
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core import DataProcessingNode


@dataclass
class KeywordExpansionResult:
    """关键词扩展结果"""
    original_keywords: List[str]  # 原有关键词
    expanded_keywords: List[str]  # 扩展关键词
    keyword_sources: Dict[str, List[str]]  # 关键词 -> 来源列表
    expansion_stats: Dict[str, Any]  # 扩展统计
    metadata: Dict[str, Any]  # 元数据


class KeywordExpander(DataProcessingNode):
    """关键词扩展器"""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化关键词扩展器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - max_expansions_per_keyword: 每个关键词最大扩展数（默认: 10）
                - request_delay_seconds: 请求延迟（秒，默认: 2）
                - max_retries: 最大重试次数（默认: 3）
                - use_mock_data: 是否使用模拟数据（默认: True，当API不可用时）
                - enable_manual_fallback: 是否启用手动备用方案（默认: True）
                - google_api_key: Google API密钥（可选）
                - google_search_engine_id: Google搜索引擎ID（可选）
        """
        config = config or {}
        super().__init__(node_id, "keyword_expander", config)

        # 配置参数
        self.max_expansions_per_keyword = config.get("max_expansions_per_keyword", 10)
        self.request_delay_seconds = config.get("request_delay_seconds", 2)
        self.max_retries = config.get("max_retries", 3)
        self.use_mock_data = config.get("use_mock_data", True)
        self.enable_manual_fallback = config.get("enable_manual_fallback", True)
        self.google_api_key = config.get("google_api_key")
        self.google_search_engine_id = config.get("google_search_engine_id")

        # 检查是否配置了Google API
        self.has_google_api = bool(self.google_api_key and self.google_search_engine_id)

        # 创建带指数退避重试的 requests Session
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.request_delay_seconds,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"User-Agent": self.USER_AGENT})

        # 端点缓存 & robots.txt 缓存
        self._last_successful_endpoint_idx = 0
        self._robots_cache: Dict[str, bool] = {}

        # 模拟数据（用于测试）
        self.mock_expansions = self._load_mock_expansions()

        # 统计数据
        self.stats = {
            "total_keywords": 0,
            "keywords_expanded": 0,
            "keywords_failed": 0,
            "total_expansions": 0,
            "api_requests": 0,
            "manual_expansions": 0,
            "mock_expansions": 0,
            "retry_attempts": 0,
        }

        self.logger.info(
            f"关键词扩展器初始化: {node_id}",
            config={
                "max_expansions_per_keyword": self.max_expansions_per_keyword,
                "has_google_api": self.has_google_api,
                "use_mock_data": self.use_mock_data,
                "enable_manual_fallback": self.enable_manual_fallback,
                "max_retries": self.max_retries,
            }
        )

    def _load_mock_expansions(self) -> Dict[str, List[str]]:
        """加载模拟扩展数据"""
        # 五金灯饰配件行业的模拟关键词扩展
        mock_data = {
            # 五金配件相关
            "metal hardware": [
                "metal hardware supplies",
                "metal hardware manufacturers",
                "metal hardware parts",
                "industrial metal hardware",
                "custom metal hardware",
                "metal hardware tools",
                "metal hardware accessories",
                "metal hardware wholesale",
                "metal hardware online",
                "metal hardware catalog"
            ],
            "lighting accessories": [
                "lighting accessories manufacturers",
                "lighting accessories wholesale",
                "lighting accessories online",
                "led lighting accessories",
                "home lighting accessories",
                "outdoor lighting accessories",
                "lighting accessories parts",
                "lighting accessories catalog",
                "custom lighting accessories",
                "lighting accessories suppliers"
            ],
            "hardware processing": [
                "hardware processing manufacturers",
                "hardware processing services",
                "cnc hardware processing",
                "custom hardware processing",
                "precision hardware processing",
                "metal hardware processing",
                "hardware processing technology",
                "hardware processing equipment",
                "hardware processing factory",
                "hardware processing solutions"
            ],
            # 通用关键词
            "industrial parts": [
                "industrial parts manufacturers",
                "industrial parts suppliers",
                "industrial parts catalog",
                "industrial parts wholesale",
                "precision industrial parts",
                "industrial machinery parts",
                "industrial equipment parts",
                "industrial replacement parts",
                "industrial spare parts",
                "industrial parts online"
            ]
        }

        return mock_data

    def execute_impl(self, input_data: Any) -> Any:
        """执行关键词扩展

        Args:
            input_data: 输入数据，应为关键词列表

        Returns:
            扩展后的关键词池（包含原关键词和扩展关键词）
        """
        # 验证输入数据
        keywords = self._validate_and_prepare_input(input_data)

        # 初始化结果
        expansion_result = KeywordExpansionResult(
            original_keywords=keywords.copy(),
            expanded_keywords=[],
            keyword_sources={},
            expansion_stats={},
            metadata={"expansion_method": None}
        )

        # 扩展每个关键词
        for i, keyword in enumerate(keywords):
            self.logger.info(
                f"扩展关键词 {i + 1}/{len(keywords)}: {keyword}",
                total_keywords=len(keywords)
            )

            try:
                # 获取扩展关键词
                expansions = self._expand_keyword(keyword)

                # 记录结果
                if expansions:
                    expansion_result.expanded_keywords.extend(expansions)
                    expansion_result.keyword_sources[keyword] = expansions
                    self.stats["keywords_expanded"] += 1
                    self.stats["total_expansions"] += len(expansions)

                    self.logger.debug(
                        f"关键词扩展成功",
                        keyword=keyword,
                        expansions_count=len(expansions),
                        expansions_preview=expansions[:3]
                    )
                else:
                    self.stats["keywords_failed"] += 1
                    self.logger.warning(
                        f"关键词扩展失败或无结果",
                        keyword=keyword,
                        expansion_method=expansion_result.metadata.get("expansion_method")
                    )

                # 请求延迟，避免被封禁
                if i < len(keywords) - 1:
                    time.sleep(self.request_delay_seconds)

            except Exception as e:
                self.stats["keywords_failed"] += 1
                self.logger.error(
                    f"关键词扩展异常: {keyword}",
                    error=str(e),
                    expansion_method=expansion_result.metadata.get("expansion_method")
                )

                # 如果启用备用方案，尝试手动扩展
                if self.enable_manual_fallback:
                    self.logger.info(f"尝试手动备用方案: {keyword}")
                    try:
                        manual_expansions = self._get_manual_expansions(keyword)
                        if manual_expansions:
                            expansion_result.expanded_keywords.extend(manual_expansions)
                            expansion_result.keyword_sources[keyword] = manual_expansions
                            self.stats["manual_expansions"] += len(manual_expansions)
                            self.logger.info(f"手动扩展成功", keyword=keyword, expansions=len(manual_expansions))
                    except Exception as manual_error:
                        self.logger.error(f"手动扩展也失败: {manual_error}")

        # 合并结果（原关键词 + 扩展关键词）
        all_keywords = self._merge_keywords(expansion_result)

        # 记录统计信息
        self._log_statistics(expansion_result, all_keywords)

        return all_keywords

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

    def _expand_keyword(self, keyword: str) -> List[str]:
        """扩展单个关键词

        单一降级链：Custom Search API → Google Suggest → Mock → Patterns。
        每个 fallback 只出现一次，避免重复调用。
        """
        expansions: List[str] = []

        # 1. Google Custom Search API（需配置 API 密钥）
        if self.has_google_api:
            self.logger.debug(f"尝试 Google Custom Search API: {keyword}")
            try:
                expansions = self._expand_with_google_custom_search(keyword)
                if expansions:
                    self.stats["api_requests"] += 1
                    self.logger.debug(f"Custom Search API 成功", keyword=keyword, count=len(expansions))
                    return expansions[:self.max_expansions_per_keyword]
            except Exception as e:
                self.logger.warning(f"Custom Search API 失败: {e}")

        # 2. Google Suggest 公共端点
        self.logger.debug(f"尝试 Google Suggest: {keyword}")
        try:
            expansions = self._get_google_suggestions(keyword)
            if expansions:
                self.logger.debug(f"Google Suggest 成功", keyword=keyword, count=len(expansions))
                return expansions[:self.max_expansions_per_keyword]
        except Exception as e:
            self.logger.warning(f"Google Suggest 失败: {e}")

        # 3. 模拟数据
        if self.use_mock_data:
            self.logger.debug(f"尝试模拟数据: {keyword}")
            expansions = self._expand_with_mock_data(keyword)
            if expansions:
                self.stats["mock_expansions"] += len(expansions)
                self.logger.debug(f"模拟数据成功", keyword=keyword, count=len(expansions))
                return expansions[:self.max_expansions_per_keyword]

        # 4. 最终兜底：模式生成
        self.logger.debug(f"使用模式兜底: {keyword}")
        expansions = self._expand_with_patterns(keyword)
        self.logger.debug(f"模式生成完成", keyword=keyword, count=len(expansions))
        return expansions[:self.max_expansions_per_keyword]

    def _check_robots_txt(self, url: str) -> bool:
        """检查 robots.txt 是否允许抓取，结果按域名缓存"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url in self._robots_cache:
            return self._robots_cache[base_url]

        try:
            robots_url = urljoin(base_url, "/robots.txt")
            response = self.session.get(robots_url, timeout=5)
            if response.status_code == 200:
                rp = RobotFileParser()
                rp.parse(response.text.splitlines())
                allowed = rp.can_fetch(self.USER_AGENT, url)
                self._robots_cache[base_url] = allowed
                return allowed
        except Exception:
            pass

        self._robots_cache[base_url] = True
        return True

    def _expand_with_google_custom_search(self, keyword: str) -> List[str]:
        """使用Google Custom Search API扩展关键词"""
        url = "https://www.googleapis.com/customsearch/v1"

        if not self._check_robots_txt(url):
            self.logger.warning(f"robots.txt 禁止访问: {url}")
            return []

        try:
            params = {
                "q": keyword,
                "key": self.google_api_key,
                "cx": self.google_search_engine_id,
                "num": 10,
                "gl": "us",
                "hl": "en",
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            expansions = []
            if "items" in data:
                for item in data["items"]:
                    title = item.get("title", "")
                    if keyword.lower() in title.lower():
                        expansions.append(title)

            return expansions[:self.max_expansions_per_keyword]

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Google Custom Search API请求异常: {e}")
            return []
        except Exception as e:
            self.logger.warning(f"Google Custom Search API处理异常: {e}")
            return []

    def _get_google_suggestions(self, keyword: str) -> List[str]:
        """获取Google搜索建议（下拉框推荐）

        多个端点依次尝试，缓存上次成功的端点以优化后续请求。
        """
        encoded_keyword = quote(keyword)

        endpoints = [
            f"https://suggestqueries.google.com/complete/search?client=firefox&q={encoded_keyword}",
            f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded_keyword}",
            f"https://www.google.com/complete/search?client=hp&q={encoded_keyword}",
        ]

        # 将上次成功的端点移到最前面
        if 0 < self._last_successful_endpoint_idx < len(endpoints):
            endpoints.insert(0, endpoints.pop(self._last_successful_endpoint_idx))
            self._last_successful_endpoint_idx = 0

        expansions: List[str] = []

        for i, endpoint in enumerate(endpoints):
            if not self._check_robots_txt(endpoint):
                self.logger.debug(f"robots.txt 禁止访问: {endpoint}")
                continue

            try:
                response = self.session.get(endpoint, timeout=5)
                response.raise_for_status()

                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    suggestions = data[1]
                    if isinstance(suggestions, list):
                        expansions.extend(suggestions)

                if expansions:
                    self._last_successful_endpoint_idx = i
                    break

            except Exception as e:
                self.logger.debug(f"端点失败 {endpoint}: {e}")
                continue

        # 去重
        unique_expansions: List[str] = []
        seen: set = set()
        for exp in expansions:
            exp_lower = exp.lower()
            if exp_lower not in seen and exp_lower != keyword.lower():
                seen.add(exp_lower)
                unique_expansions.append(exp)

        return unique_expansions[:self.max_expansions_per_keyword]

    def _expand_with_mock_data(self, keyword: str) -> List[str]:
        """使用模拟数据扩展关键词"""
        keyword_lower = keyword.lower()

        # 检查是否有预定义的模拟扩展
        for mock_keyword, expansions in self.mock_expansions.items():
            if mock_keyword in keyword_lower or keyword_lower in mock_keyword:
                # 返回相关的扩展
                return expansions.copy()

        # 如果没有匹配的模拟数据，生成通用扩展
        return self._expand_with_patterns(keyword)

    def _expand_with_patterns(self, keyword: str) -> List[str]:
        """基于模式生成扩展关键词"""
        expansions = []
        keyword_lower = keyword.lower()

        # 常见扩展模式
        patterns = [
            f"{keyword} manufacturers",
            f"{keyword} suppliers",
            f"{keyword} wholesale",
            f"{keyword} online",
            f"{keyword} catalog",
            f"{keyword} parts",
            f"{keyword} accessories",
            f"{keyword} tools",
            f"{keyword} equipment",
            f"{keyword} solutions",
            f"custom {keyword}",
            f"precision {keyword}",
            f"industrial {keyword}",
            f"professional {keyword}",
            f"quality {keyword}",
        ]

        # 添加一些变体
        expansions.extend(patterns)

        # 如果关键词包含特定行业术语，添加行业相关扩展
        industry_terms = {
            "metal": ["metal processing", "metal fabrication", "metal parts"],
            "hardware": ["hardware tools", "hardware supplies", "hardware components"],
            "lighting": ["led lighting", "lighting fixtures", "lighting systems"],
            "accessories": ["accessories parts", "accessories components", "accessories kit"],
        }

        for term, term_expansions in industry_terms.items():
            if term in keyword_lower:
                expansions.extend(term_expansions)

        # 去重
        unique_expansions = []
        seen = set()
        for exp in expansions:
            if exp.lower() not in seen:
                seen.add(exp.lower())
                unique_expansions.append(exp)

        return unique_expansions[:self.max_expansions_per_keyword]

    def _get_manual_expansions(self, keyword: str) -> List[str]:
        """获取手动扩展关键词（备用方案）

        在实际应用中，这里可以提供用户界面让用户手动输入扩展关键词
        当前实现返回基于模式的扩展
        """
        return self._expand_with_patterns(keyword)

    def _merge_keywords(self, expansion_result: KeywordExpansionResult) -> List[str]:
        """合并原关键词和扩展关键词"""
        all_keywords = expansion_result.original_keywords.copy()

        # 添加扩展关键词
        for expansions in expansion_result.keyword_sources.values():
            all_keywords.extend(expansions)

        # 去重
        unique_keywords = []
        seen = set()
        for kw in all_keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw)

        # 标记来源
        expansion_result.expansion_stats = {
            "original_count": len(expansion_result.original_keywords),
            "expanded_count": len(expansion_result.expanded_keywords),
            "unique_count": len(unique_keywords),
            "expansion_rate": len(expansion_result.expanded_keywords) / len(expansion_result.original_keywords)
                if expansion_result.original_keywords else 0,
        }

        return unique_keywords

    def _log_statistics(
        self,
        expansion_result: KeywordExpansionResult,
        all_keywords: List[str]
    ) -> None:
        """记录统计信息"""
        expansion_stats = expansion_result.expansion_stats

        self.logger.info(
            "关键词扩展统计",
            total_keywords=self.stats["total_keywords"],
            keywords_expanded=self.stats["keywords_expanded"],
            keywords_failed=self.stats["keywords_failed"],
            total_expansions=self.stats["total_expansions"],
            api_requests=self.stats["api_requests"],
            manual_expansions=self.stats["manual_expansions"],
            mock_expansions=self.stats["mock_expansions"],
            original_count=expansion_stats.get("original_count", 0),
            expanded_count=expansion_stats.get("expanded_count", 0),
            unique_count=expansion_stats.get("unique_count", 0),
            expansion_rate=f"{expansion_stats.get('expansion_rate', 0) * 100:.1f}%",
            final_keywords=len(all_keywords)
        )

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

        if len(output_data) == 0:
            self.logger.warning("输出数据为空列表")
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
        self.logger.info("开始关键词扩展")
        self.stats = {k: 0 for k in self.stats}  # 重置统计
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.info(f"关键词扩展完成，生成 {len(output_data)} 个关键词")
        return output_data

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()


# 工具函数
def expand_keywords(
    keywords: List[str],
    max_expansions_per_keyword: int = 10,
    request_delay_seconds: float = 2.0,
    **kwargs
) -> Tuple[List[str], Dict[str, Any]]:
    """
    扩展关键词的便捷函数

    Args:
        keywords: 关键词列表
        max_expansions_per_keyword: 每个关键词最大扩展数
        request_delay_seconds: 请求延迟秒数
        **kwargs: 其他KeywordExpander配置参数

    Returns:
        (扩展后的关键词列表, 统计信息字典)
    """
    expander = KeywordExpander(
        node_id="keyword_expander_tool",
        config={
            "max_expansions_per_keyword": max_expansions_per_keyword,
            "request_delay_seconds": request_delay_seconds,
            **kwargs
        }
    )

    expanded_keywords = expander.execute_impl(keywords)
    stats = expander.get_statistics()

    return expanded_keywords, stats


__all__ = [
    "KeywordExpansionResult",
    "KeywordExpander",
    "expand_keywords",
]