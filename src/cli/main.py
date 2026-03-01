"""
SEO工作流系统命令行接口
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from src.utils import get_logger, config_manager
from src.modules import ExcelProcessor
from src.modules import AIKeywordFilter
from src.core import WorkflowEngine


logger = get_logger("cli")


def setup_parser() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="SEO内容自动化工作流系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s config check                    # 检查配置
  %(prog)s excel read keywords.xlsx        # 读取Excel关键词
  %(prog)s workflow run keywords.xlsx      # 运行完整工作流
  %(prog)s --help                          # 显示帮助信息
        """
    )

    # 全局参数
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="日志级别"
    )

    # 子命令
    subparsers = parser.add_subparsers(
        dest="command",
        title="可用命令",
        description="运行 '%(prog)s <command> --help' 获取命令详情"
    )

    # config 命令
    config_parser = subparsers.add_parser(
        "config",
        help="配置管理"
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    # config check
    config_check_parser = config_subparsers.add_parser(
        "check",
        help="检查配置状态"
    )
    config_check_parser.add_argument(
        "--test-api",
        action="store_true",
        help="测试API连接"
    )

    # config list
    config_list_parser = config_subparsers.add_parser(
        "list",
        help="列出配置信息"
    )
    config_list_parser.add_argument(
        "--format",
        choices=["json", "yaml", "table"],
        default="table",
        help="输出格式"
    )

    # excel 命令
    excel_parser = subparsers.add_parser(
        "excel",
        help="Excel文件处理"
    )
    excel_subparsers = excel_parser.add_subparsers(dest="excel_command")

    # excel read
    excel_read_parser = excel_subparsers.add_parser(
        "read",
        help="读取Excel文件中的关键词"
    )
    excel_read_parser.add_argument(
        "file",
        help="Excel文件路径"
    )
    excel_read_parser.add_argument(
        "-s", "--sheet",
        default=0,
        help="工作表名称或索引（默认: 0）"
    )
    excel_read_parser.add_argument(
        "-c", "--column",
        default="keywords",
        help="关键词列名（默认: 'keywords'）"
    )
    excel_read_parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认: 输出到控制台）"
    )
    excel_read_parser.add_argument(
        "--format",
        choices=["json", "csv", "txt"],
        default="txt",
        help="输出格式（默认: txt）"
    )

    # excel validate
    excel_validate_parser = excel_subparsers.add_parser(
        "validate",
        help="验证Excel文件"
    )
    excel_validate_parser.add_argument(
        "file",
        help="Excel文件路径"
    )

    # filter 命令
    filter_parser = subparsers.add_parser(
        "filter",
        help="AI关键词筛选"
    )
    filter_subparsers = filter_parser.add_subparsers(dest="filter_command")

    # filter run
    filter_run_parser = filter_subparsers.add_parser(
        "run",
        help="运行AI关键词筛选"
    )
    filter_run_parser.add_argument(
        "input",
        help="输入文件路径或关键词列表（JSON文件）"
    )
    filter_run_parser.add_argument(
        "-o", "--output",
        help="输出文件路径"
    )
    filter_run_parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=50,
        help="批量大小（默认: 50）"
    )
    filter_run_parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.7,
        help="置信度阈值（默认: 0.7）"
    )
    filter_run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行，不调用AI"
    )

    # filter stats
    filter_stats_parser = filter_subparsers.add_parser(
        "stats",
        help="显示筛选统计"
    )

    # workflow 命令
    workflow_parser = subparsers.add_parser(
        "workflow",
        help="工作流管理"
    )
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command")

    # workflow run
    workflow_run_parser = workflow_subparsers.add_parser(
        "run",
        help="运行工作流"
    )
    workflow_run_parser.add_argument(
        "input",
        help="输入文件路径"
    )
    workflow_run_parser.add_argument(
        "-o", "--output-dir",
        default="./output",
        help="输出目录（默认: ./output）"
    )
    workflow_run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行，不调用AI和外部API"
    )
    workflow_run_parser.add_argument(
        "--resume",
        help="从保存的状态恢复执行"
    )

    # workflow status
    workflow_status_parser = workflow_subparsers.add_parser(
        "status",
        help="查看工作流状态"
    )
    workflow_status_parser.add_argument(
        "workflow_id",
        nargs="?",
        help="工作流ID（如果未提供，显示所有工作流）"
    )

    # workflow list
    workflow_list_parser = workflow_subparsers.add_parser(
        "list",
        help="列出工作流"
    )

    # workflow cancel
    workflow_cancel_parser = workflow_subparsers.add_parser(
        "cancel",
        help="取消工作流"
    )
    workflow_cancel_parser.add_argument(
        "workflow_id",
        help="工作流ID"
    )

    # 工具命令
    tools_parser = subparsers.add_parser(
        "tools",
        help="工具函数"
    )
    tools_subparsers = tools_parser.add_subparsers(dest="tools_command")

    # tools version
    tools_version_parser = tools_subparsers.add_parser(
        "version",
        help="显示版本信息"
    )

    return parser


