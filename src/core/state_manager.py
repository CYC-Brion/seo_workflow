"""
状态管理器
负责工作流状态的持久化、恢复和管理
"""

import json
import pickle
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict

from src.utils import get_logger, exception_handler

from .workflow_engine import WorkflowStatus, WorkflowResult
from .base_node import NodeStatus, NodeResult

try:
    from config.settings import CACHE_DIR as _CACHE_DIR
except ImportError:  # config 包不可用时退回按 __file__ 锚定
    _CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"

# 锚定到项目根，避免状态目录随启动目录漂移（原先是 CWD 相对的 "data/cache/states"）
_DEFAULT_STORAGE_PATH = _CACHE_DIR / "states"


class StorageType(Enum):
    """存储类型"""
    JSON = "json"
    PICKLE = "pickle"
    SQLITE = "sqlite"


@dataclass
class WorkflowState:
    """工作流状态"""
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    current_node_id: Optional[str] = None
    node_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    workflow_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time": self.execution_time,
            "current_node_id": self.current_node_id,
            "node_states": self.node_states,
            "workflow_data": self.workflow_data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """从字典创建"""
        # 转换字符串时间回datetime对象
        start_time = None
        end_time = None

        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])

        # 转换状态枚举
        status = WorkflowStatus(data["status"])

        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            status=status,
            start_time=start_time,
            end_time=end_time,
            execution_time=data.get("execution_time", 0.0),
            current_node_id=data.get("current_node_id"),
            node_states=data.get("node_states", {}),
            workflow_data=data.get("workflow_data", {}),
            metadata=data.get("metadata", {}),
        )


