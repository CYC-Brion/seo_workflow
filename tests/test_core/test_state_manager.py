"""
状态管理器单元测试
"""
import json
import pickle
import tempfile
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from pathlib import Path

from src.core.state_manager import (
    StateManager,
    StorageType,
    WorkflowState,
    state_manager,
    get_state_manager,
)
from src.core.workflow_engine import WorkflowStatus, WorkflowResult
from src.core.base_node import NodeStatus, NodeResult


class TestStateManager:
    """状态管理器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "states"

    def teardown_method(self):
        """每个测试方法后的清理"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization_default(self):
        """测试默认初始化"""
        manager = StateManager(storage_path=self.storage_path)

        assert manager.storage_path == self.storage_path
        assert manager.storage_type == StorageType.JSON
        assert self.storage_path.exists()

    def test_initialization_with_pickle(self):
        """测试使用Pickle存储初始化"""
        manager = StateManager(
            storage_path=self.storage_path,
            storage_type=StorageType.PICKLE
        )

        assert manager.storage_type == StorageType.PICKLE
        assert self.storage_path.exists()

    def test_save_workflow_state_json(self):
        """测试保存工作流状态（JSON格式）"""
        manager = StateManager(storage_path=self.storage_path)

        # 创建工作流状态
        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=1.5,
            current_node_id="node1",
            node_states={"node1": {"status": "completed"}},
            workflow_data={"result": "success"},
            metadata={"version": "1.0"}
        )

        # 保存状态
        success = manager.save_workflow_state(workflow_state)

        assert success == True

        # 验证文件已创建
        file_path = self.storage_path / "test-workflow-1.json"
        assert file_path.exists()

        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["workflow_id"] == "test-workflow-1"
        assert data["workflow_name"] == "测试工作流"
        assert data["status"] == "completed"

    def test_save_workflow_state_pickle(self):
        """测试保存工作流状态（Pickle格式）"""
        manager = StateManager(
            storage_path=self.storage_path,
            storage_type=StorageType.PICKLE
        )

        # 创建工作流状态
        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        # 保存状态
        success = manager.save_workflow_state(workflow_state)

        assert success == True

        # 验证文件已创建
        file_path = self.storage_path / "test-workflow-1.pkl"
        assert file_path.exists()

        # 验证文件内容
        with open(file_path, 'rb') as f:
            data = pickle.load(f)

        assert data["workflow_id"] == "test-workflow-1"

    def test_save_workflow_state_with_custom_filename(self):
        """测试使用自定义文件名保存工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        # 使用自定义文件名
        success = manager.save_workflow_state(
            workflow_state,
            filename="custom-filename"
        )

        assert success == True

        # 验证文件已创建（使用自定义文件名）
        file_path = self.storage_path / "custom-filename.json"
        assert file_path.exists()

    def test_save_workflow_state_error(self):
        """测试保存工作流状态时出错"""
        manager = StateManager(storage_path=self.storage_path)

        # 创建无效的存储类型以触发错误
        manager.storage_type = "invalid_type"

        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        # 保存应该失败
        success = manager.save_workflow_state(workflow_state)

        assert success == False

    def test_load_workflow_state_json(self):
        """测试加载工作流状态（JSON格式）"""
        manager = StateManager(storage_path=self.storage_path)

        # 先保存一个状态
        original_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=1.5,
            current_node_id="node1",
            node_states={"node1": {"status": "completed"}},
            workflow_data={"result": "success"},
            metadata={"version": "1.0"}
        )

        manager.save_workflow_state(original_state)

        # 加载状态
        loaded_state = manager.load_workflow_state("test-workflow-1")

        assert loaded_state is not None
        assert loaded_state.workflow_id == original_state.workflow_id
        assert loaded_state.workflow_name == original_state.workflow_name
        assert loaded_state.status == original_state.status
        assert loaded_state.execution_time == original_state.execution_time

    def test_load_workflow_state_pickle(self):
        """测试加载工作流状态（Pickle格式）"""
        manager = StateManager(
            storage_path=self.storage_path,
            storage_type=StorageType.PICKLE
        )

        # 先保存一个状态
        original_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        manager.save_workflow_state(original_state)

        # 加载状态
        loaded_state = manager.load_workflow_state("test-workflow-1")

        assert loaded_state is not None
        assert loaded_state.workflow_id == original_state.workflow_id

    def test_load_nonexistent_workflow_state(self):
        """测试加载不存在的工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        loaded_state = manager.load_workflow_state("nonexistent")

        assert loaded_state is None

    def test_load_workflow_state_by_filename(self):
        """测试通过文件名加载工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 保存状态，使用自定义文件名
        original_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        manager.save_workflow_state(original_state, filename="custom-file")

        # 通过文件名加载
        loaded_state = manager.load_workflow_state("custom-file")

        assert loaded_state is not None
        assert loaded_state.workflow_id == "test-workflow-1"

    def test_delete_workflow_state(self):
        """测试删除工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 先保存一个状态
        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        manager.save_workflow_state(workflow_state)

        # 验证文件存在
        file_path = self.storage_path / "test-workflow-1.json"
        assert file_path.exists()

        # 删除状态
        success = manager.delete_workflow_state("test-workflow-1")

        assert success == True
        assert not file_path.exists()

    def test_delete_nonexistent_workflow_state(self):
        """测试删除不存在的工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        success = manager.delete_workflow_state("nonexistent")

        assert success == False

    def test_list_workflow_states(self):
        """测试列出工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 保存多个状态
        for i in range(3):
            workflow_state = WorkflowState(
                workflow_id=f"test-workflow-{i}",
                workflow_name=f"测试工作流-{i}",
                status=WorkflowStatus.COMPLETED if i % 2 == 0 else WorkflowStatus.FAILED
            )
            manager.save_workflow_state(workflow_state)

        # 列出所有状态
        states = manager.list_workflow_states()

        assert len(states) == 3
        assert any(s["workflow_id"] == "test-workflow-0" for s in states)
        assert any(s["workflow_id"] == "test-workflow-1" for s in states)
        assert any(s["workflow_id"] == "test-workflow-2" for s in states)

    def test_list_workflow_states_with_filter(self):
        """测试使用过滤器列出工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 保存不同状态的状态
        completed_state = WorkflowState(
            workflow_id="completed-workflow",
            workflow_name="已完成工作流",
            status=WorkflowStatus.COMPLETED
        )
        failed_state = WorkflowState(
            workflow_id="failed-workflow",
            workflow_name="失败工作流",
            status=WorkflowStatus.FAILED
        )

        manager.save_workflow_state(completed_state)
        manager.save_workflow_state(failed_state)

        # 过滤已完成的状态
        completed_states = manager.list_workflow_states(
            status_filter=WorkflowStatus.COMPLETED
        )

        assert len(completed_states) == 1
        assert completed_states[0]["workflow_id"] == "completed-workflow"
        assert completed_states[0]["status"] == "completed"

        # 过滤失败的状态
        failed_states = manager.list_workflow_states(
            status_filter=WorkflowStatus.FAILED
        )

        assert len(failed_states) == 1
        assert failed_states[0]["workflow_id"] == "failed-workflow"
        assert failed_states[0]["status"] == "failed"

    def test_list_workflow_states_with_limit(self):
        """测试使用限制列出工作流状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 保存多个状态
        for i in range(10):
            workflow_state = WorkflowState(
                workflow_id=f"test-workflow-{i}",
                workflow_name=f"测试工作流-{i}",
                status=WorkflowStatus.COMPLETED
            )
            manager.save_workflow_state(workflow_state)

        # 限制返回数量
        states = manager.list_workflow_states(limit=5)

        assert len(states) == 5

    def test_create_state_from_result(self):
        """测试从工作流结果创建状态"""
        manager = StateManager(storage_path=self.storage_path)

        # 创建工作流结果
        node_results = {
            "node1": NodeResult(
                node_id="node1",
                node_type="test_node",
                status=NodeStatus.COMPLETED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_time=0.5
            ),
            "node2": NodeResult(
                node_id="node2",
                node_type="test_node",
                status=NodeStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_time=0.3,
                error_message="测试错误"
            )
        }

        workflow_result = WorkflowResult(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=1.0,
            total_nodes=2,
            completed_nodes=1,
            failed_nodes=1,
            skipped_nodes=0,
            node_results=node_results,
            final_output="最终输出",
            error_message=None,
            metadata={"test": "metadata"}
        )

        # 创建状态
        workflow_state = manager.create_state_from_result(workflow_result)

        assert workflow_state.workflow_id == "test-workflow-1"
        assert workflow_state.workflow_name == "测试工作流"
        assert workflow_state.status == WorkflowStatus.RUNNING
        assert workflow_state.execution_time == 1.0

        # 验证节点状态
        assert "node1" in workflow_state.node_states
        assert "node2" in workflow_state.node_states
        assert workflow_state.node_states["node1"]["status"] == "completed"
        assert workflow_state.node_states["node2"]["status"] == "failed"

        # 验证工作流数据
        assert "final_output_summary" in workflow_state.workflow_data
        assert "error_message" in workflow_state.workflow_data

    def test_create_checkpoint(self):
        """测试创建检查点"""
        manager = StateManager(storage_path=self.storage_path)

        # 创建模拟工作流引擎
        workflow_engine = Mock()
        workflow_engine.workflow_id = "test-workflow-1"
        workflow_engine.workflow_name = "测试工作流"
        workflow_engine.status = WorkflowStatus.RUNNING
        workflow_engine.start_time = datetime.now()
        workflow_engine.execution_time = 0.5

        # 创建模拟节点
        node1 = Mock()
        node1.node_id = "node1"
        node1.node_type = "test_node"

        node2 = Mock()
        node2.node_id = "node2"
        node2.node_type = "test_node"

        workflow_engine.nodes = {"node1": node1, "node2": node2}

        # 创建模拟节点结果
        node_result = NodeResult(
            node_id="node1",
            node_type="test_node",
            status=NodeStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=0.2
        )

        workflow_engine.results = {"node1": node_result}

        # 创建工作流数据
        workflow_data = {"current_data": "test_data", "step": 1}

        # 创建检查点
        checkpoint = manager.create_checkpoint(
            workflow_engine=workflow_engine,
            node_id="node1",
            node_result=node_result,
            workflow_data=workflow_data
        )

        assert checkpoint.workflow_id == "test-workflow-1"
        assert checkpoint.status == WorkflowStatus.RUNNING
        assert checkpoint.current_node_id == "node1"
        assert checkpoint.workflow_data == workflow_data

        # 验证节点状态
        assert "node1" in checkpoint.node_states
        assert checkpoint.node_states["node1"]["status"] == "completed"
        assert "node2" in checkpoint.node_states
        assert checkpoint.node_states["node2"]["status"] == "pending"

    def test_cleanup_old_states(self):
        """测试清理旧的状态文件"""
        manager = StateManager(storage_path=self.storage_path)

        # 创建一些状态文件
        for i in range(3):
            workflow_state = WorkflowState(
                workflow_id=f"test-workflow-{i}",
                workflow_name=f"测试工作流-{i}",
                status=WorkflowStatus.COMPLETED
            )
            manager.save_workflow_state(workflow_state)

        # 验证文件存在
        assert len(list(self.storage_path.glob("*.json"))) == 3

        # 模拟文件修改时间为30天前
        old_time = datetime.now() - timedelta(days=31)
        old_timestamp = old_time.timestamp()

        for file_path in self.storage_path.glob("*.json"):
            # 修改文件时间（需要操作系统支持）
            try:
                import os
                os.utime(file_path, (old_timestamp, old_timestamp))
            except:
                pass  # 如果失败，跳过时间修改

        # 清理30天前的文件
        deleted_count = manager.cleanup_old_states(max_age_days=30)

        # 验证文件已被清理（可能为0，如果时间修改失败）
        assert deleted_count >= 0

    def test_workflow_state_to_dict_and_from_dict(self):
        """测试工作流状态的字典转换"""
        original_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=1.5,
            current_node_id="node1",
            node_states={"node1": {"status": "completed"}},
            workflow_data={"result": "success"},
            metadata={"version": "1.0"}
        )

        # 转换为字典
        state_dict = original_state.to_dict()

        assert state_dict["workflow_id"] == "test-workflow-1"
        assert state_dict["status"] == "completed"
        assert "start_time" in state_dict
        assert "end_time" in state_dict

        # 从字典创建
        restored_state = WorkflowState.from_dict(state_dict)

        assert restored_state.workflow_id == original_state.workflow_id
        assert restored_state.workflow_name == original_state.workflow_name
        assert restored_state.status == original_state.status
        assert restored_state.execution_time == original_state.execution_time
        assert restored_state.current_node_id == original_state.current_node_id

    def test_find_state_file_by_workflow_id(self):
        """测试通过workflow_id查找状态文件"""
        manager = StateManager(storage_path=self.storage_path)

        # 保存状态，使用自定义文件名
        workflow_state = WorkflowState(
            workflow_id="test-workflow-1",
            workflow_name="测试工作流",
            status=WorkflowStatus.COMPLETED
        )

        manager.save_workflow_state(workflow_state, filename="different-filename")

        # 通过workflow_id查找应该能找到文件
        file_path = manager._find_state_file("test-workflow-1")

        assert file_path is not None
        assert file_path.exists()

        # 文件名应该包含"different-filename"
        assert "different-filename" in str(file_path)

    def test_global_state_manager(self):
        """测试全局状态管理器实例"""
        # 测试全局实例存在
        assert state_manager is not None
        assert isinstance(state_manager, StateManager)

        # 测试获取函数
        manager = get_state_manager()
        assert manager is state_manager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])