def handle_config(args: argparse.Namespace) -> int:
    """处理config命令"""
    if args.config_command == "check":
        return handle_config_check(args)
    elif args.config_command == "list":
        return handle_config_list(args)
    else:
        print("未知的config子命令")
        return 1


def handle_config_check(args: argparse.Namespace) -> int:
    """处理config check命令"""
    try:
        print("检查配置状态...")

        # 加载配置
        if not config_manager.load_all_configs():
            print("❌ 配置加载失败")
            return 1

        print("✅ 配置加载成功")

        # 检查API密钥
        api_status = config_manager.check_api_keys()
        print("\nAPI密钥状态:")
        for service, has_key in api_status.items():
            status = "✅" if has_key else "❌"
            print(f"  {service}: {status}")

        # 检查目录
        project_config = config_manager.project_config
        print("\n目录状态:")
        directories = [
            ("数据目录", project_config.data_dir),
            ("输入目录", project_config.input_dir),
            ("输出目录", project_config.output_dir),
            ("缓存目录", project_config.cache_dir),
            ("日志目录", project_config.logs_dir),
        ]

        for name, path in directories:
            if path.exists():
                print(f"  {name}: ✅ ({path})")
            else:
                print(f"  {name}: ❌ 不存在 ({path})")

        # 测试API连接（如果启用）
        if args.test_api:
            print("\n测试API连接...")
            # 这里可以添加实际的API测试
            print("  ⚠️ API测试功能尚未实现")

        print("\n配置检查完成")
        return 0

    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        logger.error("配置检查失败", exc_info=True)
        return 1


def handle_config_list(args: argparse.Namespace) -> int:
    """处理config list命令"""
    try:
        # 加载配置
        config_manager.load_all_configs()

        if args.format == "json":
            import json
            config_data = {
                "project": config_manager.project_config.__dict__,
                "ai_models": {
                    node: config.__dict__
                    for node, config in config_manager.ai_model_configs.items()
                },
                "wordpress": config_manager.wordpress_config.__dict__,
            }
            print(json.dumps(config_data, indent=2, default=str))
        else:
            # 表格格式
            print("项目配置:")
            print(f"  默认AI模型: {config_manager.project_config.default_ai_model}")
            print(f"  最大关键词批量: {config_manager.project_config.max_keywords_per_batch}")
            print(f"  文章字数: {config_manager.project_config.article_word_count}")

            print("\nAI模型配置:")
            for node_name, config in config_manager.ai_model_configs.items():
                print(f"  {node_name}: {config.provider} - {config.model}")

            print("\nWordPress配置:")
            wp_config = config_manager.wordpress_config
            print(f"  站点URL: {wp_config.url}")
            print(f"  用户名: {wp_config.username}")
            print(f"  默认状态: {wp_config.default_post_status}")

        return 0

    except Exception as e:
        print(f"❌ 列出配置失败: {e}")
        logger.error("列出配置失败", exc_info=True)
        return 1


def handle_excel(args: argparse.Namespace) -> int:
    """处理excel命令"""
    if args.excel_command == "read":
        return handle_excel_read(args)
    elif args.excel_command == "validate":
        return handle_excel_validate(args)
    else:
        print("未知的excel子命令")
        return 1


