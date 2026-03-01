"""
关键词筛选器单元测试
"""
import pytest
from unittest.mock import Mock, patch

from src.modules.keyword_filter.ai_filter import AIKeywordFilter


class TestAIKeywordFilter:
    """AI关键词筛选器测试类"""

    def test_initialization(self):
        """测试初始化"""
        filter_node = AIKeywordFilter("test-filter")
        assert filter_node.node_id == "test-filter"
        assert filter_node.node_type == "keyword_filter"
        assert filter_node.config == {}

    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "batch_size": 50,
            "confidence_threshold": 0.7,
            "enable_fallback": True,
            "language": "en"
        }
        filter_node = AIKeywordFilter("test-filter", config)
        assert filter_node.batch_size == 50
        assert filter_node.confidence_threshold == 0.7
        assert filter_node.enable_fallback == True
        assert filter_node.language == "en"

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_execute_with_keywords(self, mock_get_ai_client):
        """测试执行关键词筛选"""
        # 模拟AI客户端
        mock_client = Mock()
        mock_response = "[\"hardware tools\", \"lighting accessories\"]"
        mock_client.chat_completion.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        filter_node = AIKeywordFilter("test-filter")
        filter_node.set_ai_client(mock_client)

        keywords = ["hardware tools", "lighting accessories", "unrelated topic"]
        result = filter_node.execute(keywords)

        # 验证结果
        assert isinstance(result, list)
        assert len(result) == 2
        assert "hardware tools" in result
        assert "lighting accessories" in result

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_execute_with_empty_keywords(self, mock_get_ai_client):
        """测试执行空关键词列表"""
        filter_node = AIKeywordFilter("test-filter")

        result = filter_node.execute([])
        assert result == []

    def test_validate_input(self):
        """测试输入验证"""
        filter_node = AIKeywordFilter("test-filter")

        # 有效输入
        assert filter_node.validate_input(["keyword1", "keyword2"]) == True

        # 无效输入
        assert filter_node.validate_input(None) == False
        assert filter_node.validate_input("not a list") == False
        assert filter_node.validate_input([]) == False

    def test_validate_output(self):
        """测试输出验证"""
        filter_node = AIKeywordFilter("test-filter")

        # 有效输出
        assert filter_node.validate_output(["keyword1", "keyword2"]) == True

        # 无效输出
        assert filter_node.validate_output(None) == False
        assert filter_node.validate_output("not a list") == False
        assert filter_node.validate_output([]) == True  # 空列表可能有效

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_execute_with_ai_error(self, mock_get_ai_client):
        """测试AI错误处理"""
        # 模拟AI客户端抛出异常
        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("API error")
        mock_get_ai_client.return_value = mock_client

        filter_node = AIKeywordFilter("test-filter", {"enable_fallback": True})
        filter_node.set_ai_client(mock_client)

        keywords = ["hardware tools", "lighting accessories"]

        # 当启用回退时，应该返回原始关键词
        result = filter_node.execute(keywords)
        assert result == keywords

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_execute_without_fallback(self, mock_get_ai_client):
        """测试禁用回退的AI错误"""
        # 模拟AI客户端抛出异常
        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("API error")
        mock_get_ai_client.return_value = mock_client

        filter_node = AIKeywordFilter("test-filter", {"enable_fallback": False})
        filter_node.set_ai_client(mock_client)

        keywords = ["hardware tools", "lighting accessories"]

        # 当禁用回退时，应该抛出异常
        with pytest.raises(Exception):
            filter_node.execute(keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])