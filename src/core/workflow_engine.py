"""
工作流引擎
负责工作流的编排、执行和监控
"""

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field

from src.utils import (
    get_logger,
    exception_handler,
    WorkflowException,
    WorkflowError,
    NodeExecutionError,
    ErrorSeverity,
)

from .base_node import BaseNode, NodeStatus, NodeResult


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 执行成功
    FAILED = "failed"        # 执行失败
    PAUSED = "paused"        # 已暂停
    CANCELLED = "cancelled"  # 已取消


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    final_output: Optional[Any] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "skipped_nodes": self.skipped_nodes,
            "success_rate": self.completed_nodes / self.total_nodes if self.total_nodes > 0 else 0,
            "has_final_output": self.final_output is not None,
            "has_error": self.error_message is not None,
            "metadata": self.metadata,
        }


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self, workflow_name: str = "default-workflow"):
        """
        初始化工作流引擎

        Args:
            workflow_name: 工作流名称
        """
        self.workflow_id = str(uuid.uuid4())[:8]
        self.workflow_name = workflow_name
        self.logger = get_logger(f"workflow.{workflow_name}.{self.workflow_id}")
        self.exception_handler = exception_handler

        # 节点管理
        self.nodes: Dict[str, BaseNode] = {}
        self.node_dependencies: Dict[str, List[str]] = {}  # 节点ID -> 依赖的节点ID列表
        self.node_execution_order: List[str] = []  # 节点执行顺序

        # 工作流状态
        self.status = WorkflowStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.execution_time: float = 0.0

        # 执行结果
        self.results: Dict[str, NodeResult] = {}
        self.final_output: Optional[Any] = None

        # 回调函数
        self.on_node_start_callbacks: List[Callable] = []
        self.on_node_complete_callbacks: List[Callable] = []
        self.on_workflow_complete_callbacks: List[Callable] = []

        self.logger.info(f"工作流引擎初始化: {workflow_name} (ID: {self.workflow_id})")

    def add_node(self, node: BaseNode, dependencies: Optional[List[str]] = None) -> None:
        """添加节点到工作流

        Args:
            node: 节点实例
            dependencies: 依赖的节点ID列表
        """
        if node.node_id in self.nodes:
            raise WorkflowError(
                message=f"节点ID已存在: {node.node_id}",
                workflow_id=self.workflow_id,
                details={"existing_nodes": list(self.nodes.keys())}
            )

        self.nodes[node.node_id] = node
        self.node_dependencies[node.node_id] = dependencies or []

        # 更新依赖关系
        for dep_id in self.node_dependencies[node.node_id]:
            if dep_id in self.nodes:
                self.nodes[dep_id].add_dependent_node(node.node_id)
            else:
                self.logger.warning(f"依赖节点不存在: {dep_id}，将在后续添加")

        self.logger.info(
            f"添加节点: {node.node_id} ({node.node_type})",
            dependencies=self.node_dependencies[node.node_id]
        )

    def remove_node(self, node_id: str) -> None:
        """从工作流中移除节点"""
        if node_id not in self.nodes:
            raise WorkflowError(
                message=f"节点不存在: {node_id}",
                workflow_id=self.workflow_id
            )

        # 移除依赖关系
        for dep_id in self.node_dependencies[node_id]:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependent_nodes.remove(node_id)

        # 更新依赖此节点的节点
        for other_id, deps in self.node_dependencies.items():
            if node_id in deps:
                deps.remove(node_id)

        # 移除节点
        del self.nodes[node_id]
        del self.node_dependencies[node_id]

        self.logger.info(f"移除节点: {node_id}")

    def validate_workflow(self) -> Tuple[bool, List[str]]:
        """验证工作流

        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []

        # 检查节点是否存在
        for node_id, deps in self.node_dependencies.items():
            if node_id not in self.nodes:
                errors.append(f"节点配置中存在但未注册的节点: {node_id}")
                continue

            for dep_id in deps:
                if dep_id not in self.nodes:
                    errors.append(f"节点 {node_id} 的依赖节点不存在: {dep_id}")

        # 检查循环依赖
        if self._has_cycle():
            errors.append("工作流存在循环依赖")

        # 检查孤立节点（没有依赖也没有被依赖）
        all_deps = set()
        for deps in self.node_dependencies.values():
            all_deps.update(deps)

        for node_id in self.nodes.keys():
            if (node_id not in all_deps and
                not any(node_id in deps for deps in self.node_dependencies.values())):
                self.logger.warning(f"孤立节点: {node_id}")

        return len(errors) == 0, errors

    def _has_cycle(self) -> bool:
        """检查是否存在循环依赖"""
        visited = set()
        recursion_stack = set()

        def dfs(node_id: str) -> bool:
            if node_id in recursion_stack:
                return True
            if node_id in visited:
                return False

            visited.add(node_id)
            recursion_stack.add(node_id)

            for dep_id in self.node_dependencies.get(node_id, []):
                if dep_id in self.nodes and dfs(dep_id):
                    return True

            recursion_stack.remove(node_id)
            return False

        for node_id in self.nodes.keys():
            if dfs(node_id):
                return True

        return False

    def _calculate_execution_order(self) -> List[str]:
        """计算节点执行顺序（拓扑排序）"""
        # 计算入度
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node_id, deps in self.node_dependencies.items():
            for dep_id in deps:
                if dep_id in self.nodes:
                    in_degree[node_id] += 1

        # 拓扑排序
        order = []
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]

        while queue:
            node_id = queue.pop(0)
            order.append(node_id)

            # 更新依赖此节点的节点的入度
            for other_id in self.nodes[node_id].dependent_nodes:
                if other_id in in_degree:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        # 检查是否所有节点都被排序
        if len(order) != len(self.nodes):
            self.logger.warning("工作流可能存在循环依赖，无法确定完整的执行顺序")

        return order

    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调函数

        Args:
            event: 事件类型 ('node_start', 'node_complete', 'workflow_complete')
            callback: 回调函数
        """
        if event == 'node_start':
            self.on_node_start_callbacks.append(callback)
        elif event == 'node_complete':
            self.on_node_complete_callbacks.append(callback)
        elif event == 'workflow_complete':
            self.on_workflow_complete_callbacks.append(callback)
        else:
            raise ValueError(f"未知的事件类型: {event}")

        self.logger.debug(f"注册回调函数: {event}")

    def _trigger_callbacks(self, event: str, *args, **kwargs) -> None:
        """触发回调函数"""
        callbacks = []
        if event == 'node_start':
            callbacks = self.on_node_start_callbacks
        elif event == 'node_complete':
            callbacks = self.on_node_complete_callbacks
        elif event == 'workflow_complete':
            callbacks = self.on_workflow_complete_callbacks

        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {e}", exc_info=True)

    def execute(self, initial_input: Any = None) -> WorkflowResult:
        """执行工作流

        Args:
            initial_input: 初始输入数据

        Returns:
            工作流执行结果
        """
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()

        self.logger.log_workflow_start(
            workflow_id=self.workflow_id,
            total_nodes=len(self.nodes)
        )

        try:
            # 验证工作流
            is_valid, errors = self.validate_workflow()
            if not is_valid:
                raise WorkflowValidationError(
                    message="工作流验证失败",
                    workflow_id=self.workflow_id,
                    details={"errors": errors}
                )

            # 计算执行顺序
            self.node_execution_order = self._calculate_execution_order()
            self.logger.info(
                "节点执行顺序",
                execution_order=self.node_execution_order
            )

            # 执行节点
            current_data = initial_input
            for node_id in self.node_execution_order:
                node = self.nodes[node_id]

                # 检查节点是否可执行（依赖是否都已完成）
                deps_completed = all(
                    dep_id in self.results and
                    self.results[dep_id].status == NodeStatus.COMPLETED
                    for dep_id in self.node_dependencies[node_id]
                )

                if not deps_completed:
                    # 跳过节点
                    result = node.skip("依赖节点未完成")
                    self.results[node_id] = result
                    continue

                # 触发节点开始回调
                self._trigger_callbacks('node_start', node, current_data)

                # 执行节点
                result = node.execute(current_data)
                self.results[node_id] = result

                # 触发节点完成回调
                self._trigger_callbacks('node_complete', node, result)

                # 更新当前数据
                if result.status == NodeStatus.COMPLETED and result.output_data is not None:
                    current_data = result.output_data
                elif result.status == NodeStatus.FAILED:
                    # 节点失败，停止工作流
                    self.logger.error(f"节点执行失败，停止工作流: {node_id}")
                    break

            # 确定工作流状态
            self._determine_workflow_status()
            self.final_output = current_data

            # 记录执行结果
            self._log_execution_summary()

            # 触发工作流完成回调
            self._trigger_callbacks('workflow_complete', self.get_result())

            return self.get_result()

        except Exception as exc:
            self.status = WorkflowStatus.FAILED
            self.end_time = datetime.now()
            self.execution_time = (self.end_time - self.start_time).total_seconds()

            error_info = self.exception_handler.handle_exception(
                exc,
                context={
                    "workflow_id": self.workflow_id,
                    "workflow_name": self.workflow_name,
                    "initial_input": str(initial_input)[:100] if initial_input else None
                },
                reraise=False
            )

            self.logger.log_workflow_end(
                workflow_id=self.workflow_id,
                success=False,
                duration_seconds=self.execution_time
            )

            return self._create_result(
                status=WorkflowStatus.FAILED,
                error_message=str(exc),
                error_details=error_info
            )

        finally:
            if self.end_time is None:
                self.end_time = datetime.now()
                self.execution_time = (self.end_time - self.start_time).total_seconds()

    def _determine_workflow_status(self) -> None:
        """确定工作流状态"""
        if not self.results:
            self.status = WorkflowStatus.FAILED
            return

        # 统计节点状态
        status_counts = {status: 0 for status in NodeStatus}
        for result in self.results.values():
            status_counts[result.status] += 1

        # 根据节点状态确定工作流状态
        if status_counts[NodeStatus.FAILED] > 0:
            self.status = WorkflowStatus.FAILED
        elif status_counts[NodeStatus.COMPLETED] == len(self.nodes):
            self.status = WorkflowStatus.COMPLETED
        elif status_counts[NodeStatus.RUNNING] > 0:
            self.status = WorkflowStatus.RUNNING
        else:
            self.status = WorkflowStatus.PENDING

    def _log_execution_summary(self) -> None:
        """记录执行摘要"""
        status_counts = {status.value: 0 for status in NodeStatus}
        for result in self.results.values():
            status_counts[result.status.value] += 1

        self.logger.log_workflow_end(
            workflow_id=self.workflow_id,
            success=self.status == WorkflowStatus.COMPLETED,
            duration_seconds=self.execution_time
        )

        self.logger.info(
            "工作流执行摘要",
            workflow_id=self.workflow_id,
            status=self.status.value,
            execution_time_seconds=self.execution_time,
            node_status_counts=status_counts,
            total_nodes=len(self.nodes),
            executed_nodes=len(self.results)
        )

    def _create_result(
        self,
        status: WorkflowStatus,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowResult:
        """创建工作流结果"""
        # 统计节点状态
        status_counts = {status: 0 for status in NodeStatus}
        for result in self.results.values():
            status_counts[result.status] += 1

        result = WorkflowResult(
            workflow_id=self.workflow_id,
            workflow_name=self.workflow_name,
            status=status,
            start_time=self.start_time,
            end_time=self.end_time,
            execution_time=self.execution_time,
            total_nodes=len(self.nodes),
            completed_nodes=status_counts[NodeStatus.COMPLETED],
            failed_nodes=status_counts[NodeStatus.FAILED],
            skipped_nodes=status_counts[NodeStatus.SKIPPED],
            node_results=self.results.copy(),
            final_output=self.final_output,
            error_message=error_message,
            error_details=error_details,
            metadata=metadata or {}
        )

        return result

    def get_result(self) -> WorkflowResult:
        """获取工作流执行结果"""
        return self._create_result(self.status)

    def get_node_result(self, node_id: str) -> Optional[NodeResult]:
        """获取节点执行结果"""
        return self.results.get(node_id)

    def get_node_status(self, node_id: str) -> Optional[NodeStatus]:
        """获取节点状态"""
        result = self.get_node_result(node_id)
        return result.status if result else None

    def pause(self) -> None:
        """暂停工作流"""
        if self.status == WorkflowStatus.RUNNING:
            self.status = WorkflowStatus.PAUSED
            self.logger.info("工作流已暂停")
        else:
            self.logger.warning(f"无法暂停，当前状态: {self.status.value}")

    def resume(self) -> None:
        """恢复工作流"""
        if self.status == WorkflowStatus.PAUSED:
            self.status = WorkflowStatus.RUNNING
            self.logger.info("工作流已恢复")
        else:
            self.logger.warning(f"无法恢复，当前状态: {self.status.value}")

    def cancel(self) -> None:
        """取消工作流"""
        self.status = WorkflowStatus.CANCELLED
        self.end_time = datetime.now()
        self.execution_time = (self.end_time - self.start_time).total_seconds()
        self.logger.info("工作流已取消")

    def reset(self) -> None:
        """重置工作流"""
        self.status = WorkflowStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.execution_time = 0.0
        self.results = {}
        self.final_output = None

        # 重置所有节点
        for node in self.nodes.values():
            node.reset()

        self.logger.info("工作流已重置")

    def get_summary(self) -> Dict[str, Any]:
        """获取工作流摘要"""
        status_counts = {status.value: 0 for status in NodeStatus}
        for result in self.results.values():
            status_counts[result.status.value] += 1

        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "total_nodes": len(self.nodes),
            "executed_nodes": len(self.results),
            "node_status_counts": status_counts,
            "execution_time": self.execution_time,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    def __str__(self) -> str:
        return f"Workflow(id={self.workflow_id}, name={self.workflow_name}, status={self.status.value})"

    def __repr__(self) -> str:
        return self.__str__()


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


__all__ = [
    "WorkflowStatus",
    "WorkflowResult",
    "WorkflowEngine",
    "WorkflowValidationError",
]