def handle_excel_read(args: argparse.Namespace) -> int:
    """处理excel read命令"""
    try:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return 1

        print(f"读取Excel文件: {file_path}")

        # 创建Excel处理器
        processor = ExcelProcessor(
            node_id="excel_cli",
            config={
                "sheet_name": args.sheet,
                "keyword_column": args.column,
            }
        )

        # 读取关键词
        keywords = processor.execute_impl(file_path)
        stats = processor.get_statistics()

        print(f"✅ 读取完成，共 {len(keywords)} 个关键词")
        print(f"  总行数: {stats['total_rows']}")
        print(f"  有效关键词: {stats['valid_keywords']}")
        print(f"  无效关键词: {stats['invalid_keywords']}")
        print(f"  重复关键词: {stats['duplicate_keywords']}")

        # 输出结果
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if args.format == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(keywords, f, ensure_ascii=False, indent=2)
            elif args.format == "csv":
                import csv
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["keyword"])
                    for kw in keywords:
                        writer.writerow([kw])
            else:  # txt
                with open(output_path, 'w', encoding='utf-8') as f:
                    for kw in keywords:
                        f.write(f"{kw}\n")

            print(f"结果已保存到: {output_path}")
        else:
            # 输出到控制台
            print("\n关键词列表:")
            for i, kw in enumerate(keywords[:20], 1):  # 只显示前20个
                print(f"  {i}. {kw}")
            if len(keywords) > 20:
                print(f"  ... 还有 {len(keywords) - 20} 个关键词")

        return 0

    except Exception as e:
        print(f"❌ 读取Excel失败: {e}")
        logger.error("读取Excel失败", exc_info=True)
        return 1


def handle_excel_validate(args: argparse.Namespace) -> int:
    """处理excel validate命令"""
    try:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return 1

        print(f"验证Excel文件: {file_path}")

        # 创建Excel处理器
        processor = ExcelProcessor(
            node_id="excel_validate_cli",
            config={}
        )

        # 验证文件
        is_valid = processor.validate_input(file_path)

        if is_valid:
            print("✅ 文件验证通过")
            return 0
        else:
            print("❌ 文件验证失败")
            return 1

    except Exception as e:
        print(f"❌ 验证Excel失败: {e}")
        logger.error("验证Excel失败", exc_info=True)
        return 1


def handle_filter(args: argparse.Namespace) -> int:
    """处理filter命令"""
    if args.filter_command == "run":
        return handle_filter_run(args)
    elif args.filter_command == "stats":
        return handle_filter_stats(args)
    else:
        print("未知的filter子命令")
        return 1


def handle_filter_run(args: argparse.Namespace) -> int:
    """处理filter run命令"""
    try:
        input_path = Path(args.input)
        keywords = []

        # 加载输入数据
        if input_path.exists() and input_path.suffix.lower() == '.json':
            with open(input_path, 'r', encoding='utf-8') as f:
                keywords = json.load(f)
        elif input_path.exists():
            # 尝试作为文本文件读取
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('[') and content.endswith(']'):
                    keywords = json.loads(content)
                else:
                    keywords = [line.strip() for line in content.split('\n') if line.strip()]
        else:
            # 直接作为关键词字符串
            if args.input.startswith('[') and args.input.endswith(']'):
                keywords = json.loads(args.input)
            else:
                keywords = [args.input]

        print(f"开始AI关键词筛选，共 {len(keywords)} 个关键词")
        print(f"批量大小: {args.batch_size}, 置信度阈值: {args.threshold}")

        if args.dry_run:
            print("试运行模式，跳过AI调用")
            print(f"将处理 {len(keywords)} 个关键词")
            return 0

        # 创建筛选器
        filter_node = AIKeywordFilter(
            node_id="filter_cli",
            config={
                "batch_size": args.batch_size,
                "confidence_threshold": args.threshold,
            }
        )

        # 执行筛选
        filtered_keywords = filter_node.execute_impl(keywords)
        stats = filter_node.get_statistics()

        print(f"✅ 筛选完成")
        print(f"  原始关键词: {stats['total_keywords']}")
        print(f"  相关关键词: {stats['relevant_keywords']}")
        print(f"  不相关关键词: {stats['irrelevant_keywords']}")
        print(f"  低置信度关键词: {stats['low_confidence_keywords']}")
        print(f"  AI调用次数: {stats['ai_calls']}")
        print(f"  总Tokens: {stats['total_tokens']}")
        print(f"  总成本: ${stats['total_cost']:.4f}")
        print(f"  最终关键词: {len(filtered_keywords)}")

        # 输出结果
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_keywords, f, ensure_ascii=False, indent=2)

            print(f"结果已保存到: {output_path}")
        else:
            # 输出到控制台
            print("\n筛选后的关键词:")
            for i, kw in enumerate(filtered_keywords[:20], 1):
                print(f"  {i}. {kw}")
            if len(filtered_keywords) > 20:
                print(f"  ... 还有 {len(filtered_keywords) - 20} 个关键词")

        return 0

    except Exception as e:
        print(f"❌ AI关键词筛选失败: {e}")
        logger.error("AI关键词筛选失败", exc_info=True)
        return 1