class StateManager:
    """状态管理器"""

    def __init__(
        self,
        storage_path: Union[str, Path] = _DEFAULT_STORAGE_PATH,
        storage_type: StorageType = StorageType.JSON
    ):
        """
        初始化状态管理器

        Args:
            storage_path: 存储路径
            storage_type: 存储类型
        """
        self.storage_path = Path(storage_path)
        self.storage_type = storage_type
        self.logger = get_logger("state_manager")
        self.exception_handler = exception_handler

        # 创建存储目录
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"状态管理器初始化",
            storage_path=str(self.storage_path),
            storage_type=storage_type.value
        )

    def save_workflow_state(
        self,
        workflow_state: WorkflowState,
        filename: Optional[str] = None
    ) -> bool:
        """保存工作流状态

        Args:
            workflow_state: 工作流状态
            filename: 文件名（不包含扩展名），如果为None则使用workflow_id

        Returns:
            是否保存成功
        """
        try:
            filename = filename or workflow_state.workflow_id
            file_path = self._get_file_path(filename)

            state_dict = workflow_state.to_dict()

            if self.storage_type == StorageType.JSON:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_dict, f, ensure_ascii=False, indent=2)
            elif self.storage_type == StorageType.PICKLE:
                with open(file_path, 'wb') as f:
                    pickle.dump(state_dict, f)
            else:
                raise ValueError(f"不支持的存储类型: {self.storage_type}")

            self.logger.debug(
                f"保存工作流状态: {workflow_state.workflow_id}",
                file_path=str(file_path),
                workflow_status=workflow_state.status.value
            )
            return True

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "save_workflow_state",
                    "workflow_id": workflow_state.workflow_id,
                    "filename": filename
                },
                reraise=False
            )
            return False

    def load_workflow_state(self, identifier: str) -> Optional[WorkflowState]:
        """加载工作流状态

        Args:
            identifier: 标识符（workflow_id或文件名）

        Returns:
            工作流状态，如果加载失败返回None
        """
        try:
            file_path = self._find_state_file(identifier)
            if not file_path or not file_path.exists():
                self.logger.warning(f"状态文件不存在: {identifier}")
                return None

            if self.storage_type == StorageType.JSON:
                with open(file_path, 'r', encoding='utf-8') as f:
                    state_dict = json.load(f)
            elif self.storage_type == StorageType.PICKLE:
                with open(file_path, 'rb') as f:
                    state_dict = pickle.load(f)
            else:
                raise ValueError(f"不支持的存储类型: {self.storage_type}")

            workflow_state = WorkflowState.from_dict(state_dict)

            self.logger.debug(
                f"加载工作流状态: {workflow_state.workflow_id}",
                file_path=str(file_path),
                workflow_status=workflow_state.status.value
            )
            return workflow_state

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "load_workflow_state",
                    "identifier": identifier
                },
                reraise=False
            )
            return None

    def delete_workflow_state(self, identifier: str) -> bool:
        """删除工作流状态

        Args:
            identifier: 标识符（workflow_id或文件名）

        Returns:
            是否删除成功
        """
        try:
            file_path = self._find_state_file(identifier)
            if not file_path or not file_path.exists():
                self.logger.warning(f"状态文件不存在: {identifier}")
                return False

            file_path.unlink()
            self.logger.debug(f"删除工作流状态: {identifier}", file_path=str(file_path))
            return True

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "delete_workflow_state",
                    "identifier": identifier
                },
                reraise=False
            )
            return False

    def list_workflow_states(
        self,
        status_filter: Optional[WorkflowStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出工作流状态

        Args:
            status_filter: 状态过滤器
            limit: 返回数量限制

        Returns:
            工作流状态列表
        """
        states = []
        try:
            pattern = "*.json" if self.storage_type == StorageType.JSON else "*.pkl"
            state_files = list(self.storage_path.glob(pattern))[:limit]

            for file_path in state_files:
                try:
                    workflow_state = self.load_workflow_state(file_path.stem)
                    if workflow_state:
                        if status_filter is None or workflow_state.status == status_filter:
                            states.append(workflow_state.to_dict())
                except Exception as e:
                    self.logger.warning(f"加载状态文件失败: {file_path}", error=str(e))
                    continue

            self.logger.debug(f"列出工作流状态", count=len(states), filtered_by=status_filter)
            return states

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "list_workflow_states",
                    "status_filter": status_filter,
                    "limit": limit
                },
                reraise=False
            )
            return []

    def create_state_from_result(self, workflow_result: WorkflowResult) -> WorkflowState:
        """从工作流结果创建状态

        Args:
            workflow_result: 工作流结果

        Returns:
            工作流状态
        """
        # 提取节点状态
        node_states = {}
        for node_id, node_result in workflow_result.node_results.items():
            node_states[node_id] = {
                "status": node_result.status.value,
                "execution_time": node_result.execution_time,
                "start_time": node_result.start_time.isoformat() if node_result.start_time else None,
                "end_time": node_result.end_time.isoformat() if node_result.end_time else None,
                "has_error": node_result.error_message is not None,
                "metadata": node_result.metadata,
            }

        # 确定当前节点
        current_node_id = None
        if workflow_result.status == WorkflowStatus.RUNNING:
            # 找到最后一个完成的节点
            completed_nodes = [
                node_id for node_id, node_result in workflow_result.node_results.items()
                if node_result.status == NodeStatus.COMPLETED
            ]
            if completed_nodes:
                # 假设节点按顺序执行，最后一个完成的节点是当前节点
                current_node_id = completed_nodes[-1]

        return WorkflowState(
            workflow_id=workflow_result.workflow_id,
            workflow_name=workflow_result.workflow_name,
            status=workflow_result.status,
            start_time=workflow_result.start_time,
            end_time=workflow_result.end_time,
            execution_time=workflow_result.execution_time,
            current_node_id=current_node_id,
            node_states=node_states,
            workflow_data={
                "final_output_summary": str(workflow_result.final_output)[:200] if workflow_result.final_output else None,
                "error_message": workflow_result.error_message,
            },
            metadata=workflow_result.metadata,
        )

    def create_checkpoint(
        self,
        workflow_engine,
        node_id: str,
        node_result: NodeResult,
        workflow_data: Dict[str, Any]
    ) -> WorkflowState:
        """创建检查点

        Args:
            workflow_engine: 工作流引擎实例
            node_id: 当前节点ID
            node_result: 节点结果
            workflow_data: 工作流数据

        Returns:
            工作流状态
        """
        # 收集所有节点状态
        node_states = {}
        for nid, node in workflow_engine.nodes.items():
            node_result = workflow_engine.results.get(nid)
            if node_result:
                node_states[nid] = {
                    "status": node_result.status.value,
                    "execution_time": node_result.execution_time,
                    "start_time": node_result.start_time.isoformat() if node_result.start_time else None,
                    "end_time": node_result.end_time.isoformat() if node_result.end_time else None,
                    "has_error": node_result.error_message is not None,
                    "metadata": node_result.metadata,
                }
            else:
                node_states[nid] = {
                    "status": NodeStatus.PENDING.value,
                    "execution_time": 0.0,
                }

        return WorkflowState(
            workflow_id=workflow_engine.workflow_id,
            workflow_name=workflow_engine.workflow_name,
            status=workflow_engine.status,
            start_time=workflow_engine.start_time,
            end_time=datetime.now() if workflow_engine.status != WorkflowStatus.RUNNING else None,
            execution_time=workflow_engine.execution_time,
            current_node_id=node_id,
            node_states=node_states,
            workflow_data=workflow_data,
            metadata={
                "checkpoint_time": datetime.now().isoformat(),
                "node_id": node_id,
                "node_type": workflow_engine.nodes[node_id].node_type if node_id in workflow_engine.nodes else None,
            },
        )

    def _get_file_path(self, filename: str) -> Path:
        """获取文件路径"""
        if self.storage_type == StorageType.JSON:
            ext = ".json"
        elif self.storage_type == StorageType.PICKLE:
            ext = ".pkl"
        else:
            ext = ".state"

        return self.storage_path / f"{filename}{ext}"

    def _find_state_file(self, identifier: str) -> Optional[Path]:
        """查找状态文件"""
        # 尝试直接查找
        for ext in [".json", ".pkl", ".state"]:
            file_path = self.storage_path / f"{identifier}{ext}"
            if file_path.exists():
                return file_path

        # 尝试通过workflow_id查找
        for ext in [".json", ".pkl", ".state"]:
            pattern = f"*{ext}"
            for file_path in self.storage_path.glob(pattern):
                try:
                    if self.storage_type == StorageType.JSON:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            state_dict = json.load(f)
                    elif self.storage_type == StorageType.PICKLE:
                        with open(file_path, 'rb') as f:
                            state_dict = pickle.load(f)
                    else:
                        continue

                    if state_dict.get("workflow_id") == identifier:
                        return file_path
                except Exception:
                    continue

        return None

    def cleanup_old_states(self, max_age_days: int = 30) -> int:
        """清理旧的状态文件

        Args:
            max_age_days: 最大保留天数

        Returns:
            清理的文件数量
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(days=max_age_days)

            deleted_count = 0
            for file_path in self.storage_path.glob("*"):
                if file_path.is_file():
                    # 检查文件修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            self.logger.warning(f"删除文件失败: {file_path}", error=str(e))

            self.logger.info(f"清理旧的状态文件", deleted_count=deleted_count, max_age_days=max_age_days)
            return deleted_count

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "cleanup_old_states",
                    "max_age_days": max_age_days
                },
                reraise=False
            )
            return 0


# 全局状态管理器实例
state_manager = StateManager()

def get_state_manager() -> StateManager:
    """获取全局状态管理器"""
    return state_manager


__all__ = [
    "StorageType",
    "WorkflowState",
    "StateManager",
    "state_manager",
    "get_state_manager",
]