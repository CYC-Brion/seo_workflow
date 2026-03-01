#!/usr/bin/env python3
"""
测试项目导入
验证所有模块是否可以正常导入
"""

import sys
import traceback

def test_import(module_name: str, import_statement: str) -> bool:
    """测试导入单个模块"""
    try:
        exec(import_statement)
        print(f"[PASS] {module_name}")
        return True
    except Exception as e:
        print(f"[FAIL] {module_name}: {e}")
        if "verbose" in sys.argv:
            traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("测试项目导入...")
    print("=" * 60)

    # 测试列表
    tests = [
        ("utils.logger", "from src.utils.logger import get_logger, logger"),
        ("utils.config_loader", "from src.utils.config_loader import config_manager, get_config"),
        ("utils.exception_handler", "from src.utils.exception_handler import exception_handler, WorkflowException"),
        ("utils.ai_client", "from src.utils.ai_client import get_ai_client, AIProvider"),

        ("core.base_node", "from src.core.base_node import BaseNode, NodeStatus"),
        ("core.workflow_engine", "from src.core.workflow_engine import WorkflowEngine, WorkflowStatus"),
        ("core.state_manager", "from src.core.state_manager import state_manager, WorkflowState"),
        ("core.task_scheduler", "from src.core.task_scheduler import task_scheduler"),

        ("modules.excel_reader", "from src.modules.excel_reader import ExcelProcessor"),
        ("modules.keyword_filter", "from src.modules.keyword_filter import AIKeywordFilter"),

        ("cli.main", "from src.cli.main import main"),
    ]

    results = []
    for module_name, import_stmt in tests:
        success = test_import(module_name, import_stmt)
        results.append((module_name, success))

    print("=" * 60)

    # 统计结果
    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed

    print(f"总计: {total}, 通过: {passed}, 失败: {failed}")

    if failed > 0:
        print("\n失败的模块:")
        for module_name, success in results:
            if not success:
                print(f"  - {module_name}")

    # 测试配置加载
    print("\n" + "=" * 60)
    print("测试配置加载...")
    try:
        from src.utils.config_loader import config_manager
        success = config_manager.load_all_configs()
        if success:
            print("[PASS] 配置加载成功")
            print(f"   项目名称: {config_manager.project_config.default_ai_model}")
            print(f"   AI模型数量: {len(config_manager.ai_model_configs)}")
        else:
            print("[FAIL] 配置加载失败")
    except Exception as e:
        print(f"[FAIL] 配置加载测试失败: {e}")
        if "verbose" in sys.argv:
            traceback.print_exc()

    # 测试工作流引擎创建
    print("\n" + "=" * 60)
    print("测试工作流引擎...")
    try:
        from src.core.workflow_engine import WorkflowEngine
        workflow = WorkflowEngine("test-workflow")
        print(f"[PASS] 工作流引擎创建成功: {workflow.workflow_id}")
    except Exception as e:
        print(f"[FAIL] 工作流引擎测试失败: {e}")
        if "verbose" in sys.argv:
            traceback.print_exc()

    # 测试节点创建
    print("\n" + "=" * 60)
    print("测试节点创建...")
    try:
        from src.modules.excel_reader import ExcelProcessor
        from src.modules.keyword_filter import AIKeywordFilter

        excel_node = ExcelProcessor("test-excel")
        print(f"[PASS] Excel处理器创建成功: {excel_node.node_id}")

        filter_node = AIKeywordFilter("test-filter")
        print(f"[PASS] AI筛选器创建成功: {filter_node.node_id}")
    except Exception as e:
        print(f"[FAIL] 节点创建测试失败: {e}")
        if "verbose" in sys.argv:
            traceback.print_exc()

    print("\n" + "=" * 60)
    if failed == 0:
        print("[SUCCESS] 所有导入测试通过！")
        return 0
    else:
        print("[WARNING]  部分导入测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())