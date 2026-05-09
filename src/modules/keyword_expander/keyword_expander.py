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

    # Google / Bing 公共 suggest 端点
    GOOGLE_SUGGEST_ENDPOINTS = [
        "https://suggestqueries.google.com/complete/search?client=firefox&q={query}",
        "https://suggestqueries.google.com/complete/search?client=chrome&q={query}",
        "https://www.google.com/complete/search?client=hp&q={query}",
    ]

    BING_SUGGEST_ENDPOINT = "https://api.bing.com/osjson.aspx?query={query}"

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
                - google_api_key: Google API密钥（可选）
                - google_search_engine_id: Google搜索引擎ID（可选）
                - http_proxy: HTTP 代理地址，如 http://127.0.0.1:7890（可选）
        """
        config = config or {}
        super().__init__(node_id, "keyword_expander", config)

        # 配置参数
        self.max_expansions_per_keyword = config.get("max_expansions_per_keyword", 10)
        self.request_delay_seconds = config.get("request_delay_seconds", 2)
        self.max_retries = config.get("max_retries", 3)
        self.google_api_key = config.get("google_api_key")
        self.google_search_engine_id = config.get("google_search_engine_id")
        self.http_proxy = config.get("http_proxy")

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

        # 配置代理
        if self.http_proxy:
            self.session.proxies = {
                "http": self.http_proxy,
                "https": self.http_proxy,
            }
            self.logger.info(f"代理已配置: {self.http_proxy}")

        # 端点缓存 & robots.txt 缓存
        self._last_successful_google_endpoint_idx = 0
        self._robots_cache: Dict[str, bool] = {}

        # 统计数据
        self.stats = {
            "total_keywords": 0,
            "keywords_expanded": 0,
            "keywords_failed": 0,
            "total_expansions": 0,
            "api_requests": 0,
            "google_suggest_requests": 0,
            "bing_suggest_requests": 0,
            "retry_attempts": 0,
        }

        self.logger.info(
            f"关键词扩展器初始化: {node_id}",
            config={
                "max_expansions_per_keyword": self.max_expansions_per_keyword,
                "has_google_api": self.has_google_api,
                "max_retries": self.max_retries,
                "http_proxy": self.http_proxy,
            }
        )

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
                )

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

        同时查询 Google Suggest + Bing Suggest（以及可选的 Google Custom Search API），
        两个渠道都必须成功，任意失败即报错。合并去重后返回。
        """
        all_expansions: List[str] = []
        errors: List[str] = []

        # 1. Google Custom Search API（需配置 API 密钥）
        if self.has_google_api:
            self.logger.debug(f"尝试 Google Custom Search API: {keyword}")
            try:
                expansions = self._expand_with_google_custom_search(keyword)
                if expansions:
                    self.stats["api_requests"] += 1
                    all_expansions.extend(expansions)
                    self.logger.debug(f"Custom Search API 成功", keyword=keyword, count=len(expansions))
            except Exception as e:
                err_msg = f"Google Custom Search API: {e}"
                self.logger.warning(err_msg)
                errors.append(err_msg)

        # 2. Google Suggest（必须成功）
        self.logger.debug(f"尝试 Google Suggest: {keyword}")
        try:
            expansions = self._get_google_suggestions(keyword)
            if not expansions:
                raise RuntimeError("Google Suggest 返回空结果")
            self.stats["google_suggest_requests"] += 1
            all_expansions.extend(expansions)
            self.logger.debug(f"Google Suggest 成功", keyword=keyword, count=len(expansions))
        except Exception as e:
            err_msg = f"Google Suggest 失败: {e}"
            self.logger.error(err_msg)
            raise RuntimeError(
                f"关键词 '{keyword}': Google Suggest 不可用 — {e}"
                + ("\n  提示: 中国大陆需要配置 http_proxy 代理访问 Google"
                   if not self.http_proxy else "")
            ) from e

        # 3. Bing Suggest（必须成功）
        self.logger.debug(f"尝试 Bing Suggest: {keyword}")
        try:
            expansions = self._get_bing_suggestions(keyword)
            if not expansions:
                raise RuntimeError("Bing Suggest 返回空结果")
            self.stats["bing_suggest_requests"] += 1
            all_expansions.extend(expansions)
            self.logger.debug(f"Bing Suggest 成功", keyword=keyword, count=len(expansions))
        except Exception as e:
            err_msg = f"Bing Suggest 失败: {e}"
            self.logger.error(err_msg)
            raise RuntimeError(
                f"关键词 '{keyword}': Bing Suggest 不可用 — {e}"
            ) from e

        # 合并去重（Google + Bing 可能有重复建议）
        unique: List[str] = []
        seen: set = set()
        kw_lower = keyword.lower()
        for exp in all_expansions:
            exp_lower = exp.lower()
            if exp_lower not in seen and exp_lower != kw_lower:
                seen.add(exp_lower)
                unique.append(exp)

        return unique[:self.max_expansions_per_keyword]

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
        if 0 < self._last_successful_google_endpoint_idx < len(endpoints):
            endpoints.insert(0, endpoints.pop(self._last_successful_google_endpoint_idx))
            self._last_successful_google_endpoint_idx = 0

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
                    self._last_successful_google_endpoint_idx = i
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

    def _get_bing_suggestions(self, keyword: str) -> List[str]:
        """获取Bing搜索建议（下拉框推荐）

        使用 Bing osjson.aspx 公共端点（无需 API 密钥），
        响应格式为 ["keyword", ["suggestion1", "suggestion2", ...]]。
        """
        encoded_keyword = quote(keyword)
        url = self.BING_SUGGEST_ENDPOINT.format(query=encoded_keyword)

        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                suggestions = data[1]
                if isinstance(suggestions, list) and suggestions:
                    unique: List[str] = []
                    seen: set = set()
                    for s in suggestions:
                        s_lower = s.lower()
                        if s_lower not in seen and s_lower != keyword.lower():
                            seen.add(s_lower)
                            unique.append(s)
                    return unique[:self.max_expansions_per_keyword]

        except Exception as e:
            self.logger.warning(f"Bing Suggest 请求失败: {e}")
            raise

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
            google_suggest_requests=self.stats["google_suggest_requests"],
            bing_suggest_requests=self.stats["bing_suggest_requests"],
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