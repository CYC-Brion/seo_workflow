"""
关键词扩展器
使用Google搜索API获取下拉推荐关键词
"""

import json
import os
import time
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError, ProxyError
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
    ideas: List["KeywordIdea"] = field(default_factory=list)


@dataclass
class KeywordIdea:
    """Normalized keyword research data from any expansion source."""

    keyword: str
    sources: List[str] = field(default_factory=list)
    seed_keywords: List[str] = field(default_factory=list)
    avg_monthly_searches: Optional[int] = None
    competition: Optional[str] = None
    competition_index: Optional[int] = None
    low_top_of_page_bid_micros: Optional[int] = None
    high_top_of_page_bid_micros: Optional[int] = None
    monthly_search_volumes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable copy for workflow state or exports."""
        return {
            "keyword": self.keyword,
            "sources": list(self.sources),
            "seed_keywords": list(self.seed_keywords),
            "avg_monthly_searches": self.avg_monthly_searches,
            "competition": self.competition,
            "competition_index": self.competition_index,
            "low_top_of_page_bid_micros": self.low_top_of_page_bid_micros,
            "high_top_of_page_bid_micros": self.high_top_of_page_bid_micros,
            "monthly_search_volumes": [dict(volume) for volume in self.monthly_search_volumes],
        }


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
                - enable_google_browser_fallback: 是否启用 Google 浏览器模拟兜底（默认: False）
                - browser_fallback_timeout_seconds: 浏览器兜底超时时间（默认: 20）
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
        self.enable_public_suggestions = config.get("enable_public_suggestions", True)
        self.google_ads_language = str(config.get("google_ads_language", "languageConstants/1000"))
        self.google_ads_geo_target_constants = list(
            config.get("google_ads_geo_target_constants", ["geoTargetConstants/2840"])
        )
        self.google_ads_keyword_plan_network = str(
            config.get("google_ads_keyword_plan_network", "GOOGLE_SEARCH")
        )
        self.enable_google_browser_fallback = config.get("enable_google_browser_fallback", False)
        self.browser_fallback_timeout_seconds = config.get("browser_fallback_timeout_seconds", 20)

        # 检查是否配置了Google API
        self.has_google_api = bool(self.google_api_key and self.google_search_engine_id)
        self.google_ads_config = {
            key: config.get(key.lower()) or os.getenv(key, "")
            for key in ("GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_LOGIN_CUSTOMER_ID")
        }
        self.has_google_ads_keyword_planner = all(self.google_ads_config.values())
        self._google_ads_access_token: Optional[str] = None
        self.last_result: Optional[KeywordExpansionResult] = None

        # 创建带指数退避重试的 requests Session
        retry_strategy = Retry(
            total=self.max_retries,
            connect=0,
            read=0,
            backoff_factor=self.request_delay_seconds,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        # Do not silently inherit a stale system proxy. The optional project proxy
        # below is the only proxy used, and can be disabled after a quick failure.
        self.session.trust_env = False
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
        self._proxy_active = bool(self.http_proxy)

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
            "google_ads_keyword_planner_requests": 0,
            "google_ads_keyword_planner_failures": 0,
            "google_ads_ideas_with_metrics": 0,
            "google_suggest_requests": 0,
            "google_browser_fallback_requests": 0,
            "bing_suggest_requests": 0,
            "retry_attempts": 0,
        }

        self.logger.info(
            f"关键词扩展器初始化: {node_id}",
            config={
                "max_expansions_per_keyword": self.max_expansions_per_keyword,
                "has_google_api": self.has_google_api,
                "enable_google_browser_fallback": self.enable_google_browser_fallback,
                "google_ads_language": self.google_ads_language,
                "google_ads_geo_target_constants": self.google_ads_geo_target_constants,
                "max_retries": self.max_retries,
                "http_proxy": self.http_proxy,
            }
        )

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """Use the configured proxy when available, then fall back to direct access.

        A local proxy is often transient. Keeping it after a connection refusal
        makes every keyword wait through the retry budget, so disable it once for
        the rest of the batch and continue with a direct request.
        """
        try:
            return self.session.get(url, **kwargs)
        except (ProxyError, RequestsConnectionError) as exc:
            if not self._proxy_active:
                raise
            self._proxy_active = False
            self.session.proxies = {}
            self.logger.warning(f"代理不可用，已切换为直连: {exc}")
            return self.session.get(url, **kwargs)

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
                ideas = self._expand_keyword_ideas(keyword)
                expansions = [idea.keyword for idea in ideas]

                # 记录结果
                if expansions:
                    expansion_result.expanded_keywords.extend(expansions)
                    expansion_result.keyword_sources[keyword] = expansions
                    expansion_result.ideas.extend(ideas)
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
        expansion_result.ideas = self._merge_ideas(
            [
                KeywordIdea(keyword=keyword, sources=["seed"], seed_keywords=[keyword])
                for keyword in keywords
            ] + expansion_result.ideas
        )
        expansion_result.metadata.update({
            "google_ads_keyword_planner_enabled": self.has_google_ads_keyword_planner,
            "keyword_idea_count": len(expansion_result.ideas),
        })
        self.last_result = expansion_result

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
        """Backward-compatible string-only expansion interface."""
        return [idea.keyword for idea in self._expand_keyword_ideas(keyword)]

    def _expand_keyword_ideas(self, keyword: str) -> List[KeywordIdea]:
        """扩展单个关键词

        同时查询 Google Suggest + Bing Suggest（以及可选的 Google Custom Search API），
        只要任一来源成功就继续。合并去重后返回。
        """
        all_ideas: List[KeywordIdea] = []
        source_errors: List[str] = []

        if self.has_google_ads_keyword_planner:
            try:
                planner_expansions = self._get_google_ads_keyword_ideas(keyword)
                self.stats["google_ads_keyword_planner_requests"] += 1
                if planner_expansions:
                    all_ideas.extend(planner_expansions)
                    self.stats["google_ads_ideas_with_metrics"] += sum(
                        1 for idea in planner_expansions
                        if idea.avg_monthly_searches is not None
                    )
            except Exception as exc:
                self.stats["google_ads_keyword_planner_failures"] += 1
                self.logger.warning(f"Google Ads Keyword Planner 失败: {exc}")
                source_errors.append(f"Google Ads Keyword Planner: {exc}")

        # 1. Google Custom Search API（需配置 API 密钥）
        if self.enable_public_suggestions and self.has_google_api:
            self.logger.debug(f"尝试 Google Custom Search API: {keyword}")
            try:
                expansions = self._expand_with_google_custom_search(keyword)
                if expansions:
                    self.stats["api_requests"] += 1
                    all_ideas.extend(
                        self._ideas_from_strings(expansions, "google_custom_search", keyword)
                    )
                    self.logger.debug(f"Custom Search API 成功", keyword=keyword, count=len(expansions))
            except Exception as e:
                err_msg = f"Google Custom Search API: {e}"
                self.logger.warning(err_msg)
                source_errors.append(err_msg)

        # 2. Google Suggest（优先使用公开端点；可选浏览器兜底）
        self.logger.debug(f"尝试 Google Suggest: {keyword}")
        google_expansions: List[str] = []
        google_error: Optional[Exception] = None
        try:
            if not self.enable_public_suggestions:
                raise RuntimeError("公共建议源已禁用")
            google_expansions = self._get_google_suggestions(keyword)
            if google_expansions:
                self.stats["google_suggest_requests"] += 1
                all_ideas.extend(
                    self._ideas_from_strings(google_expansions, "google_suggest", keyword)
                )
                self.logger.debug(f"Google Suggest 成功", keyword=keyword, count=len(google_expansions))
            else:
                raise RuntimeError("Google Suggest 返回空结果")
        except Exception as e:
            google_error = e
            self.logger.warning(f"Google Suggest 失败: {e}")
            source_errors.append(f"Google Suggest: {e}")

        if (
            self.enable_public_suggestions
            and not google_expansions
            and self.enable_google_browser_fallback
        ):
            self.logger.debug(f"尝试 Google 浏览器模拟兜底: {keyword}")
            try:
                browser_expansions = self._get_google_suggestions_via_browser(keyword)
                if browser_expansions:
                    self.stats["google_browser_fallback_requests"] += 1
                    all_ideas.extend(
                        self._ideas_from_strings(
                            browser_expansions, "google_browser_fallback", keyword
                        )
                    )
                    google_expansions = browser_expansions
                    self.logger.debug(
                        f"Google 浏览器兜底成功",
                        keyword=keyword,
                        count=len(browser_expansions)
                    )
            except Exception as e:
                self.logger.warning(f"Google 浏览器兜底失败: {e}")
                source_errors.append(f"Google Browser Fallback: {e}")

        # 3. Bing Suggest（与 Google 并行兜底，任一成功即可）
        self.logger.debug(f"尝试 Bing Suggest: {keyword}")
        bing_expansions: List[str] = []
        try:
            if not self.enable_public_suggestions:
                raise RuntimeError("公共建议源已禁用")
            bing_expansions = self._get_bing_suggestions(keyword)
            if bing_expansions:
                self.stats["bing_suggest_requests"] += 1
                all_ideas.extend(
                    self._ideas_from_strings(bing_expansions, "bing_suggest", keyword)
                )
                self.logger.debug(f"Bing Suggest 成功", keyword=keyword, count=len(bing_expansions))
            else:
                raise RuntimeError("Bing Suggest 返回空结果")
        except Exception as e:
            self.logger.warning(f"Bing Suggest 失败: {e}")
            source_errors.append(f"Bing Suggest: {e}")

        if not all_ideas:
            error_text = "; ".join(source_errors) if source_errors else "无可用扩展来源"
            raise RuntimeError(f"关键词 '{keyword}': 所有扩展来源都不可用 — {error_text}")

        unique = [
            idea for idea in self._merge_ideas(all_ideas)
            if idea.keyword.lower() != keyword.lower()
        ]
        return self._select_top_ideas(unique, self.max_expansions_per_keyword)

    @staticmethod
    def _select_top_ideas(ideas: List[KeywordIdea], limit: int) -> List[KeywordIdea]:
        """按平均月搜索量降序取前 limit 条。

        Keyword Planner 一次可能返回上百条候选，直接切片等于按 API 返回顺序截断，
        会把高搜索量的词丢掉。这里改为按需求量排序后再截断，保证每个种子词产出的
        是最有流量价值的词。

        没有搜索量数据的情况（Suggest 类来源不带指标，或 Planner 未返回
        avgMonthlySearches）按 0 处理，排在有数据的词之后；同分时保持原顺序。
        """
        def sort_key(indexed_idea: Tuple[int, KeywordIdea]) -> Tuple[int, int]:
            index, idea = indexed_idea
            volume = idea.avg_monthly_searches
            return (-(volume if volume is not None else 0), index)

        ranked = sorted(enumerate(ideas), key=sort_key)
        return [idea for _, idea in ranked[:limit]]

    @staticmethod
    def _ideas_from_strings(
        keywords: List[str], source: str, seed_keyword: str
    ) -> List[KeywordIdea]:
        return [
            KeywordIdea(
                keyword=str(item).strip(),
                sources=[source],
                seed_keywords=[seed_keyword],
            )
            for item in keywords
            if str(item).strip()
        ]

    @staticmethod
    def _merge_ideas(ideas: List[KeywordIdea]) -> List[KeywordIdea]:
        """Merge duplicate phrases, retaining all sources and Planner metrics."""
        merged: Dict[str, KeywordIdea] = {}
        for idea in ideas:
            normalized = idea.keyword.strip().lower()
            if not normalized:
                continue
            if normalized not in merged:
                merged[normalized] = KeywordIdea(
                    keyword=idea.keyword.strip(),
                    sources=list(idea.sources),
                    seed_keywords=list(idea.seed_keywords),
                    avg_monthly_searches=idea.avg_monthly_searches,
                    competition=idea.competition,
                    competition_index=idea.competition_index,
                    low_top_of_page_bid_micros=idea.low_top_of_page_bid_micros,
                    high_top_of_page_bid_micros=idea.high_top_of_page_bid_micros,
                    monthly_search_volumes=[dict(volume) for volume in idea.monthly_search_volumes],
                )
                continue

            current = merged[normalized]
            current.sources = list(dict.fromkeys(current.sources + idea.sources))
            current.seed_keywords = list(dict.fromkeys(current.seed_keywords + idea.seed_keywords))
            for metric in (
                "avg_monthly_searches", "competition", "competition_index",
                "low_top_of_page_bid_micros", "high_top_of_page_bid_micros",
            ):
                if getattr(current, metric) is None and getattr(idea, metric) is not None:
                    setattr(current, metric, getattr(idea, metric))
            if not current.monthly_search_volumes and idea.monthly_search_volumes:
                current.monthly_search_volumes = [dict(volume) for volume in idea.monthly_search_volumes]
        return list(merged.values())

    def _get_google_ads_keyword_ideas(self, keyword: str) -> List[KeywordIdea]:
        """Return Planner ideas with demand and commercial metrics (US English)."""
        cfg = self.google_ads_config
        if not self._google_ads_access_token:
            token_response = self.session.post(
                "https://oauth2.googleapis.com/token",
                data={"grant_type": "refresh_token", "client_id": cfg["GOOGLE_ADS_CLIENT_ID"], "client_secret": cfg["GOOGLE_ADS_CLIENT_SECRET"], "refresh_token": cfg["GOOGLE_ADS_REFRESH_TOKEN"]},
                timeout=20,
            )
            token_response.raise_for_status()
            self._google_ads_access_token = token_response.json()["access_token"]

        response = self.session.post(
            f"https://googleads.googleapis.com/v25/customers/{cfg['GOOGLE_ADS_CUSTOMER_ID']}:generateKeywordIdeas",
            headers={"Authorization": f"Bearer {self._google_ads_access_token}", "developer-token": cfg["GOOGLE_ADS_DEVELOPER_TOKEN"], "login-customer-id": cfg["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]},
            json={
                "language": self.google_ads_language,
                "geoTargetConstants": self.google_ads_geo_target_constants,
                "keywordPlanNetwork": self.google_ads_keyword_plan_network,
                "includeAdultKeywords": False,
                "keywordSeed": {"keywords": [keyword]},
            },
            timeout=30,
        )
        response.raise_for_status()
        ideas: List[KeywordIdea] = []
        for item in response.json().get("results", []):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            metrics = item.get("keywordIdeaMetrics") or {}
            volumes = [
                {
                    "year": volume.get("year"),
                    "month": volume.get("month"),
                    "monthly_searches": self._as_optional_int(volume.get("monthlySearches")),
                }
                for volume in metrics.get("monthlySearchVolumes") or []
                if isinstance(volume, dict)
            ]
            ideas.append(KeywordIdea(
                keyword=text,
                sources=["google_ads_keyword_planner"],
                seed_keywords=[keyword],
                avg_monthly_searches=self._as_optional_int(metrics.get("avgMonthlySearches")),
                competition=metrics.get("competition"),
                competition_index=self._as_optional_int(metrics.get("competitionIndex")),
                low_top_of_page_bid_micros=self._as_optional_int(metrics.get("lowTopOfPageBidMicros")),
                high_top_of_page_bid_micros=self._as_optional_int(metrics.get("highTopOfPageBidMicros")),
                monthly_search_volumes=volumes,
            ))
        return ideas

    @staticmethod
    def _as_optional_int(value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _check_robots_txt(self, url: str) -> bool:
        """检查 robots.txt 是否允许抓取，结果按域名缓存"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url in self._robots_cache:
            return self._robots_cache[base_url]

        try:
            robots_url = urljoin(base_url, "/robots.txt")
            response = self._get(robots_url, timeout=5)
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

            response = self._get(url, params=params, timeout=10)
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
                response = self._get(endpoint, timeout=5)
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

    def _get_google_suggestions_via_browser(self, keyword: str) -> List[str]:
        """通过浏览器模拟获取 Google 搜索建议（可选兜底）"""
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as e:
            self.logger.warning(f"Playwright 未安装，无法启用浏览器兜底: {e}")
            return []

        search_url = "https://www.google.com/?hl=en"
        suggestions: List[str] = []

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(user_agent=self.USER_AGENT)
                page.set_default_timeout(int(self.browser_fallback_timeout_seconds * 1000))
                page.goto(search_url, wait_until="domcontentloaded")

                search_box = page.locator("textarea[name='q'], input[name='q']").first
                search_box.click()
                page.keyboard.type(keyword, delay=80)

                try:
                    page.wait_for_timeout(1200)
                except Exception:
                    pass

                selectors = [
                    "div[role='listbox'] [role='option']",
                    "div[role='listbox'] li",
                    "ul[role='listbox'] li",
                    "ul[role='listbox'] div",
                    "[aria-label='Search suggestions'] li",
                ]

                for selector in selectors:
                    try:
                        locator = page.locator(selector)
                        if locator.count() > 0:
                            suggestions.extend(locator.all_inner_texts())
                    except PlaywrightTimeoutError:
                        continue
                    except Exception:
                        continue

                browser.close()

        except Exception as e:
            self.logger.warning(f"浏览器模拟获取 Google Suggest 失败: {e}")
            return []

        cleaned: List[str] = []
        seen: set = set()
        keyword_lower = keyword.lower()
        for item in suggestions:
            suggestion = re.sub(r"\s+", " ", str(item)).strip()
            if not suggestion:
                continue
            suggestion_lower = suggestion.lower()
            if suggestion_lower == keyword_lower or suggestion_lower in seen:
                continue
            seen.add(suggestion_lower)
            cleaned.append(suggestion)

        return cleaned[:self.max_expansions_per_keyword]

    def _get_bing_suggestions(self, keyword: str) -> List[str]:
        """获取Bing搜索建议（下拉框推荐）

        使用 Bing osjson.aspx 公共端点（无需 API 密钥），
        响应格式为 ["keyword", ["suggestion1", "suggestion2", ...]]。
        """
        encoded_keyword = quote(keyword)
        url = self.BING_SUGGEST_ENDPOINT.format(query=encoded_keyword)

        try:
            response = self._get(url, timeout=5)
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
            google_ads_keyword_planner_requests=self.stats["google_ads_keyword_planner_requests"],
            google_ads_keyword_planner_failures=self.stats["google_ads_keyword_planner_failures"],
            google_ads_ideas_with_metrics=self.stats["google_ads_ideas_with_metrics"],
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

    def get_keyword_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Return research data keyed by keyword without changing the old output API."""
        if not self.last_result:
            return {}
        return {
            idea.keyword: idea.to_dict()
            for idea in self.last_result.ideas
        }


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
    "KeywordIdea",
    "KeywordExpander",
    "expand_keywords",
]
