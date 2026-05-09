"""
AI客户端工具
统一封装OpenAI和Anthropic的API调用
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field

from src.utils import (
    get_logger,
    exception_handler,
    AIError,
    APIError,
    RateLimitError,
    TokenLimitError,
    CostLimitError,
    config_manager,
)

# 尝试导入AI库
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class AIProvider(Enum):
    """AI提供商"""
    AZURE = "azure"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"  # 预留


class AIMessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class AIMessage:
    """AI消息"""
    role: AIMessageRole
    content: str

    def to_dict(self) -> Dict[str, str]:
        """转换为API需要的字典格式"""
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "AIMessage":
        """从字典创建"""
        return cls(role=AIMessageRole(data["role"]), content=data["content"])


@dataclass
class AIResponse:
    """AI响应"""
    content: str
    model: str
    provider: AIProvider
    usage: Dict[str, int]  # 包含tokens使用情况
    cost: float  # 估算成本（美元）
    response_time: float  # 响应时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "usage": self.usage,
            "cost": self.cost,
            "response_time": self.response_time,
            "metadata": self.metadata,
        }


class AIClient(ABC):
    """AI客户端抽象基类"""

    def __init__(
        self,
        provider: AIProvider,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        logger_name: Optional[str] = None
    ):
        """
        初始化AI客户端

        Args:
            provider: AI提供商
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            logger_name: 日志记录器名称
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_logger(logger_name or f"ai_client.{provider.value}.{model}")
        self.exception_handler = exception_handler

        # 成本跟踪
        self.total_cost = 0.0
        self.total_tokens = 0

        self._init_client()

    @abstractmethod
    def _init_client(self) -> None:
        """初始化客户端"""
        pass

    @abstractmethod
    def chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """
        聊天补全

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大tokens数
            **kwargs: 其他模型参数

        Returns:
            AI响应

        Raises:
            AIError: AI相关错误
        """
        pass

    @abstractmethod
    async def chat_completion_async(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """异步聊天补全"""
        pass

    @abstractmethod
    def stream_chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        pass

    def calculate_cost(
        self,
        usage: Dict[str, int],
        cost_per_1k_tokens: Optional[float] = None
    ) -> float:
        """计算成本

        Args:
            usage: 使用情况字典，包含input_tokens和output_tokens
            cost_per_1k_tokens: 每千tokens成本（美元）

        Returns:
            估算成本（美元）
        """
        if cost_per_1k_tokens is None:
            # 从配置获取默认成本
            config = config_manager.get_node_model_config("default")
            cost_per_1k_tokens = getattr(config, "cost_per_1k_tokens", 0.0)

        total_tokens = usage.get("total_tokens", 0)
        if "input_tokens" in usage and "output_tokens" in usage:
            total_tokens = usage["input_tokens"] + usage["output_tokens"]

        cost = (total_tokens / 1000) * cost_per_1k_tokens
        return cost

    def update_cost_tracking(self, response: AIResponse) -> None:
        """更新成本跟踪"""
        self.total_cost += response.cost
        self.total_tokens += response.usage.get("total_tokens", 0)

        self.logger.debug(
            "成本跟踪更新",
            provider=self.provider.value,
            model=self.model,
            cost=response.cost,
            total_cost=self.total_cost,
            tokens=response.usage.get("total_tokens", 0),
            total_tokens=self.total_tokens
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "avg_cost_per_token": self.total_cost / self.total_tokens if self.total_tokens > 0 else 0,
        }

    def reset_cost_tracking(self) -> None:
        """重置成本跟踪"""
        self.total_cost = 0.0
        self.total_tokens = 0
        self.logger.debug("成本跟踪已重置")


class OpenAIClient(AIClient):
    """OpenAI客户端"""

    def _init_client(self) -> None:
        """初始化OpenAI客户端"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI库未安装，请运行: pip install openai")

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        self.logger.debug(f"OpenAI客户端初始化: {self.model}")

    def chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """OpenAI聊天补全"""
        start_time = time.time()

        try:
            # 准备API参数
            api_messages = [msg.to_dict() for msg in messages]

            api_kwargs = {
                "model": self.model,
                "messages": api_messages,
                "temperature": temperature,
                "timeout": self.timeout,
                **kwargs
            }

            if max_tokens is not None:
                api_kwargs["max_tokens"] = max_tokens

            # 调用API
            response = self.client.chat.completions.create(**api_kwargs)

            # 提取响应内容
            content = response.choices[0].message.content or ""

            # 解析使用情况
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            # 计算成本
            config = config_manager.get_node_model_config("default")
            cost = self.calculate_cost(usage, getattr(config, "cost_per_1k_tokens", None))

            # 创建响应对象
            ai_response = AIResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                usage=usage,
                cost=cost,
                response_time=time.time() - start_time,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "id": response.id,
                }
            )

            # 更新成本跟踪
            self.update_cost_tracking(ai_response)

            self.logger.log_api_call(
                service="openai",
                endpoint="chat.completions",
                success=True,
                duration_seconds=ai_response.response_time,
                model=self.model,
                tokens=usage["total_tokens"],
                cost=cost
            )

            return ai_response

        except openai.RateLimitError as e:
            retry_after = getattr(e, 'retry_after', None)
            raise RateLimitError(
                provider=self.provider.value,
                model=self.model,
                retry_after=retry_after,
                details={"error": str(e)}
            )
        except openai.BadRequestError as e:
            if "maximum context length" in str(e).lower():
                raise TokenLimitError(
                    provider=self.provider.value,
                    model=self.model,
                    max_tokens=4096,  # 默认值，实际应从错误信息中提取
                    requested_tokens=0,  # 实际应从请求中计算
                    details={"error": str(e)}
                )
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=400,
                details={"error": str(e)}
            )
        except openai.APIError as e:
            status_code = getattr(e, 'status_code', None)
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=status_code,
                details={"error": str(e)}
            )
        except Exception as e:
            raise AIError(
                message=f"OpenAI API调用失败: {str(e)}",
                provider=self.provider.value,
                model=self.model,
                details={"error": str(e)},
                cause=e
            )

    async def chat_completion_async(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """异步聊天补全（简化实现，调用同步版本）"""
        # 注意：实际实现应该使用异步客户端
        return self.chat_completion(messages, temperature, max_tokens, **kwargs)

    def stream_chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全（简化实现）"""
        # 注意：实际实现应该返回真正的流式响应
        response = self.chat_completion(messages, temperature, max_tokens, **kwargs)
        # 模拟流式响应：将内容分成几块返回
        chunk_size = 100
        content = response.content
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]


