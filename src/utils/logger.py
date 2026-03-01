"""
统一日志系统
基于loguru库，提供统一的日志接口
支持文件和控制台输出，支持结构化日志
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from loguru import logger as loguru_logger

# 导入项目配置
try:
    from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, DEBUG
except ImportError:
    # 默认配置，用于测试
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = Path("logs/workflow.log")
    DEBUG = False


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str = "seo-workflow"):
        self.name = name
        self._logger = loguru_logger
        self._setup_logging()

    def _setup_logging(self) -> None:
        """配置loguru日志系统"""

        # 移除默认的处理器
        self._logger.remove()

        # 控制台输出配置
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        self._logger.add(
            sys.stdout,
            format=console_format,
            level=LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=DEBUG
        )

        # 文件输出配置
        if LOG_FILE:
            log_file_path = Path(LOG_FILE)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            )

            self._logger.add(
                str(log_file_path),
                format=file_format,
                level=LOG_LEVEL,
                rotation="10 MB",  # 日志文件轮转：10MB
                retention="30 days",  # 保留30天
                compression="zip",  # 压缩归档
                backtrace=True,
                diagnose=DEBUG
            )

    def _format_structured_data(self, data: Dict[str, Any]) -> str:
        """格式化结构化数据为JSON字符串"""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(data)

    def debug(self, message: str, **kwargs) -> None:
        """记录调试日志"""
        if kwargs:
            structured_message = f"{message} | {self._format_structured_data(kwargs)}"
            self._logger.bind(name=self.name).debug(structured_message)
        else:
            self._logger.bind(name=self.name).debug(message)

    def info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        if kwargs:
            structured_message = f"{message} | {self._format_structured_data(kwargs)}"
            self._logger.bind(name=self.name).info(structured_message)
        else:
            self._logger.bind(name=self.name).info(message)

    def warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        if kwargs:
            structured_message = f"{message} | {self._format_structured_data(kwargs)}"
            self._logger.bind(name=self.name).warning(structured_message)
        else:
            self._logger.bind(name=self.name).warning(message)

    def error(self, message: str, **kwargs) -> None:
        """记录错误日志"""
        if kwargs:
            structured_message = f"{message} | {self._format_structured_data(kwargs)}"
            self._logger.bind(name=self.name).error(structured_message)
        else:
            self._logger.bind(name=self.name).error(message)

    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误日志"""
        if kwargs:
            structured_message = f"{message} | {self._format_structured_data(kwargs)}"
            self._logger.bind(name=self.name).critical(structured_message)
        else:
            self._logger.bind(name=self.name).critical(message)

    def exception(self, message: str, exc: Exception, **kwargs) -> None:
        """记录异常日志"""
        structured_data = {"exception": str(exc), "exception_type": exc.__class__.__name__}
        structured_data.update(kwargs)

        structured_message = f"{message} | {self._format_structured_data(structured_data)}"
        self._logger.bind(name=self.name).exception(structured_message)

    def log_workflow_start(self, workflow_id: str, total_nodes: int) -> None:
        """记录工作流开始"""
        self.info(
            "工作流开始执行",
            workflow_id=workflow_id,
            total_nodes=total_nodes,
            timestamp=datetime.now().isoformat()
        )

    def log_workflow_end(self, workflow_id: str, success: bool, duration_seconds: float) -> None:
        """记录工作流结束"""
        self.info(
            "工作流执行完成",
            workflow_id=workflow_id,
            success=success,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat()
        )

    def log_node_start(self, node_id: str, node_type: str, input_data: Optional[Dict] = None) -> None:
        """记录节点开始执行"""
        log_data = {
            "node_id": node_id,
            "node_type": node_type,
            "timestamp": datetime.now().isoformat()
        }
        if input_data:
            # 只记录输入数据的元信息，避免记录敏感数据
            log_data["input_summary"] = {
                "data_type": type(input_data).__name__,
                "size": len(str(input_data)) if hasattr(input_data, '__len__') else None
            }

        self.info(f"节点开始执行: {node_id}", **log_data)

    def log_node_end(self, node_id: str, success: bool, duration_seconds: float,
                    output_summary: Optional[Dict] = None) -> None:
        """记录节点执行完成"""
        log_data = {
            "node_id": node_id,
            "success": success,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
        if output_summary:
            log_data["output_summary"] = output_summary

        self.info(f"节点执行完成: {node_id}", **log_data)

    def log_api_call(self, service: str, endpoint: str, success: bool,
                    duration_seconds: float, **kwargs) -> None:
        """记录API调用"""
        log_data = {
            "service": service,
            "endpoint": endpoint,
            "success": success,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
        log_data.update(kwargs)

        self.info(f"API调用: {service}/{endpoint}", **log_data)

    def log_cost(self, service: str, cost_usd: float, tokens_used: int,
                operation: str) -> None:
        """记录成本信息"""
        self.info(
            f"成本记录: {service}",
            service=service,
            cost_usd=cost_usd,
            tokens_used=tokens_used,
            operation=operation,
            timestamp=datetime.now().isoformat()
        )


# 创建全局日志实例
logger = StructuredLogger()

# 提供简化的函数接口
def get_logger(name: str = "seo-workflow") -> StructuredLogger:
    """获取指定名称的日志记录器"""
    return StructuredLogger(name)


# 导出常用函数
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception

__all__ = [
    "logger",
    "get_logger",
    "StructuredLogger",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
]