"""
工作流节点抽象基类
定义所有工作流节点的通用接口和行为
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

from src.utils import (
    get_logger,
    exception_handler,
    WorkflowException,
    NodeExecutionError,
    ErrorSeverity,
)


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 执行成功
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 跳过执行


@dataclass
class NodeResult:
    """节点执行结果"""
    node_id: str
    node_type: str
    status: NodeStatus
    output_data: Optional[Any] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0  # 执行时间（秒）
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
            "has_output": self.output_data is not None,
            "has_error": self.error_message is not None,
        }


class BaseNode(ABC):
    """工作流节点抽象基类"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        logger_name: Optional[str] = None
    ):
        """
        初始化节点

        Args:
            node_id: 节点唯一标识符
            node_type: 节点类型
            config: 节点配置
            logger_name: 日志记录器名称
        """
        self.node_id = node_id
        self.node_type = node_type
        self.config = config or {}
        self.logger = get_logger(logger_name or f"node.{node_type}.{node_id}")
        self.exception_handler = exception_handler

        self.status = NodeStatus.PENDING
        self.result: Optional[NodeResult] = None
        self.input_data: Optional[Any] = None
        self.output_data: Optional[Any] = None

        # 执行统计
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.execution_time: float = 0.0

        # 节点依赖
        self.dependencies: List[str] = []
        self.dependent_nodes: List[str] = []

    def add_dependency(self, node_id: str) -> None:
        """添加依赖节点"""
        if node_id not in self.dependencies:
            self.dependencies.append(node_id)

    def add_dependent_node(self, node_id: str) -> None:
        """添加依赖此节点的节点"""
        if node_id not in self.dependent_nodes:
            self.dependent_nodes.append(node_id)

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据

        子类可以重写此方法实现具体的输入验证逻辑
        默认实现只检查输入是否为None

        Args:
            input_data: 输入数据

        Returns:
            是否验证通过
        """
        if input_data is None:
            self.logger.warning("输入数据为None")
            return False
        return True

    def validate_output(self, output_data: Any) -> bool:
        """验证输出数据

        子类可以重写此方法实现具体的输出验证逻辑
        默认实现只检查输出是否为None

        Args:
            output_data: 输出数据

        Returns:
            是否验证通过
        """
        if output_data is None:
            self.logger.warning("输出数据为None")
            return False
        return True

    def pre_execute(self, input_data: Any) -> Optional[Any]:
        """执行前处理

        子类可以重写此方法实现执行前的预处理
        默认实现返回输入数据

        Args:
            input_data: 输入数据

        Returns:
            处理后的输入数据
        """
        self.logger.debug("执行前处理", input_summary=self._summarize_data(input_data))
        return input_data

    @abstractmethod
    def execute_impl(self, input_data: Any) -> Any:
        """具体执行逻辑

        子类必须实现此方法

        Args:
            input_data: 输入数据

        Returns:
            输出数据

        Raises:
            Exception: 执行过程中发生的异常
        """
        pass

    def post_execute(self, output_data: Any) -> Optional[Any]:
        """执行后处理

        子类可以重写此方法实现执行后的后处理
        默认实现返回输出数据

        Args:
            output_data: 输出数据

        Returns:
            处理后的输出数据
        """
        self.logger.debug("执行后处理", output_summary=self._summarize_data(output_data))
        return output_data

    def execute(self, input_data: Any) -> NodeResult:
        """执行节点

        Args:
            input_data: 输入数据

        Returns:
            节点执行结果
        """
        self.input_data = input_data
        self.status = NodeStatus.RUNNING
        self.start_time = datetime.now()

        self.logger.log_node_start(
            node_id=self.node_id,
            node_type=self.node_type,
            input_data=input_data
        )

        try:
            # 验证输入
            if not self.validate_input(input_data):
                raise NodeExecutionError(
                    message="输入数据验证失败",
                    node_id=self.node_id,
                    node_type=self.node_type,
                    details={"input_data": self._summarize_data(input_data)}
                )

            # 执行前处理
            processed_input = self.pre_execute(input_data)

            # 执行具体逻辑
            raw_output = self.execute_impl(processed_input)

            # 执行后处理
            processed_output = self.post_execute(raw_output)

            # 验证输出
            if not self.validate_output(processed_output):
                raise NodeExecutionError(
                    message="输出数据验证失败",
                    node_id=self.node_id,
                    node_type=self.node_type,
                    details={"output_data": self._summarize_data(processed_output)}
                )

            self.output_data = processed_output
            self.status = NodeStatus.COMPLETED

            self.logger.log_node_end(
                node_id=self.node_id,
                success=True,
                duration_seconds=self.execution_time,
                output_summary=self._summarize_data(processed_output)
            )

            return self._create_result(
                status=NodeStatus.COMPLETED,
                output_data=processed_output
            )

        except Exception as exc:
            self.status = NodeStatus.FAILED
            self.end_time = datetime.now()
            self.execution_time = (self.end_time - self.start_time).total_seconds()

            # 处理异常
            error_info = self.exception_handler.handle_exception(
                exc,
                context={
                    "node_id": self.node_id,
                    "node_type": self.node_type,
                    "input_data": self._summarize_data(input_data)
                },
                reraise=False
            )

            self.logger.log_node_end(
                node_id=self.node_id,
                success=False,
                duration_seconds=self.execution_time,
                output_summary={"error": error_info}
            )

            return self._create_result(
                status=NodeStatus.FAILED,
                error_message=str(exc),
                error_details=error_info
            )

        finally:
            if self.end_time is None:
                self.end_time = datetime.now()
                self.execution_time = (self.end_time - self.start_time).total_seconds()

    def skip(self, reason: str = "") -> NodeResult:
        """跳过节点执行

        Args:
            reason: 跳过原因

        Returns:
            跳过结果
        """
        self.status = NodeStatus.SKIPPED
        self.start_time = datetime.now()
        self.end_time = self.start_time

        self.logger.info(f"跳过节点: {self.node_id}", reason=reason)

        return self._create_result(
            status=NodeStatus.SKIPPED,
            metadata={"skip_reason": reason}
        )

    def _create_result(
        self,
        status: NodeStatus,
        output_data: Optional[Any] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """创建节点结果"""
        result = NodeResult(
            node_id=self.node_id,
            node_type=self.node_type,
            status=status,
            output_data=output_data,
            error_message=error_message,
            error_details=error_details,
            execution_time=self.execution_time,
            start_time=self.start_time,
            end_time=self.end_time,
            metadata=metadata or {}
        )

        self.result = result
        return result

    def _summarize_data(self, data: Any) -> Dict[str, Any]:
        """总结数据，用于日志记录

        避免记录过大的数据，只记录元信息
        """
        if data is None:
            return {"type": "None", "summary": "None"}

        data_type = type(data).__name__

        if isinstance(data, (str, int, float, bool)):
            return {"type": data_type, "value": data}

        elif isinstance(data, (list, tuple)):
            return {
                "type": data_type,
                "length": len(data),
                "first_few": data[:3] if len(data) > 0 else [],
            }

        elif isinstance(data, dict):
            return {
                "type": data_type,
                "keys": list(data.keys()),
                "size": len(data),
            }

        else:
            return {
                "type": data_type,
                "str_repr": str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
            }

    def get_status(self) -> NodeStatus:
        """获取节点状态"""
        return self.status

    def get_result(self) -> Optional[NodeResult]:
        """获取节点结果"""
        return self.result

    def get_execution_time(self) -> float:
        """获取执行时间"""
        return self.execution_time

    def reset(self) -> None:
        """重置节点状态"""
        self.status = NodeStatus.PENDING
        self.result = None
        self.input_data = None
        self.output_data = None
        self.start_time = None
        self.end_time = None
        self.execution_time = 0.0

        self.logger.debug(f"节点已重置: {self.node_id}")

    def __str__(self) -> str:
        return f"Node(id={self.node_id}, type={self.node_type}, status={self.status.value})"

    def __repr__(self) -> str:
        return self.__str__()


class DataProcessingNode(BaseNode):
    """数据处理节点基类

    用于处理结构化数据的节点
    """

    def __init__(
        self,
        node_id: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        logger_name: Optional[str] = None
    ):
        super().__init__(node_id, node_type, config, logger_name)
        self.data_schema: Optional[Dict[str, Any]] = None

    def set_data_schema(self, schema: Dict[str, Any]) -> None:
        """设置数据模式"""
        self.data_schema = schema
        self.logger.debug(f"设置数据模式: {schema}")

    def validate_with_schema(self, data: Any) -> bool:
        """使用数据模式验证数据"""
        if self.data_schema is None:
            return True

        # 简单的模式验证实现
        # 子类可以重写此方法实现更复杂的验证
        if isinstance(data, dict):
            required_fields = self.data_schema.get("required", [])
            for field in required_fields:
                if field not in data:
                    self.logger.warning(f"缺少必填字段: {field}")
                    return False
        return True

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据（包含模式验证）"""
        if not super().validate_input(input_data):
            return False

        return self.validate_with_schema(input_data)