def handle_filter_stats(args: argparse.Namespace) -> int:
    """处理filter stats命令"""
    print("筛选统计功能尚未实现")
    return 0


def handle_workflow(args: argparse.Namespace) -> int:
    """处理workflow命令"""
    if args.workflow_command == "run":
        return handle_workflow_run(args)
    elif args.workflow_command == "status":
        return handle_workflow_status(args)
    elif args.workflow_command == "list":
        return handle_workflow_list(args)
    elif args.workflow_command == "cancel":
        return handle_workflow_cancel(args)
    else:
        print("未知的workflow子命令")
        return 1


def handle_workflow_run(args: argparse.Namespace) -> int:
    """处理workflow run命令"""
    try:
        print("运行工作流...")
        print("⚠️ 工作流运行功能尚未完全实现")

        # 这里可以添加实际的工作流执行逻辑
        # 目前只演示基本流程

        if args.dry_run:
            print("试运行模式，跳过实际执行")
            return 0

        # 创建简单的工作流示例
        workflow = WorkflowEngine("seo-workflow-cli")

        # 这里可以添加实际的工作流节点
        # 目前只是演示

        print(f"工作流创建成功: {workflow.workflow_id}")
        print("使用 'seo-workflow workflow status' 查看状态")

        return 0

    except Exception as e:
        print(f"❌ 工作流运行失败: {e}")
        logger.error("工作流运行失败", exc_info=True)
        return 1


def handle_workflow_status(args: argparse.Namespace) -> int:
    """处理workflow status命令"""
    print("工作流状态功能尚未实现")
    return 0


def handle_workflow_list(args: argparse.Namespace) -> int:
    """处理workflow list命令"""
    print("工作流列表功能尚未实现")
    return 0


def handle_workflow_cancel(args: argparse.Namespace) -> int:
    """处理workflow cancel命令"""
    print("工作流取消功能尚未实现")
    return 0


def handle_tools(args: argparse.Namespace) -> int:
    """处理tools命令"""
    if args.tools_command == "version":
        return handle_tools_version(args)
    else:
        print("未知的tools子命令")
        return 1


def handle_tools_version(args: argparse.Namespace) -> int:
    """处理tools version命令"""
    try:
        # 从pyproject.toml读取版本信息
        import toml
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                pyproject = toml.load(f)
                version = pyproject.get('project', {}).get('version', '未知')
                name = pyproject.get('project', {}).get('name', 'seo-content-automation')
                description = pyproject.get('project', {}).get('description', '')

                print(f"{name} v{version}")
                print(description)
        else:
            print("SEO内容自动化工作流系统 v0.1.0")

        return 0
    except Exception:
        print("SEO内容自动化工作流系统 v0.1.0")
        return 0


def main(argv: Optional[list] = None) -> int:
    """CLI主入口点"""
    parser = setup_parser()
    args = parser.parse_args(argv)

    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 设置日志级别
    logger.level = args.log_level

    try:
        # 根据命令分发处理
        if args.command == "config":
            return handle_config(args)
        elif args.command == "excel":
            return handle_excel(args)
        elif args.command == "filter":
            return handle_filter(args)
        elif args.command == "workflow":
            return handle_workflow(args)
        elif args.command == "tools":
            return handle_tools(args)
        else:
            print(f"未知命令: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 130
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())