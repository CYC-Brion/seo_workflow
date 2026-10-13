"""
关键词扩展器单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.modules.keyword_expander.keyword_expander import (
    KeywordExpander,
    KeywordExpansionResult,
    expand_keywords
)


class TestKeywordExpander:
    """关键词扩展器测试类"""

    def test_initialization(self):
        """测试初始化"""
        expander = KeywordExpander("test-expander")
        assert expander.node_id == "test-expander"
        assert expander.node_type == "keyword_expander"
        assert expander.config == {}
        assert expander.max_expansions_per_keyword == 10
        assert expander.request_delay_seconds == 2

    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "max_expansions_per_keyword": 5,
            "request_delay_seconds": 1.5,
            "max_retries": 2,
            "google_api_key": "test-key",
            "google_search_engine_id": "test-engine-id"
        }
        expander = KeywordExpander("test-expander", config)
        assert expander.max_expansions_per_keyword == 5
        assert expander.request_delay_seconds == 1.5
        assert expander.max_retries == 2
        assert expander.google_api_key == "test-key"
        assert expander.google_search_engine_id == "test-engine-id"
        assert expander.has_google_api == True

    def test_validate_input_with_list(self):
        """测试列表输入验证"""
        expander = KeywordExpander("test-expander")
        keywords = ["hardware tools", "lighting accessories"]
        validated = expander._validate_and_prepare_input(keywords)
        assert validated == keywords

    def test_validate_input_with_string(self):
        """测试字符串输入验证"""
        expander = KeywordExpander("test-expander")
        input_str = "hardware tools, lighting accessories"
        validated = expander._validate_and_prepare_input(input_str)
        assert validated == ["hardware tools", "lighting accessories"]

    def test_validate_input_with_json_string(self):
        """测试JSON字符串输入验证"""
        expander = KeywordExpander("test-expander")
        input_str = '["hardware tools", "lighting accessories"]'
        validated = expander._validate_and_prepare_input(input_str)
        assert validated == ["hardware tools", "lighting accessories"]

    def test_validate_input_with_newline_separated(self):
        """测试换行分隔的字符串输入"""
        expander = KeywordExpander("test-expander")
        input_str = "hardware tools\nlighting accessories\nmetal parts"
        validated = expander._validate_and_prepare_input(input_str)
        assert validated == ["hardware tools", "lighting accessories", "metal parts"]

    def test_validate_input_empty(self):
        """测试空输入"""
        expander = KeywordExpander("test-expander")
        with pytest.raises(ValueError):
            expander._validate_and_prepare_input([])
        with pytest.raises(ValueError):
            expander._validate_and_prepare_input("")

    def test_validate_input_invalid_type(self):
        """测试无效输入类型"""
        expander = KeywordExpander("test-expander")
        with pytest.raises(ValueError):
            expander._validate_and_prepare_input(123)

    def test_google_suggest_success(self):
        """测试 Google Suggest 成功获取建议"""
        expander = KeywordExpander("test-expander")
        mock_response = MagicMock()
        mock_response.json.return_value = [
            "metal hardware",
            ["metal hardware manufacturers", "metal hardware suppliers", "metal hardware parts"]
        ]
        mock_response.raise_for_status.return_value = None

        with patch.object(expander.session, 'get', return_value=mock_response):
            expansions = expander._get_google_suggestions("metal hardware")
            assert len(expansions) > 0
            assert "metal hardware manufacturers" in expansions
            assert expansions[0] != "metal hardware"  # 原关键词应被过滤

    def test_google_suggest_deduplication(self):
        """测试 Google Suggest 去重"""
        expander = KeywordExpander("test-expander")
        mock_response = MagicMock()
        mock_response.json.return_value = [
            "test",
            ["Test Keyword", "test keyword", "TEST KEYWORD"]
        ]
        mock_response.raise_for_status.return_value = None

        with patch.object(expander.session, 'get', return_value=mock_response):
            expansions = expander._get_google_suggestions("test")
            assert len(expansions) == 1  # 三个相同建议去重后只剩1个

    def test_bing_suggest_success(self):
        """测试 Bing Suggest 成功获取建议"""
        expander = KeywordExpander("test-expander")
        mock_response = MagicMock()
        mock_response.json.return_value = [
            "metal hardware",
            ["metal hardware manufacturers", "metal hardware suppliers"]
        ]
        mock_response.raise_for_status.return_value = None

        with patch.object(expander.session, 'get', return_value=mock_response):
            expansions = expander._get_bing_suggestions("metal hardware")
            assert len(expansions) == 2
            assert "metal hardware manufacturers" in expansions

    def test_bing_suggest_failure_raises(self):
        """测试 Bing Suggest 失败时抛出异常（不再静默跳过）"""
        expander = KeywordExpander("test-expander")

        with patch.object(expander.session, 'get', side_effect=requests.exceptions.ConnectionError("timeout")):
            with pytest.raises(requests.exceptions.ConnectionError):
                expander._get_bing_suggestions("test")

    def test_expand_keyword_merges_google_and_bing(self):
        """测试合并 Google + Bing 建议并去重"""
        expander = KeywordExpander("test-expander")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                resp.json.return_value = ["test", ["shared suggestion", "google only"]]
            elif "api.bing.com" in url:
                resp.json.return_value = ["test", ["shared suggestion", "bing only"]]
            else:
                resp.json.return_value = ["", []]
            return resp

        with patch.object(expander.session, 'get', side_effect=mock_get):
            expansions = expander._expand_keyword("test")
            # 去重: shared suggestion 只出现一次
            assert "shared suggestion" in expansions
            assert "google only" in expansions
            assert "bing only" in expansions
            # 不应包含原始关键词
            assert "test" not in expansions
            # 验证两个渠道都被调用了
            assert expander.stats["google_suggest_requests"] == 1
            assert expander.stats["bing_suggest_requests"] == 1

    def test_expand_keyword_google_fail_bing_success(self):
        """测试 Google 失败时仍可用 Bing 结果继续"""
        expander = KeywordExpander("test-expander")

        def mock_get(url, *args, **kwargs):
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                raise requests.exceptions.ConnectionError("Google blocked")
            elif "api.bing.com" in url:
                resp = MagicMock()
                resp.json.return_value = ["test", ["bing suggestion 1"]]
                resp.raise_for_status.return_value = None
                return resp
            return MagicMock()

        with patch.object(expander.session, 'get', side_effect=mock_get):
            expansions = expander._expand_keyword("test")
            assert "bing suggestion 1" in expansions
            assert "test" not in expansions

    def test_expand_keyword_google_browser_fallback_used_when_enabled(self):
        """测试 Google 失败时可选启用浏览器兜底"""
        expander = KeywordExpander(
            "test-expander",
            {
                "enable_google_browser_fallback": True,
                "browser_fallback_timeout_seconds": 5,
            }
        )

        def mock_get(url, *args, **kwargs):
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                raise requests.exceptions.ConnectionError("Google blocked")
            elif "api.bing.com" in url:
                resp = MagicMock()
                resp.json.return_value = ["test", ["bing suggestion 1"]]
                resp.raise_for_status.return_value = None
                return resp
            return MagicMock()

        with patch.object(expander.session, 'get', side_effect=mock_get):
            with patch.object(expander, '_get_google_suggestions_via_browser', return_value=["browser suggestion 1"]):
                expansions = expander._expand_keyword("test")
                assert "browser suggestion 1" in expansions
                assert "bing suggestion 1" in expansions
                assert expander.stats["google_browser_fallback_requests"] == 1

    def test_expand_keyword_all_sources_fail_raises_error(self):
        """测试所有扩展来源都失败时抛出异常"""
        expander = KeywordExpander("test-expander")

        def mock_get(url, *args, **kwargs):
            raise requests.exceptions.ConnectionError("Network down")

        with patch.object(expander.session, 'get', side_effect=mock_get):
            with pytest.raises(RuntimeError, match="所有扩展来源都不可用"):
                expander._expand_keyword("test")

    def test_execute_success(self):
        """测试完整的执行流程（Google + Bing 合并去重）"""
        expander = KeywordExpander("test-expander")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                resp.json.return_value = [
                    "hardware",
                    ["hardware tools", "hardware supplies"]
                ]
            elif "api.bing.com" in url:
                resp.json.return_value = [
                    "hardware",
                    ["hardware parts", "hardware supplies"]  # "hardware supplies" 与 Google 重复
                ]
            else:
                resp.json.return_value = ["", []]
            return resp

        with patch.object(expander.session, 'get', side_effect=mock_get):
            result = expander.execute_impl(["hardware"])
            assert isinstance(result, list)
            assert len(result) > 1  # 原词 + 扩展
            assert "hardware" in result
            assert "hardware tools" in result
            assert "hardware parts" in result

    def test_validate_input_method(self):
        """测试输入验证方法"""
        expander = KeywordExpander("test-expander")
        assert expander.validate_input(["keyword1", "keyword2"]) == True
        assert expander.validate_input("keyword1, keyword2") == True
        assert expander.validate_input(None) == False
        assert expander.validate_input(123) == False
        assert expander.validate_input([]) == False

    def test_validate_output_method(self):
        """测试输出验证方法"""
        expander = KeywordExpander("test-expander")
        assert expander.validate_output(["keyword1", "keyword2"]) == True
        assert expander.validate_output(None) == False
        assert expander.validate_output([]) == False
        assert expander.validate_output("not a list") == False
        assert expander.validate_output([123, "keyword"]) == False
        assert expander.validate_output(["", "keyword"]) == False

    def test_pre_execute(self):
        """测试执行前处理"""
        expander = KeywordExpander("test-expander")
        result = expander.pre_execute(["test"])
        assert result == ["test"]
        assert expander.stats["total_keywords"] == 0

    def test_post_execute(self):
        """测试执行后处理"""
        expander = KeywordExpander("test-expander")
        output = ["keyword1", "keyword2"]
        result = expander.post_execute(output)
        assert result == output

    def test_get_statistics(self):
        """测试获取统计信息"""
        expander = KeywordExpander("test-expander")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                resp.json.return_value = ["metal hardware", ["metal hardware suppliers"]]
            elif "api.bing.com" in url:
                resp.json.return_value = ["metal hardware", ["metal hardware catalog"]]
            else:
                resp.json.return_value = ["", []]
            return resp

        with patch.object(expander.session, 'get', side_effect=mock_get):
            expander.execute_impl(["metal hardware"])

        stats = expander.get_statistics()
        assert isinstance(stats, dict)
        assert "total_keywords" in stats
        assert "keywords_expanded" in stats
        assert "google_suggest_requests" in stats
        assert "bing_suggest_requests" in stats

    def test_keyword_expansion_result_dataclass(self):
        """测试KeywordExpansionResult数据类"""
        result = KeywordExpansionResult(
            original_keywords=["kw1", "kw2"],
            expanded_keywords=["exp1", "exp2"],
            keyword_sources={"kw1": ["exp1"]},
            expansion_stats={"count": 1},
            metadata={"method": "google_suggest"}
        )
        assert result.original_keywords == ["kw1", "kw2"]
        assert result.expanded_keywords == ["exp1", "exp2"]
        assert result.keyword_sources == {"kw1": ["exp1"]}

    def test_google_ads_ideas_keep_keyword_planner_metrics(self):
        """Keyword Planner metrics must survive parsing instead of being discarded."""
        expander = KeywordExpander("test-expander")
        expander.google_ads_config = {
            "GOOGLE_ADS_DEVELOPER_TOKEN": "developer-token",
            "GOOGLE_ADS_CLIENT_ID": "client-id",
            "GOOGLE_ADS_CLIENT_SECRET": "client-secret",
            "GOOGLE_ADS_REFRESH_TOKEN": "refresh-token",
            "GOOGLE_ADS_CUSTOMER_ID": "123",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "456",
        }
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "access-token"}
        token_response.raise_for_status.return_value = None
        ideas_response = MagicMock()
        ideas_response.json.return_value = {
            "results": [{
                "text": "lamp hardware supplier",
                "keywordIdeaMetrics": {
                    "avgMonthlySearches": "90",
                    "competition": "MEDIUM",
                    "competitionIndex": "42",
                    "lowTopOfPageBidMicros": "1200000",
                    "highTopOfPageBidMicros": "3400000",
                    "monthlySearchVolumes": [{
                        "year": "2026", "month": "JANUARY", "monthlySearches": "100"
                    }],
                },
            }]
        }
        ideas_response.raise_for_status.return_value = None

        with patch.object(expander.session, "post", side_effect=[token_response, ideas_response]):
            ideas = expander._get_google_ads_keyword_ideas("lighting hardware")

        assert len(ideas) == 1
        assert ideas[0].avg_monthly_searches == 90
        assert ideas[0].competition == "MEDIUM"
        assert ideas[0].competition_index == 42
        assert ideas[0].low_top_of_page_bid_micros == 1200000
        assert ideas[0].monthly_search_volumes == [
            {"year": "2026", "month": "JANUARY", "monthly_searches": 100}
        ]

    def test_google_ads_request_uses_configured_market(self):
        expander = KeywordExpander(
            "test-expander",
            config={
                "google_ads_language": "languageConstants/1001",
                "google_ads_geo_target_constants": ["geoTargetConstants/2826"],
            },
        )
        expander.google_ads_config = {
            "GOOGLE_ADS_DEVELOPER_TOKEN": "developer-token",
            "GOOGLE_ADS_CLIENT_ID": "client-id",
            "GOOGLE_ADS_CLIENT_SECRET": "client-secret",
            "GOOGLE_ADS_REFRESH_TOKEN": "refresh-token",
            "GOOGLE_ADS_CUSTOMER_ID": "123",
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "456",
        }
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "access-token"}
        token_response.raise_for_status.return_value = None
        ideas_response = MagicMock()
        ideas_response.json.return_value = {"results": []}
        ideas_response.raise_for_status.return_value = None

        with patch.object(expander.session, "post", side_effect=[token_response, ideas_response]) as post:
            expander._get_google_ads_keyword_ideas("lamp parts")

        assert post.call_args_list[1].kwargs["json"]["language"] == "languageConstants/1001"
        assert post.call_args_list[1].kwargs["json"]["geoTargetConstants"] == ["geoTargetConstants/2826"]
        assert post.call_args_list[1].kwargs["json"]["keywordPlanNetwork"] == "GOOGLE_SEARCH"

    def test_metadata_merges_sources_and_retains_planner_values(self):
        """The same phrase from several sources should be one auditable record."""
        expander = KeywordExpander("test-expander")
        planner = KeywordExpansionResult(
            original_keywords=[], expanded_keywords=[], keyword_sources={},
            expansion_stats={}, metadata={}
        )
        del planner  # Ensure the test uses the public metadata representation below.
        from src.modules.keyword_expander.keyword_expander import KeywordIdea
        merged = expander._merge_ideas([
            KeywordIdea("Lamp Parts", ["google_suggest"], ["lamp parts"]),
            KeywordIdea("lamp parts", ["google_ads_keyword_planner"], ["lighting hardware"], 70, "LOW"),
        ])
        assert len(merged) == 1
        assert merged[0].sources == ["google_suggest", "google_ads_keyword_planner"]
        assert merged[0].seed_keywords == ["lamp parts", "lighting hardware"]
        assert merged[0].avg_monthly_searches == 70
        assert merged[0].competition == "LOW"


class TestExpandKeywordsFunction:
    """expand_keywords函数测试类"""

    def test_expand_keywords_function(self):
        """测试便捷函数"""
        keywords = ["metal hardware"]

        def mock_get(self, url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                resp.json.return_value = ["metal hardware", ["metal hardware suppliers"]]
            elif "api.bing.com" in url:
                resp.json.return_value = ["metal hardware", ["metal hardware catalog"]]
            else:
                resp.json.return_value = ["", []]
            return resp

        with patch("requests.Session.get", mock_get):
            expanded_keywords, stats = expand_keywords(
                keywords,
                max_expansions_per_keyword=5,
                request_delay_seconds=0.1,
            )
            assert isinstance(expanded_keywords, list)
            assert isinstance(stats, dict)
            assert len(expanded_keywords) > len(keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