class AINode(BaseNode):
    """AI节点基类

    用于调用AI服务的节点
    """

    def __init__(
        self,
        node_id: str,
        node_type: str,
        config: Optional[Dict[str, Any]] = None,
        logger_name: Optional[str] = None
    ):
        super().__init__(node_id, node_type, config, logger_name)
        self.ai_client = None
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 5)

    def set_ai_client(self, ai_client) -> None:
        """设置AI客户端"""
        self.ai_client = ai_client
        self.logger.debug(f"设置AI客户端: {ai_client.__class__.__name__}")

    def call_ai_with_retry(self, func, *args, **kwargs) -> Any:
        """带重试机制的AI调用"""
        if self.ai_client is None:
            raise ValueError("AI客户端未设置")

        last_exception = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"重试AI调用，第{attempt + 1}次尝试")
                    time.sleep(self.retry_delay)

                return func(*args, **kwargs)

            except Exception as exc:
                last_exception = exc
                self.logger.warning(
                    f"AI调用失败，第{attempt + 1}次尝试",
                    exception=str(exc),
                    attempt=attempt + 1
                )

        # 所有重试都失败
        raise last_exception


__all__ = [
    "NodeStatus",
    "NodeResult",
    "BaseNode",
    "DataProcessingNode",
    "AINode",
]