class AzureOpenAIClient(AIClient):
    """Azure OpenAI 客户端"""

    def __init__(
        self,
        provider: AIProvider,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        logger_name: Optional[str] = None,
    ):
        self.api_version = api_version or "2024-12-01-preview"
        super().__init__(provider, model, api_key, base_url, timeout, max_retries, logger_name)

    def _init_client(self) -> None:
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI库未安装，请运行: pip install openai")

        self.client = openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.base_url,
            api_version=self.api_version,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        self.logger.debug(f"Azure OpenAI 客户端初始化: endpoint={self.base_url}, deployment={self.model}")

    def chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        start_time = time.time()

        try:
            api_messages = [msg.to_dict() for msg in messages]

            api_kwargs = {
                "model": self.model,
                "messages": api_messages,
                "temperature": temperature,
                "timeout": self.timeout,
                "stream": True,
                "stream_options": {"include_usage": True},
                **kwargs
            }

            if max_tokens is not None:
                api_kwargs["max_completion_tokens"] = max_tokens

            stream = self.client.chat.completions.create(**api_kwargs)

            content_parts = []
            usage = {}
            finish_reason = None
            response_id = None

            for chunk in stream:
                if chunk.id:
                    response_id = chunk.id
                if chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content_parts.append(delta.content)
                    if chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason

            content = "".join(content_parts)

            if not usage:
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            config = config_manager.get_node_model_config("default")
            cost = self.calculate_cost(usage, getattr(config, "cost_per_1k_tokens", None))

            ai_response = AIResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                usage=usage,
                cost=cost,
                response_time=time.time() - start_time,
                metadata={
                    "finish_reason": finish_reason,
                    "id": response_id,
                }
            )

            self.update_cost_tracking(ai_response)

            self.logger.log_api_call(
                service="azure_openai",
                endpoint="chat.completions",
                success=True,
                duration_seconds=ai_response.response_time,
                model=self.model,
                tokens=usage["total_tokens"],
                cost=cost
            )

            return ai_response

        except openai.RateLimitError as e:
            retry_after = getattr(e, 'retry_after', None)
            raise RateLimitError(
                provider=self.provider.value,
                model=self.model,
                retry_after=retry_after,
                details={"error": str(e)}
            )
        except openai.BadRequestError as e:
            if "maximum context length" in str(e).lower():
                raise TokenLimitError(
                    provider=self.provider.value,
                    model=self.model,
                    max_tokens=4096,
                    requested_tokens=0,
                    details={"error": str(e)}
                )
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=400,
                details={"error": str(e)}
            )
        except openai.APIError as e:
            status_code = getattr(e, 'status_code', None)
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=status_code,
                details={"error": str(e)}
            )
        except Exception as e:
            raise AIError(
                message=f"Azure OpenAI API调用失败: {str(e)}",
                provider=self.provider.value,
                model=self.model,
                details={"error": str(e)},
                cause=e
            )

    async def chat_completion_async(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        return self.chat_completion(messages, temperature, max_tokens, **kwargs)

    def stream_chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        api_messages = [msg.to_dict() for msg in messages]

        api_kwargs = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature,
            "timeout": self.timeout,
            "stream": True,
            **kwargs
        }

        if max_tokens is not None:
            api_kwargs["max_completion_tokens"] = max_tokens

        stream = self.client.chat.completions.create(**api_kwargs)

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(AIClient):
    """Anthropic客户端"""

    def _init_client(self) -> None:
        """初始化Anthropic客户端"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic库未安装，请运行: pip install anthropic")

        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        self.logger.debug(f"Anthropic客户端初始化: {self.model}")

    def chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Anthropic聊天补全"""
        start_time = time.time()

        try:
            # Anthropic API格式与OpenAI不同
            # 需要将消息转换为Anthropic格式
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg.role == AIMessageRole.SYSTEM:
                    system_message = msg.content
                else:
                    conversation_messages.append({
                        "role": msg.role.value,
                        "content": msg.content
                    })

            # 准备API参数
            api_kwargs = {
                "model": self.model,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,  # Anthropic需要max_tokens
                "timeout": self.timeout,
                **kwargs
            }

            if system_message:
                api_kwargs["system"] = system_message

            # 调用API
            response = self.client.messages.create(**api_kwargs)

            # 提取响应内容
            content = ""
            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text

            # 解析使用情况
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            # 计算成本
            config = config_manager.get_node_model_config("default")
            cost = self.calculate_cost(usage, getattr(config, "cost_per_1k_tokens", None))

            # 创建响应对象
            ai_response = AIResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                usage=usage,
                cost=cost,
                response_time=time.time() - start_time,
                metadata={
                    "id": response.id,
                    "stop_reason": response.stop_reason,
                }
            )

            # 更新成本跟踪
            self.update_cost_tracking(ai_response)

            self.logger.log_api_call(
                service="anthropic",
                endpoint="messages.create",
                success=True,
                duration_seconds=ai_response.response_time,
                model=self.model,
                tokens=usage["total_tokens"],
                cost=cost
            )

            return ai_response

        except anthropic.RateLimitError as e:
            retry_after = None
            if hasattr(e, 'response') and e.response.headers.get('retry-after'):
                retry_after = int(e.response.headers['retry-after'])
            raise RateLimitError(
                provider=self.provider.value,
                model=self.model,
                retry_after=retry_after,
                details={"error": str(e)}
            )
        except anthropic.BadRequestError as e:
            if "max_tokens" in str(e).lower():
                raise TokenLimitError(
                    provider=self.provider.value,
                    model=self.model,
                    max_tokens=4096,  # 默认值
                    requested_tokens=max_tokens or 4096,
                    details={"error": str(e)}
                )
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=400,
                details={"error": str(e)}
            )
        except anthropic.APIError as e:
            status_code = getattr(e, 'status_code', None)
            raise APIError(
                message=str(e),
                provider=self.provider.value,
                model=self.model,
                status_code=status_code,
                details={"error": str(e)}
            )
        except Exception as e:
            raise AIError(
                message=f"Anthropic API调用失败: {str(e)}",
                provider=self.provider.value,
                model=self.model,
                details={"error": str(e)},
                cause=e
            )

    async def chat_completion_async(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """异步聊天补全（简化实现）"""
        return self.chat_completion(messages, temperature, max_tokens, **kwargs)

    def stream_chat_completion(
        self,
        messages: List[AIMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全（简化实现）"""
        response = self.chat_completion(messages, temperature, max_tokens, **kwargs)
        chunk_size = 100
        content = response.content
        for i in range(0, len(content), chunk_size):
            yield content[i:i + chunk_size]


class AIClientFactory:
    """AI客户端工厂"""

    @staticmethod
    def create_client(
        provider: Union[str, AIProvider],
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AIClient:
        """
        创建AI客户端

        Args:
            provider: 提供商名称或枚举
            model: 模型名称
            api_key: API密钥（如果为None，从配置获取）
            base_url: API基础URL（如果为None，从配置获取）
            **kwargs: 其他客户端参数

        Returns:
            AI客户端实例
        """
        if isinstance(provider, str):
            provider = AIProvider(provider.lower())

        # 从配置获取API密钥和URL（如果未提供）
        if api_key is None or base_url is None:
            provider_config = config_manager.get_provider_config(provider.value)

            if api_key is None:
                api_key_env_var = provider_config.api_key_env_var
                api_key = getattr(config_manager.project_config, api_key_env_var.lower(), None)

            if base_url is None:
                base_url_env_var = provider_config.base_url_env_var
                base_url = getattr(config_manager.project_config, base_url_env_var.lower(), None)
                if not base_url:
                    base_url = provider_config.default_base_url

        # 根据提供商创建客户端
        if provider == AIProvider.AZURE:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI库未安装")
            provider_config = config_manager.get_provider_config(provider.value)
            api_version = None
            if hasattr(provider_config, 'api_version_env_var') and provider_config.api_version_env_var:
                api_version = getattr(
                    config_manager.project_config,
                    provider_config.api_version_env_var.lower(),
                    provider_config.default_api_version
                )
            return AzureOpenAIClient(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                api_version=api_version,
                **kwargs
            )
        elif provider == AIProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI库未安装")
            return OpenAIClient(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                **kwargs
            )
        elif provider == AIProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic库未安装")
            return AnthropicClient(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                **kwargs
            )
        else:
            raise ValueError(f"不支持的AI提供商: {provider}")

    @staticmethod
    def create_client_from_config(node_name: str) -> AIClient:
        """
        根据节点配置创建AI客户端

        Args:
            node_name: 节点名称（如 "keyword_filter", "title_generator"）

        Returns:
            AI客户端实例
        """
        # 获取节点配置
        model_config = config_manager.get_node_model_config(node_name)

        # 创建客户端
        return AIClientFactory.create_client(
            provider=model_config.provider,
            model=model_config.model,
            timeout=getattr(model_config, "timeout", 30),
            max_retries=getattr(model_config, "max_retries", 3),
        )


# 全局AI客户端管理器
class AIClientManager:
    """AI客户端管理器"""

    def __init__(self):
        self.clients: Dict[str, AIClient] = {}
        self.logger = get_logger("ai_client_manager")
        self.factory = AIClientFactory()

    def get_client(
        self,
        node_name: str,
        use_fallback: bool = False
    ) -> AIClient:
        """
        获取或创建AI客户端

        Args:
            node_name: 节点名称
            use_fallback: 是否使用备用模型

        Returns:
            AI客户端实例
        """
        client_key = f"{node_name}_fallback" if use_fallback else node_name

        if client_key not in self.clients:
            if use_fallback:
                # 获取备用模型配置
                fallback_config = config_manager.get_fallback_model_config(node_name)
                if not fallback_config:
                    self.logger.error(
                        f"节点 '{node_name}' 未配置备用模型。"
                        f"主模型调用失败时将使用内置默认内容。"
                        f"请检查 Azure OpenAI / OpenAI 配置是否正确。"
                    )
                    raise ValueError(
                        f"节点 '{node_name}' 没有备用模型配置，"
                        f"且主模型调用失败。请检查 API 密钥和 Endpoint 配置。"
                    )

                client = self.factory.create_client(
                    provider=fallback_config.provider,
                    model=fallback_config.model,
                    timeout=getattr(fallback_config, "timeout", 30),
                    max_retries=getattr(fallback_config, "max_retries", 3),
                )
            else:
                # 获取主模型配置
                client = self.factory.create_client_from_config(node_name)

            self.clients[client_key] = client
            self.logger.debug(f"创建AI客户端: {client_key}")

        return self.clients[client_key]

    def close_all_clients(self) -> None:
        """关闭所有客户端"""
        self.clients.clear()
        self.logger.debug("所有AI客户端已关闭")


# 全局实例
ai_client_manager = AIClientManager()


# 便捷函数
def get_ai_client(node_name: str, use_fallback: bool = False) -> AIClient:
    """获取AI客户端便捷函数"""
    return ai_client_manager.get_client(node_name, use_fallback)


def create_message(role: AIMessageRole, content: str) -> AIMessage:
    """创建消息便捷函数"""
    return AIMessage(role=role, content=content)


def create_system_message(content: str) -> AIMessage:
    """创建系统消息"""
    return create_message(AIMessageRole.SYSTEM, content)


def create_user_message(content: str) -> AIMessage:
    """创建用户消息"""
    return create_message(AIMessageRole.USER, content)


def create_assistant_message(content: str) -> AIMessage:
    """创建助手消息"""
    return create_message(AIMessageRole.ASSISTANT, content)


__all__ = [
    # 枚举
    "AIProvider",
    "AIMessageRole",

    # 数据类
    "AIMessage",
    "AIResponse",

    # 客户端类
    "AIClient",
    "OpenAIClient",
    "AzureOpenAIClient",
    "AnthropicClient",

    # 工厂和管理器
    "AIClientFactory",
    "AIClientManager",
    "ai_client_manager",

    # 便捷函数
    "get_ai_client",
    "create_message",
    "create_system_message",
    "create_user_message",
    "create_assistant_message",
]