"""
关键词扩展器单元测试
"""
import pytest
from unittest.mock import Mock, patch
import time

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
        assert expander.use_mock_data == True

    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "max_expansions_per_keyword": 5,
            "request_delay_seconds": 1.5,
            "max_retries": 2,
            "use_mock_data": False,
            "enable_manual_fallback": False,
            "google_api_key": "test-key",
            "google_search_engine_id": "test-engine-id"
        }
        expander = KeywordExpander("test-expander", config)
        assert expander.max_expansions_per_keyword == 5
        assert expander.request_delay_seconds == 1.5
        assert expander.max_retries == 2
        assert expander.use_mock_data == False
        assert expander.enable_manual_fallback == False
        assert expander.google_api_key == "test-key"
        assert expander.google_search_engine_id == "test-engine-id"
        assert expander.has_google_api == True

    def test_validate_input_with_list(self):
        """测试列表输入验证"""
        expander = KeywordExpander("test-expander")

        # 有效列表输入
        keywords = ["hardware tools", "lighting accessories"]
        validated = expander._validate_and_prepare_input(keywords)
        assert validated == keywords

    def test_validate_input_with_string(self):
        """测试字符串输入验证"""
        expander = KeywordExpander("test-expander")

        # 逗号分隔的字符串
        input_str = "hardware tools, lighting accessories"
        validated = expander._validate_and_prepare_input(input_str)
        assert validated == ["hardware tools", "lighting accessories"]

    def test_validate_input_with_json_string(self):
        """测试JSON字符串输入验证"""
        expander = KeywordExpander("test-expander")

        # JSON字符串
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

    def test_expand_with_mock_data(self):
        """测试使用模拟数据扩展"""
        expander = KeywordExpander("test-expander", {"use_mock_data": True})

        # 测试已知的模拟关键词
        expansions = expander._expand_with_mock_data("metal hardware")
        assert len(expansions) > 0
        assert "metal hardware supplies" in expansions

    def test_expand_with_patterns(self):
        """测试基于模式的扩展"""
        expander = KeywordExpander("test-expander", {"use_mock_data": False})

        expansions = expander._expand_with_patterns("test keyword")
        assert len(expansions) > 0
        assert "test keyword manufacturers" in expansions
        assert "custom test keyword" in expansions

    def test_expand_keyword_with_mock(self):
        """测试关键词扩展（使用模拟数据）"""
        expander = KeywordExpander("test-expander", {"use_mock_data": True})

        expansions = expander._expand_keyword("metal hardware")
        assert len(expansions) > 0
        assert len(expansions) <= expander.max_expansions_per_keyword

    def test_expand_keyword_without_api(self):
        """测试无API时的关键词扩展"""
        expander = KeywordExpander("test-expander", {
            "use_mock_data": False,
            "google_api_key": None
        })

        expansions = expander._expand_keyword("test keyword")
        assert len(expansions) > 0

    def test_execute_with_keywords(self):
        """测试执行关键词扩展"""
        expander = KeywordExpander("test-expander", {"use_mock_data": True})

        keywords = ["metal hardware", "lighting accessories"]
        result = expander.execute(keywords)

        assert isinstance(result, list)
        assert len(result) > len(keywords)  # 应该包含扩展关键词
        assert "metal hardware" in result
        assert "lighting accessories" in result

    def test_execute_with_single_keyword(self):
        """测试执行单个关键词扩展"""
        expander = KeywordExpander("test-expander", {"use_mock_data": True})

        result = expander.execute(["metal hardware"])
        assert isinstance(result, list)
        assert len(result) > 1

    def test_validate_input_method(self):
        """测试输入验证方法"""
        expander = KeywordExpander("test-expander")

        # 有效输入
        assert expander.validate_input(["keyword1", "keyword2"]) == True
        assert expander.validate_input("keyword1, keyword2") == True

        # 无效输入
        assert expander.validate_input(None) == False
        assert expander.validate_input(123) == False
        assert expander.validate_input([]) == False

    def test_validate_output_method(self):
        """测试输出验证方法"""
        expander = KeywordExpander("test-expander")

        # 有效输出
        assert expander.validate_output(["keyword1", "keyword2"]) == True

        # 无效输出
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
        assert expander.stats["total_keywords"] == 0  # 尚未统计

    def test_post_execute(self):
        """测试执行后处理"""
        expander = KeywordExpander("test-expander")
        output = ["keyword1", "keyword2"]
        result = expander.post_execute(output)
        assert result == output

    def test_get_statistics(self):
        """测试获取统计信息"""
        expander = KeywordExpander("test-expander")

        # 执行一些操作
        expander.execute(["metal hardware"])

        stats = expander.get_statistics()
        assert isinstance(stats, dict)
        assert "total_keywords" in stats
        assert "keywords_expanded" in stats

    def test_keyword_expansion_result_dataclass(self):
        """测试KeywordExpansionResult数据类"""
        result = KeywordExpansionResult(
            original_keywords=["kw1", "kw2"],
            expanded_keywords=["exp1", "exp2"],
            keyword_sources={"kw1": ["exp1"]},
            expansion_stats={"count": 1},
            metadata={"method": "mock"}
        )

        assert result.original_keywords == ["kw1", "kw2"]
        assert result.expanded_keywords == ["exp1", "exp2"]
        assert result.keyword_sources == {"kw1": ["exp1"]}


class TestExpandKeywordsFunction:
    """expand_keywords函数测试类"""

    def test_expand_keywords_function(self):
        """测试便捷函数"""
        keywords = ["metal hardware"]
        expanded_keywords, stats = expand_keywords(
            keywords,
            max_expansions_per_keyword=5,
            request_delay_seconds=0.1,
            use_mock_data=True
        )

        assert isinstance(expanded_keywords, list)
        assert isinstance(stats, dict)
        assert len(expanded_keywords) > len(keywords)

    def test_expand_keywords_with_custom_config(self):
        """测试带自定义配置的便捷函数"""
        keywords = ["test keyword"]
        expanded_keywords, stats = expand_keywords(
            keywords,
            max_expansions_per_keyword=3,
            request_delay_seconds=0,
            use_mock_data=True,
            enable_manual_fallback=False
        )

        assert len(expanded_keywords) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])