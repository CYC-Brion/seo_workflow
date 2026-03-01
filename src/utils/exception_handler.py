"""
异常处理框架
提供统一的异常类和异常处理机制
"""

import traceback
from typing import Any, Dict, Optional, Type
from enum import Enum

from .logger import get_logger

logger = get_logger("exception_handler")


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"          # 可忽略的错误，不影响主要功能
    MEDIUM = "medium"    # 需要注意的错误，可能影响部分功能
    HIGH = "high"        # 严重错误，影响核心功能
    CRITICAL = "critical"  # 致命错误，系统无法继续运行


class WorkflowException(Exception):
    """工作流基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        self.stack_trace = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
            "stack_trace": self.stack_trace,
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        cause_str = f", caused by: {self.cause}" if self.cause else ""
        details_str = f", details: {self.details}" if self.details else ""
        return f"[{self.error_code}] {self.message}{cause_str}{details_str}"


# 配置相关异常
class ConfigError(WorkflowException):
    """配置错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            severity=ErrorSeverity.HIGH,
            details=details
        )


class MissingConfigError(ConfigError):
    """配置缺失错误"""
    def __init__(self, config_key: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"缺少必要配置: {config_key}",
            details={"config_key": config_key, **(details or {})}
        )


class InvalidConfigError(ConfigError):
    """配置无效错误"""
    def __init__(self, config_key: str, config_value: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"配置值无效: {config_key}={config_value}",
            details={"config_key": config_key, "config_value": config_value, **(details or {})}
        )


# 文件相关异常
class FileError(WorkflowException):
    """文件错误"""
    def __init__(self, message: str, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="FILE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            details={"file_path": file_path, **(details or {})}
        )


class FileNotFoundError(FileError):
    """文件未找到错误"""
    def __init__(self, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"文件未找到: {file_path}",
            file_path=file_path,
            details=details
        )


class FilePermissionError(FileError):
    """文件权限错误"""
    def __init__(self, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"文件权限错误: {file_path}",
            file_path=file_path,
            details=details
        )


class FileFormatError(FileError):
    """文件格式错误"""
    def __init__(self, file_path: str, expected_format: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"文件格式错误: {file_path}，期望格式: {expected_format}",
            file_path=file_path,
            details={"expected_format": expected_format, **(details or {})}
        )


# AI相关异常
class AIError(WorkflowException):
    """AI服务错误"""
    def __init__(
        self,
        message: str,
        provider: str,
        model: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_ERROR",
            severity=ErrorSeverity.HIGH,
            details={"provider": provider, "model": model, **(details or {})},
            cause=cause
        )


class APIError(AIError):
    """API调用错误"""
    def __init__(
        self,
        message: str,
        provider: str,
        model: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code

        super().__init__(
            message=f"API调用失败: {message}",
            provider=provider,
            model=model,
            details=details,
            cause=cause
        )


class RateLimitError(APIError):
    """速率限制错误"""
    def __init__(
        self,
        provider: str,
        model: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message="API速率限制",
            provider=provider,
            model=model,
            details=details
        )


class TokenLimitError(AIError):
    """Token限制错误"""
    def __init__(
        self,
        provider: str,
        model: str,
        max_tokens: int,
        requested_tokens: int,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            "max_tokens": max_tokens,
            "requested_tokens": requested_tokens,
        })

        super().__init__(
            message=f"Token数量超过限制: 请求{requested_tokens}，最大{max_tokens}",
            provider=provider,
            model=model,
            details=details
        )


class CostLimitError(AIError):
    """成本限制错误"""
    def __init__(
        self,
        provider: str,
        model: str,
        max_cost: float,
        current_cost: float,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            "max_cost": max_cost,
            "current_cost": current_cost,
        })

        super().__init__(
            message=f"成本超过限制: 当前${current_cost:.4f}，最大${max_cost:.2f}",
            provider=provider,
            model=model,
            details=details
        )


# 工作流相关异常
class WorkflowError(WorkflowException):
    """工作流错误"""
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="WORKFLOW_ERROR",
            severity=ErrorSeverity.HIGH,
            details={"workflow_id": workflow_id, "node_id": node_id, **(details or {})}
        )


class NodeExecutionError(WorkflowError):
    """节点执行错误"""
    def __init__(
        self,
        message: str,
        node_id: str,
        node_type: str,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=f"节点执行失败 [{node_type}:{node_id}]: {message}",
            workflow_id=workflow_id,
            node_id=node_id,
            details={"node_type": node_type, **(details or {})},
            cause=cause
        )


class WorkflowValidationError(WorkflowError):
    """工作流验证错误"""
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"工作流验证失败: {message}",
            workflow_id=workflow_id,
            details=details
        )


