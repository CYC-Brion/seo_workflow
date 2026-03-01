"""
工作流引擎单元测试
"""
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime

from src.core.workflow_engine import (
    WorkflowEngine,
    WorkflowStatus,
    WorkflowResult,
    WorkflowValidationError,
)
from src.core.base_node import BaseNode, NodeStatus, NodeResult


class MockNode(BaseNode):
    """模拟节点用于测试"""

    def __init__(self, node_id, node_type="mock_node", config=None):
        super().__init__(node_id, node_type, config)
        self.execute_called = False
        self.execute_input = None
        self.execute_output = "output_" + node_id
        self.should_fail = False
        self.failure_message = "模拟失败"

    def execute_impl(self, input_data):
        self.execute_called = True
        self.execute_input = input_data

        if self.should_fail:
            raise Exception(self.failure_message)

        return self.execute_output

    def validate_input(self, input_data):
        # 接受任何输入
        return True

    def validate_output(self, output_data):
        # 接受任何输出
        return True


class TestWorkflowEngine:
    """工作流引擎测试类"""

    def test_initialization(self):
        """测试初始化"""
        engine = WorkflowEngine("test-workflow")

        assert engine.workflow_name == "test-workflow"
        assert len(engine.workflow_id) == 8
        assert engine.status == WorkflowStatus.PENDING
        assert engine.nodes == {}
        assert engine.node_dependencies == {}
        assert engine.results == {}

    def test_add_node(self):
        """测试添加节点"""
        engine = WorkflowEngine("test-workflow")
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        # 添加第一个节点
        engine.add_node(node1)
        assert "node1" in engine.nodes
        assert engine.nodes["node1"] == node1
        assert engine.node_dependencies["node1"] == []

        # 添加第二个节点，带依赖
        engine.add_node(node2, dependencies=["node1"])
        assert "node2" in engine.nodes
        assert engine.node_dependencies["node2"] == ["node1"]

        # 验证节点间的依赖关系
        assert node1.dependent_nodes == ["node2"]

    def test_add_node_duplicate_id(self):
        """测试添加重复节点ID"""
        engine = WorkflowEngine("test-workflow")
        node1 = MockNode("node1")
        node2 = MockNode("node1")  # 相同ID

        engine.add_node(node1)

        with pytest.raises(Exception) as exc_info:
            engine.add_node(node2)

        assert "节点ID已存在" in str(exc_info.value)

    def test_remove_node(self):
        """测试移除节点"""
        engine = WorkflowEngine("test-workflow")
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])

        # 验证依赖关系已建立
        assert "node1" in engine.nodes
        assert node1.dependent_nodes == ["node2"]

        # 移除节点
        engine.remove_node("node1")

        assert "node1" not in engine.nodes
        assert "node1" not in engine.node_dependencies
        assert node2.dependent_nodes == []  # 依赖关系已移除

    def test_remove_nonexistent_node(self):
        """测试移除不存在的节点"""
        engine = WorkflowEngine("test-workflow")

        with pytest.raises(Exception) as exc_info:
            engine.remove_node("nonexistent")

        assert "节点不存在" in str(exc_info.value)

    def test_validate_workflow_no_cycle(self):
        """测试验证无循环依赖的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建线性工作流: node1 -> node2 -> node3
        node1 = MockNode("node1")
        node2 = MockNode("node2")
        node3 = MockNode("node3")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])
        engine.add_node(node3, dependencies=["node2"])

        is_valid, errors = engine.validate_workflow()

        assert is_valid == True
        assert errors == []

    def test_validate_workflow_with_cycle(self):
        """测试验证有循环依赖的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建循环依赖: node1 -> node2 -> node3 -> node1
        node1 = MockNode("node1")
        node2 = MockNode("node2")
        node3 = MockNode("node3")

        engine.add_node(node1, dependencies=["node3"])  # node1 依赖 node3
        engine.add_node(node2, dependencies=["node1"])
        engine.add_node(node3, dependencies=["node2"])

        is_valid, errors = engine.validate_workflow()

        assert is_valid == False
        assert any("循环依赖" in error for error in errors)

    def test_validate_workflow_missing_dependency(self):
        """测试验证有缺失依赖的工作流"""
        engine = WorkflowEngine("test-workflow")

        node1 = MockNode("node1")

        # 添加依赖不存在的节点
        engine.add_node(node1, dependencies=["nonexistent"])

        is_valid, errors = engine.validate_workflow()

        assert is_valid == False
        assert any("依赖节点不存在" in error for error in errors)

    def test_calculate_execution_order(self):
        """测试计算执行顺序"""
        engine = WorkflowEngine("test-workflow")

        # 创建复杂依赖关系
        # node1 -> node2, node3
        # node2 -> node4
        # node3 -> node4
        nodes = {f"node{i}": MockNode(f"node{i}") for i in range(1, 5)}

        for node in nodes.values():
            engine.add_node(node)

        # 设置依赖关系
        engine.node_dependencies["node2"] = ["node1"]
        engine.node_dependencies["node3"] = ["node1"]
        engine.node_dependencies["node4"] = ["node2", "node3"]

        # 更新依赖节点关系
        for node_id, deps in engine.node_dependencies.items():
            for dep_id in deps:
                if dep_id in engine.nodes:
                    engine.nodes[dep_id].add_dependent_node(node_id)

        order = engine._calculate_execution_order()

        # 验证拓扑顺序
        assert "node1" in order
        assert "node4" in order

        # node1 应该在 node2 和 node3 之前
        node1_index = order.index("node1")
        node2_index = order.index("node2")
        node3_index = order.index("node3")
        node4_index = order.index("node4")

        assert node1_index < node2_index
        assert node1_index < node3_index
        assert node2_index < node4_index
        assert node3_index < node4_index

    def test_register_callback(self):
        """测试注册回调函数"""
        engine = WorkflowEngine("test-workflow")

        # 创建模拟回调
        node_start_callback = Mock()
        node_complete_callback = Mock()
        workflow_complete_callback = Mock()

        # 注册回调
        engine.register_callback("node_start", node_start_callback)
        engine.register_callback("node_complete", node_complete_callback)
        engine.register_callback("workflow_complete", workflow_complete_callback)

        assert node_start_callback in engine.on_node_start_callbacks
        assert node_complete_callback in engine.on_node_complete_callbacks
        assert workflow_complete_callback in engine.on_workflow_complete_callbacks

    def test_register_invalid_callback_event(self):
        """测试注册无效事件类型的回调"""
        engine = WorkflowEngine("test-workflow")

        callback = Mock()

        with pytest.raises(ValueError) as exc_info:
            engine.register_callback("invalid_event", callback)

        assert "未知的事件类型" in str(exc_info.value)

    def test_execute_workflow_success(self):
        """测试执行成功的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建简单工作流: node1 -> node2
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])

        # 执行工作流
        result = engine.execute("initial_input")

        # 验证结果
        assert result.status == WorkflowStatus.COMPLETED
        assert result.workflow_id == engine.workflow_id
        assert result.total_nodes == 2
        assert result.completed_nodes == 2
        assert result.failed_nodes == 0

        # 验证节点执行
        assert node1.execute_called
        assert node2.execute_called
        assert node1.execute_input == "initial_input"
        assert node2.execute_input == "output_node1"

        # 验证执行结果存储
        assert "node1" in engine.results
        assert "node2" in engine.results
        assert engine.results["node1"].status == NodeStatus.COMPLETED
        assert engine.results["node2"].status == NodeStatus.COMPLETED

    def test_execute_workflow_with_failed_node(self):
        """测试执行有节点失败的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建工作流，其中node2会失败
        node1 = MockNode("node1")
        node2 = MockNode("node2")
        node2.should_fail = True
        node3 = MockNode("node3")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])
        engine.add_node(node3, dependencies=["node2"])

        # 执行工作流
        result = engine.execute("initial_input")

        # 验证结果
        assert result.status == WorkflowStatus.FAILED
        assert result.total_nodes == 3
        assert result.completed_nodes == 1  # node1完成
        assert result.failed_nodes == 1  # node2失败

        # 验证节点执行
        assert node1.execute_called
        assert node2.execute_called
        assert not node3.execute_called  # node3应该被跳过

        # 验证执行结果
        assert engine.results["node1"].status == NodeStatus.COMPLETED
        assert engine.results["node2"].status == NodeStatus.FAILED
        assert "node3" not in engine.results

    def test_execute_workflow_with_skip(self):
        """测试执行有跳过节点的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建工作流，其中node2依赖不存在的节点（将导致验证失败）
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["nonexistent"])  # 依赖不存在的节点

        # 执行工作流，验证失败
        result = engine.execute("initial_input")

        # 验证结果状态为失败
        assert result.status == WorkflowStatus.FAILED
        assert result.error_message is not None
        assert "验证失败" in result.error_message or "依赖节点不存在" in result.error_message

    def test_execute_workflow_invalid_validation(self):
        """测试执行验证失败的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建有循环依赖的工作流
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        engine.add_node(node1, dependencies=["node2"])
        engine.add_node(node2, dependencies=["node1"])

        # 执行工作流，应该返回验证失败的结果
        result = engine.execute("initial_input")

        # 验证结果状态为失败
        assert result.status == WorkflowStatus.FAILED
        assert result.error_message is not None
        assert "验证失败" in result.error_message or "循环依赖" in result.error_message

    def test_execute_workflow_with_callbacks(self):
        """测试执行工作流并触发回调"""
        engine = WorkflowEngine("test-workflow")

        # 创建模拟回调
        node_start_callback = Mock()
        node_complete_callback = Mock()
        workflow_complete_callback = Mock()

        engine.register_callback("node_start", node_start_callback)
        engine.register_callback("node_complete", node_complete_callback)
        engine.register_callback("workflow_complete", workflow_complete_callback)

        # 创建简单工作流
        node1 = MockNode("node1")
        engine.add_node(node1)

        # 执行工作流
        result = engine.execute("initial_input")

        # 验证回调被调用
        node_start_callback.assert_called_once()
        node_complete_callback.assert_called_once()
        workflow_complete_callback.assert_called_once()

        # 验证回调参数
        node_start_args = node_start_callback.call_args[0]
        assert node_start_args[0] == node1  # 节点
        assert node_start_args[1] == "initial_input"  # 输入数据

    def test_pause_resume_workflow(self):
        """测试暂停和恢复工作流"""
        engine = WorkflowEngine("test-workflow")

        # 初始状态不能暂停
        engine.pause()
        assert engine.status == WorkflowStatus.PENDING  # 状态不变

        # 开始执行
        engine.status = WorkflowStatus.RUNNING

        # 暂停
        engine.pause()
        assert engine.status == WorkflowStatus.PAUSED

        # 恢复
        engine.resume()
        assert engine.status == WorkflowStatus.RUNNING

        # 非暂停状态不能恢复
        engine.status = WorkflowStatus.COMPLETED
        engine.resume()
        assert engine.status == WorkflowStatus.COMPLETED  # 状态不变

    def test_cancel_workflow(self):
        """测试取消工作流"""
        engine = WorkflowEngine("test-workflow")

        # 设置开始时间
        engine.start_time = datetime.now()

        # 取消
        engine.cancel()

        assert engine.status == WorkflowStatus.CANCELLED
        assert engine.end_time is not None
        assert engine.execution_time > 0

    def test_reset_workflow(self):
        """测试重置工作流"""
        engine = WorkflowEngine("test-workflow")

        # 设置一些状态
        node1 = MockNode("node1")
        engine.add_node(node1)
        engine.status = WorkflowStatus.COMPLETED
        engine.start_time = datetime.now()
        engine.end_time = datetime.now()
        engine.execution_time = 1.5
        engine.results["node1"] = NodeResult(
            node_id="node1",
            node_type="mock_node",
            status=NodeStatus.COMPLETED
        )

        # 重置
        engine.reset()

        assert engine.status == WorkflowStatus.PENDING
        assert engine.start_time is None
        assert engine.end_time is None
        assert engine.execution_time == 0.0
        assert engine.results == {}
        assert node1.status == NodeStatus.PENDING

    def test_get_node_result(self):
        """测试获取节点结果"""
        engine = WorkflowEngine("test-workflow")

        node1 = MockNode("node1")
        engine.add_node(node1)

        # 执行工作流
        engine.execute("initial_input")

        # 获取节点结果
        result = engine.get_node_result("node1")

        assert result is not None
        assert result.node_id == "node1"
        assert result.status == NodeStatus.COMPLETED

    def test_get_node_status(self):
        """测试获取节点状态"""
        engine = WorkflowEngine("test-workflow")

        node1 = MockNode("node1")
        engine.add_node(node1)

        # 执行工作流
        engine.execute("initial_input")

        # 获取节点状态
        status = engine.get_node_status("node1")

        assert status == NodeStatus.COMPLETED

    def test_get_summary(self):
        """测试获取工作流摘要"""
        engine = WorkflowEngine("test-workflow")

        # 创建工作流并执行
        node1 = MockNode("node1")
        node2 = MockNode("node2")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])

        engine.execute("initial_input")

        # 获取摘要
        summary = engine.get_summary()

        assert summary["workflow_id"] == engine.workflow_id
        assert summary["workflow_name"] == "test-workflow"
        assert summary["status"] == WorkflowStatus.COMPLETED.value
        assert summary["total_nodes"] == 2
        assert summary["executed_nodes"] == 2
        assert "node_status_counts" in summary

    def test_workflow_result_to_dict(self):
        """测试工作流结果转换为字典"""
        result = WorkflowResult(
            workflow_id="test-id",
            workflow_name="test-workflow",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_time=1.5,
            total_nodes=3,
            completed_nodes=3,
            failed_nodes=0,
            skipped_nodes=0,
            node_results={},
            final_output="output",
            error_message=None,
            error_details=None,
            metadata={"test": "metadata"}
        )

        result_dict = result.to_dict()

        assert result_dict["workflow_id"] == "test-id"
        assert result_dict["workflow_name"] == "test-workflow"
        assert result_dict["status"] == "completed"
        assert result_dict["execution_time"] == 1.5
        assert result_dict["total_nodes"] == 3
        assert result_dict["completed_nodes"] == 3
        assert result_dict["success_rate"] == 1.0
        assert result_dict["has_final_output"] == True
        assert result_dict["has_error"] == False
        assert "metadata" in result_dict

    def test_workflow_with_no_nodes(self):
        """测试没有节点的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 执行空工作流
        result = engine.execute("initial_input")

        assert result.status == WorkflowStatus.FAILED  # 没有节点，视为失败
        assert result.total_nodes == 0

    def test_node_dependency_updates(self):
        """测试节点依赖关系更新"""
        engine = WorkflowEngine("test-workflow")

        # 先添加被依赖的节点
        node1 = MockNode("node1")
        engine.add_node(node1)

        # 添加依赖node1的节点
        node2 = MockNode("node2")
        engine.add_node(node2, dependencies=["node1"])

        # 验证依赖关系
        assert "node1" in engine.node_dependencies["node2"]
        assert "node2" in node1.dependent_nodes

        # 移除node1
        engine.remove_node("node1")

        # 验证依赖关系已清除
        assert "node1" not in engine.nodes
        assert "node2" in engine.nodes
        assert "node1" not in engine.node_dependencies.get("node2", [])

    def test_workflow_with_parallel_nodes(self):
        """测试并行节点的工作流"""
        engine = WorkflowEngine("test-workflow")

        # 创建并行结构: node1 -> node2, node3
        node1 = MockNode("node1")
        node2 = MockNode("node2")
        node3 = MockNode("node3")

        engine.add_node(node1)
        engine.add_node(node2, dependencies=["node1"])
        engine.add_node(node3, dependencies=["node1"])

        # 执行工作流
        result = engine.execute("initial_input")

        assert result.status == WorkflowStatus.COMPLETED
        assert result.completed_nodes == 3

        # 验证所有节点都执行了
        assert node1.execute_called
        assert node2.execute_called
        assert node3.execute_called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])