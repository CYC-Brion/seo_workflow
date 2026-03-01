"""
AI客户端单元测试
使用模拟(mock)避免实际API调用
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.utils.ai_client import (
    get_ai_client,
    AIProvider,
    AIMessage,
    AIMessageRole,
    AIResponse,
    AIError,
    APIError,
    RateLimitError,
    TokenLimitError,
    CostLimitError,
    AIClient,
    OpenAIClient,
    AnthropicClient
)


class TestAIMessage:
    """AIMessage测试类"""

    def test_message_creation(self):
        """测试消息创建"""
        message = AIMessage(role=AIMessageRole.USER, content="Hello")
        assert message.role == AIMessageRole.USER
        assert message.content == "Hello"

    def test_to_dict(self):
        """测试转换为字典"""
        message = AIMessage(role=AIMessageRole.ASSISTANT, content="Hi there")
        result = message.to_dict()
        assert result == {"role": "assistant", "content": "Hi there"}

    def test_from_dict(self):
        """测试从字典创建"""
        data = {"role": "system", "content": "You are a helpful assistant"}
        message = AIMessage.from_dict(data)
        assert message.role == AIMessageRole.SYSTEM
        assert message.content == "You are a helpful assistant"


class TestAIProvider:
    """AIProvider测试类"""

    def test_enum_values(self):
        """测试枚举值"""
        assert AIProvider.OPENAI.value == "openai"
        assert AIProvider.ANTHROPIC.value == "anthropic"
        assert AIProvider.CUSTOM.value == "custom"



class TestAIClientBase:
    """AI客户端基类测试（使用模拟）"""

    @patch('src.utils.ai_client.OpenAIClient')
    def test_get_ai_client_openai(self, mock_openai_client):
        """测试获取OpenAI客户端"""
        # 模拟OpenAIClient实例
        mock_instance = Mock()
        mock_openai_client.return_value = mock_instance

        client = get_ai_client(AIProvider.OPENAI, api_key="test-key")
        assert client == mock_instance
        mock_openai_client.assert_called_once_with(api_key="test-key")

    @patch('src.utils.ai_client.AnthropicClient')
    def test_get_ai_client_anthropic(self, mock_anthropic_client):
        """测试获取Anthropic客户端"""
        mock_instance = Mock()
        mock_anthropic_client.return_value = mock_instance

        client = get_ai_client(AIProvider.ANTHROPIC, api_key="test-key")
        assert client == mock_instance
        mock_anthropic_client.assert_called_once_with(api_key="test-key")

    def test_get_ai_client_invalid(self):
        """测试获取无效的客户端"""
        with pytest.raises(ValueError):
            get_ai_client("invalid_provider")


class TestOpenAIClient:
    """OpenAI客户端测试（模拟）"""

    @patch('src.utils.ai_client.openai', None)
    def test_openai_not_available(self):
        """测试OpenAI不可用的情况"""
        from src.utils.ai_client import OpenAIClient
        with pytest.raises(ImportError):
            OpenAIClient(api_key="test-key")

    @patch('src.utils.ai_client.openai')
    @patch('src.utils.ai_client.OPENAI_AVAILABLE', True)
    def test_openai_initialization(self, mock_openai):
        """测试OpenAI客户端初始化"""
        from src.utils.ai_client import OpenAIClient

        mock_openai.OpenAI.return_value = Mock()

        client = OpenAIClient(api_key="test-key", base_url="http://test.com")

        mock_openai.OpenAI.assert_called_once_with(
            api_key="test-key",
            base_url="http://test.com",
            timeout=30.0,
            max_retries=3
        )
        assert client.client is not None

    @patch('src.utils.ai_client.openai')
    @patch('src.utils.ai_client.OPENAI_AVAILABLE', True)
    def test_openai_chat_completion(self, mock_openai):
        """测试OpenAI聊天完成"""
        from src.utils.ai_client import OpenAIClient

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_response.usage = Mock(total_tokens=10)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        messages = [AIMessage(role=AIMessageRole.USER, content="Hello")]
        response = client.chat_completion(
            messages=messages,
            model="gpt-3.5-turbo",
            temperature=0.7
        )

        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()

    @patch('src.utils.ai_client.openai')
    @patch('src.utils.ai_client.OPENAI_AVAILABLE', True)
    def test_openai_chat_completion_with_error(self, mock_openai):
        """测试OpenAI聊天完成错误"""
        from src.utils.ai_client import OpenAIClient

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai.OpenAI.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        messages = [AIMessage(role=AIMessageRole.USER, content="Hello")]

        with pytest.raises(APIError):
            client.chat_completion(messages=messages, model="gpt-3.5-turbo")


class TestAnthropicClient:
    """Anthropic客户端测试（模拟）"""

    @patch('src.utils.ai_client.anthropic', None)
    def test_anthropic_not_available(self):
        """测试Anthropic不可用的情况"""
        from src.utils.ai_client import AnthropicClient
        with pytest.raises(ImportError):
            AnthropicClient(api_key="test-key")

    @patch('src.utils.ai_client.anthropic')
    @patch('src.utils.ai_client.ANTHROPIC_AVAILABLE', True)
    def test_anthropic_initialization(self, mock_anthropic):
        """测试Anthropic客户端初始化"""
        from src.utils.ai_client import AnthropicClient

        mock_anthropic.Anthropic.return_value = Mock()

        client = AnthropicClient(api_key="test-key", base_url="http://test.com")

        mock_anthropic.Anthropic.assert_called_once_with(
            api_key="test-key",
            base_url="http://test.com",
            timeout=30.0,
            max_retries=3
        )
        assert client.client is not None

    @patch('src.utils.ai_client.anthropic')
    @patch('src.utils.ai_client.ANTHROPIC_AVAILABLE', True)
    def test_anthropic_message_create(self, mock_anthropic):
        """测试Anthropic消息创建"""
        from src.utils.ai_client import AnthropicClient

        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=5)

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        client = AnthropicClient(api_key="test-key")

        messages = [AIMessage(role=AIMessageRole.USER, content="Hello")]
        response = client.chat_completion(
            messages=messages,
            model="claude-3-opus",
            temperature=0.7
        )

        assert response == "Test response"
        mock_client.messages.create.assert_called_once()


class TestAIErrorClasses:
    """AI错误类测试"""

    def test_ai_error(self):
        """测试AIError"""
        error = AIError(message="Test error", details={"code": 500})
        assert str(error) == "Test error"
        assert error.details == {"code": 500}

    def test_api_error(self):
        """测试APIError"""
        error = APIError(message="API error", status_code=429)
        assert "API error" in str(error)
        assert error.status_code == 429

    def test_rate_limit_error(self):
        """测试RateLimitError"""
        error = RateLimitError(message="Rate limited", retry_after=60)
        assert "Rate limited" in str(error)
        assert error.retry_after == 60

    def test_token_limit_error(self):
        """测试TokenLimitError"""
        error = TokenLimitError(
            message="Token limit exceeded",
            max_tokens=1000,
            requested_tokens=1500
        )
        assert "Token limit exceeded" in str(error)
        assert error.max_tokens == 1000
        assert error.requested_tokens == 1500

    def test_cost_limit_error(self):
        """测试CostLimitError"""
        error = CostLimitError(
            message="Cost limit exceeded",
            max_cost=10.0,
            estimated_cost=15.0
        )
        assert "Cost limit exceeded" in str(error)
        assert error.max_cost == 10.0
        assert error.estimated_cost == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])