# WordPress相关异常
class WordPressError(WorkflowException):
    """WordPress错误"""
    def __init__(
        self,
        message: str,
        url: str,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            error_code="WORDPRESS_ERROR",
            severity=ErrorSeverity.HIGH,
            details={"url": url, "endpoint": endpoint, **(details or {})},
            cause=cause
        )


class WordPressAuthError(WordPressError):
    """WordPress认证错误"""
    def __init__(
        self,
        url: str,
        username: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message="WordPress认证失败",
            url=url,
            details={"username": username, **(details or {})}
        )


class WordPressPublishError(WordPressError):
    """WordPress发布错误"""
    def __init__(
        self,
        url: str,
        post_title: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=f"文章发布失败: {post_title}",
            url=url,
            details={"post_title": post_title, **(details or {})},
            cause=cause
        )


# 异常处理器
class ExceptionHandler:
    """异常处理器"""

    def __init__(self, logger_instance=None):
        self.logger = logger_instance or logger

    def handle_exception(
        self,
        exc: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True
    ) -> Optional[Dict[str, Any]]:
        """处理异常

        Args:
            exc: 异常对象
            context: 上下文信息
            reraise: 是否重新抛出异常

        Returns:
            异常信息字典，如果不重新抛出异常
        """
        context = context or {}

        # 记录异常
        self._log_exception(exc, context)

        # 转换异常信息
        error_info = self._extract_error_info(exc, context)

        # 根据配置决定是否重新抛出
        if reraise:
            if isinstance(exc, WorkflowException):
                raise exc
            else:
                # 转换为工作流异常
                workflow_exc = WorkflowException(
                    message=str(exc),
                    error_code="UNHANDLED_ERROR",
                    severity=ErrorSeverity.CRITICAL,
                    details={"original_exception": exc.__class__.__name__, **context},
                    cause=exc
                )
                raise workflow_exc
        else:
            return error_info

    def _log_exception(self, exc: Exception, context: Dict[str, Any]) -> None:
        """记录异常日志"""
        if isinstance(exc, WorkflowException):
            # 工作流异常，记录详细信息
            error_dict = exc.to_dict()
            error_dict.update({"context": context})

            # 从error_dict中移除message字段，避免与日志方法的第一个参数冲突
            error_dict.pop("message", None)

            if exc.severity == ErrorSeverity.CRITICAL:
                self.logger.critical(f"严重异常: {exc.message}", **error_dict)
            elif exc.severity == ErrorSeverity.HIGH:
                self.logger.error(f"错误: {exc.message}", **error_dict)
            elif exc.severity == ErrorSeverity.MEDIUM:
                self.logger.warning(f"警告: {exc.message}", **error_dict)
            else:
                self.logger.debug(f"低级别异常: {exc.message}", **error_dict)
        else:
            # 其他异常
            self.logger.error(
                f"未处理异常: {exc.__class__.__name__}: {str(exc)}",
                exception_type=exc.__class__.__name__,
                exception_message=str(exc),
                stack_trace=traceback.format_exc(),
                context=context
            )

    def _extract_error_info(self, exc: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取异常信息"""
        if isinstance(exc, WorkflowException):
            error_info = exc.to_dict()
        else:
            error_info = {
                "error_code": "UNHANDLED_ERROR",
                "message": str(exc),
                "exception_type": exc.__class__.__name__,
                "severity": ErrorSeverity.CRITICAL.value,
                "stack_trace": traceback.format_exc(),
            }

        error_info.update({"context": context})
        return error_info

    def safe_execute(
        self,
        func,
        *args,
        error_message: str = "执行失败",
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True,
        **kwargs
    ) -> Any:
        """安全执行函数，自动处理异常

        Args:
            func: 要执行的函数
            error_message: 错误消息
            context: 上下文信息
            reraise: 是否重新抛出异常
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果，如果失败且reraise=False则返回None
        """
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            context = context or {}
            context.update({
                "function": func.__name__,
                "module": func.__module__ if hasattr(func, '__module__') else 'unknown'
            })

            error_info = self.handle_exception(
                exc,
                context=context,
                reraise=reraise
            )

            if not reraise:
                return None


# 全局异常处理器实例
exception_handler = ExceptionHandler()

def get_exception_handler() -> ExceptionHandler:
    """获取全局异常处理器"""
    return exception_handler


__all__ = [
    # 异常类
    "WorkflowException",
    "ConfigError",
    "MissingConfigError",
    "InvalidConfigError",
    "FileError",
    "FileNotFoundError",
    "FilePermissionError",
    "FileFormatError",
    "AIError",
    "APIError",
    "RateLimitError",
    "TokenLimitError",
    "CostLimitError",
    "WorkflowError",
    "NodeExecutionError",
    "WorkflowValidationError",
    "WordPressError",
    "WordPressAuthError",
    "WordPressPublishError",

    # 枚举
    "ErrorSeverity",

    # 处理器
    "ExceptionHandler",
    "exception_handler",
    "get_exception_handler",
]