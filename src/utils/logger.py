"""Project logging helpers built on top of loguru."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger as loguru_logger

try:
    from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, DEBUG
except ImportError:
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # 即使 config.settings 不可用也要锚定到项目根，否则日志会落到启动目录下的 logs/
    LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "workflow.log"
    DEBUG = False


class StructuredLogger:
    """Small wrapper that keeps the existing project logger API stable."""

    def __init__(self, name: str = "seo-workflow") -> None:
        self.name = name
        self._logger = loguru_logger
        self._setup_logging()

    def _setup_logging(self) -> None:
        self._logger.remove()

        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[logger_name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        self._logger.add(
            sys.stdout,
            format=console_format,
            level=LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=DEBUG,
        )

        if not LOG_FILE:
            return

        log_file_path = Path(LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{extra[logger_name]}:{function}:{line} | "
            "{message}"
        )

        try:
            self._logger.add(
                str(log_file_path),
                format=file_format,
                level=LOG_LEVEL,
                rotation="10 MB",
                retention="30 days",
                compression="zip",
                backtrace=True,
                diagnose=DEBUG,
            )
        except OSError as exc:
            self._logger.bind(logger_name=self.name).warning(
                f"Failed to initialize file logging at {log_file_path}: {exc}"
            )

    def _format_structured_data(self, data: Dict[str, Any]) -> str:
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(data)

    def _bind(self):
        return self._logger.bind(logger_name=self.name)

    def debug(self, message: str, **kwargs) -> None:
        if kwargs:
            self._bind().debug(f"{message} | {self._format_structured_data(kwargs)}")
        else:
            self._bind().debug(message)

    def info(self, message: str, **kwargs) -> None:
        if kwargs:
            self._bind().info(f"{message} | {self._format_structured_data(kwargs)}")
        else:
            self._bind().info(message)

    def warning(self, message: str, **kwargs) -> None:
        if kwargs:
            self._bind().warning(f"{message} | {self._format_structured_data(kwargs)}")
        else:
            self._bind().warning(message)

    def error(self, message: str, **kwargs) -> None:
        if kwargs:
            self._bind().error(f"{message} | {self._format_structured_data(kwargs)}")
        else:
            self._bind().error(message)

    def critical(self, message: str, **kwargs) -> None:
        if kwargs:
            self._bind().critical(f"{message} | {self._format_structured_data(kwargs)}")
        else:
            self._bind().critical(message)

    def exception(self, message: str, exc: Exception, **kwargs) -> None:
        structured_data = {
            "exception": str(exc),
            "exception_type": exc.__class__.__name__,
        }
        structured_data.update(kwargs)
        self._bind().exception(
            f"{message} | {self._format_structured_data(structured_data)}"
        )

    def log_workflow_start(self, workflow_id: str, total_nodes: int) -> None:
        self.info(
            "Workflow execution started",
            workflow_id=workflow_id,
            total_nodes=total_nodes,
            timestamp=datetime.now().isoformat(),
        )

    def log_workflow_end(
        self, workflow_id: str, success: bool, duration_seconds: float
    ) -> None:
        self.info(
            "Workflow execution finished",
            workflow_id=workflow_id,
            success=success,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
        )

    def log_node_start(
        self, node_id: str, node_type: str, input_data: Optional[Dict] = None
    ) -> None:
        log_data = {
            "node_id": node_id,
            "node_type": node_type,
            "timestamp": datetime.now().isoformat(),
        }
        if input_data:
            log_data["input_summary"] = {
                "data_type": type(input_data).__name__,
                "size": len(str(input_data)) if hasattr(input_data, "__len__") else None,
            }
        self.info(f"Node execution started: {node_id}", **log_data)

    def log_node_end(
        self,
        node_id: str,
        success: bool,
        duration_seconds: float,
        output_summary: Optional[Dict] = None,
    ) -> None:
        log_data = {
            "node_id": node_id,
            "success": success,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat(),
        }
        if output_summary:
            log_data["output_summary"] = output_summary
        self.info(f"Node execution finished: {node_id}", **log_data)

    def log_api_call(
        self,
        service: str,
        endpoint: str,
        success: bool,
        duration_seconds: float,
        **kwargs,
    ) -> None:
        log_data = {
            "service": service,
            "endpoint": endpoint,
            "success": success,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat(),
        }
        log_data.update(kwargs)
        self.info(f"API call: {service}/{endpoint}", **log_data)

    def log_cost(
        self, service: str, cost_usd: float, tokens_used: int, operation: str
    ) -> None:
        self.info(
            f"Cost record: {service}",
            service=service,
            cost_usd=cost_usd,
            tokens_used=tokens_used,
            operation=operation,
            timestamp=datetime.now().isoformat(),
        )


logger = StructuredLogger()


def get_logger(name: str = "seo-workflow") -> StructuredLogger:
    return StructuredLogger(name)


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
