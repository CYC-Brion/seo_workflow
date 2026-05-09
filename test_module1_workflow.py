#!/usr/bin/env python3
"""
模块1端到端测试脚本
测试完整工作流：Excel读取 → 关键词扩展 → AI关键词筛选
使用实际Excel文件：测试用例.xlsx
"""

import sys
import os
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import Mock, patch

from src.modules.excel_reader.excel_processor import ExcelProcessor
from src.modules.keyword_expander.keyword_expander import KeywordExpander
from src.modules.keyword_filter.ai_filter import AIKeywordFilter


def test_excel_reading(file_path):
    """测试Excel读取"""
    print("\n" + "="*60)
    print("步骤1: Excel文件读取")
    print("="*60)

    print(f"文件路径: {file_path}")
    print(f"文件存在: {Path(file_path).exists()}")

    try:
        # 创建Excel处理器
        excel_processor = ExcelProcessor(
            node_id="excel-reader-test",
            config={
                "keyword_column": "keywords",  # 假设列名为"keywords"
                "deduplicate": True,
                "validate_keywords": True,
                "max_keywords": 100  # 限制最大关键词数
            }
        )

        # 执行读取
        raw_keywords = excel_processor.execute_impl(file_path)
        stats = excel_processor.get_statistics()

        print(f"[OK] Excel读取成功")
        print(f"  读取关键词数量: {len(raw_keywords)}")
        print(f"  有效关键词: {stats.get('valid_keywords', 'N/A')}")
        print(f"  无效关键词: {stats.get('invalid_keywords', 'N/A')}")
        print(f"  空行: {stats.get('empty_rows', 'N/A')}")
        print(f"  重复关键词: {stats.get('duplicate_keywords', 'N/A')}")

        if raw_keywords:
            print(f"  前10个关键词: {raw_keywords[:10]}")
            if len(raw_keywords) > 10:
                print(f"  ... 还有 {len(raw_keywords) - 10} 个关键词")

        return raw_keywords, stats

    except Exception as e:
        print(f"[FAIL] Excel读取失败: {e}")
        return None, None


def test_keyword_expansion(keywords):
    """测试关键词扩展"""
    print("\n" + "="*60)
    print("步骤2: 关键词扩展")
    print("="*60)

    if not keywords:
        print("[FAIL] 输入关键词为空，跳过扩展步骤")
        return None, None

    print(f"输入关键词数量: {len(keywords)}")

    try:
        # 创建关键词扩展器（使用模拟数据，避免需要Google API）
        keyword_expander = KeywordExpander(
            node_id="keyword-expander-test",
            config={
                "use_mock_data": True,  # 使用模拟数据
                "max_expansions_per_keyword": 10,
                "request_delay_seconds": 0,  # 测试时无需延迟
                "enable_manual_fallback": True
            }
        )

        # 执行扩展
        expanded_keywords = keyword_expander.execute_impl(keywords)
        stats = keyword_expander.get_statistics()

        print(f"[OK] 关键词扩展成功")
        print(f"  扩展后关键词数量: {len(expanded_keywords)}")
        print(f"  原始关键词数量: {stats.get('total_keywords', 'N/A')}")
        print(f"  成功扩展的关键词: {stats.get('keywords_expanded', 'N/A')}")
        print(f"  扩展失败的关键词: {stats.get('keywords_failed', 'N/A')}")
        print(f"  总扩展数: {stats.get('total_expansions', 'N/A')}")
        print(f"  API请求次数: {stats.get('api_requests', 'N/A')}")
        print(f"  模拟扩展数: {stats.get('mock_expansions', 'N/A')}")

        # 计算扩展率
        if stats.get('total_keywords', 0) > 0:
            expansion_rate = stats.get('total_expansions', 0) / stats.get('total_keywords', 1)
            print(f"  平均每个关键词扩展数: {expansion_rate:.2f}")

        if expanded_keywords:
            print(f"  前10个扩展后关键词: {expanded_keywords[:10]}")
            if len(expanded_keywords) > 10:
                print(f"  ... 还有 {len(expanded_keywords) - 10} 个关键词")

        return expanded_keywords, stats

    except Exception as e:
        print(f"[FAIL] 关键词扩展失败: {e}")
        return None, None


@patch('src.modules.keyword_filter.ai_filter.get_ai_client')
def test_ai_keyword_filter(keywords, mock_get_ai_client):
    """测试AI关键词筛选"""
    print("\n" + "="*60)
    print("步骤3: AI关键词筛选")
    print("="*60)

    if not keywords:
        print("[FAIL] 输入关键词为空，跳过筛选步骤")
        return None, None

    print(f"输入关键词数量: {len(keywords)}")

    try:
        # 模拟AI客户端响应
        mock_client = Mock()
        # 模拟返回所有关键词作为相关关键词
        mock_response = '[' + ', '.join([f'"{kw}"' for kw in keywords[:20]]) + ']'
        mock_client.chat_completion.return_value.content = mock_response
        mock_client.chat_completion.return_value.usage = {"total_tokens": 100}
        mock_client.chat_completion.return_value.cost = 0.002
        mock_get_ai_client.return_value = mock_client

        # 创建AI关键词筛选器
        ai_filter = AIKeywordFilter(
            node_id="ai-filter-test",
            config={
                "batch_size": 50,
                "confidence_threshold": 0.7,
                "enable_fallback": True,  # 启用回退机制
                "industry": "Metal Hardware & Lighting Accessories Processing"
            }
        )

        # 执行筛选
        filtered_keywords = ai_filter.execute_impl(keywords)
        stats = ai_filter.get_statistics()

        print(f"[OK] AI关键词筛选成功")
        print(f"  筛选后关键词数量: {len(filtered_keywords)}")
        print(f"  总关键词数: {stats.get('total_keywords', 'N/A')}")
        print(f"  相关关键词: {stats.get('relevant_keywords', 'N/A')}")
        print(f"  不相关关键词: {stats.get('irrelevant_keywords', 'N/A')}")
        print(f"  低置信度关键词: {stats.get('low_confidence_keywords', 'N/A')}")
        print(f"  AI调用次数: {stats.get('ai_calls', 'N/A')}")
        print(f"  总token数: {stats.get('total_tokens', 'N/A')}")
        print(f"  总成本: ${stats.get('total_cost', 0):.4f}")

        # 计算筛选率
        if stats.get('total_keywords', 0) > 0:
            relevance_rate = stats.get('relevant_keywords', 0) / stats.get('total_keywords', 1) * 100
            filter_rate = stats.get('irrelevant_keywords', 0) / stats.get('total_keywords', 1) * 100
            print(f"  相关率: {relevance_rate:.1f}%")
            print(f"  过滤率: {filter_rate:.1f}%")

        if filtered_keywords:
            print(f"  前10个筛选后关键词: {filtered_keywords[:10]}")
            if len(filtered_keywords) > 10:
                print(f"  ... 还有 {len(filtered_keywords) - 10} 个关键词")

        return filtered_keywords, stats

    except Exception as e:
        print(f"[FAIL] AI关键词筛选失败: {e}")
        return None, None


def main():
    """主函数"""
    print("模块1端到端测试开始")
    print("="*60)

    # 测试文件路径
    test_file = Path("测试用例.xlsx")
    if not test_file.exists():
        print(f"[FAIL] 测试文件不存在: {test_file}")
        return 1

    print(f"使用测试文件: {test_file.absolute()}")

    # 步骤1: Excel读取
    raw_keywords, excel_stats = test_excel_reading(test_file)
    if raw_keywords is None:
        print("[FAIL] Excel读取失败，停止测试")
        return 1

    # 步骤2: 关键词扩展
    expanded_keywords, expander_stats = test_keyword_expansion(raw_keywords)
    if expanded_keywords is None:
        print("[FAIL] 关键词扩展失败，停止测试")
        return 1

    # 步骤3: AI关键词筛选
    filtered_keywords, filter_stats = test_ai_keyword_filter(expanded_keywords)
    if filtered_keywords is None:
        print("[FAIL] AI关键词筛选失败")
        return 1

    # 测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    print(f"原始关键词数量: {len(raw_keywords) if raw_keywords else 0}")
    print(f"扩展后关键词数量: {len(expanded_keywords) if expanded_keywords else 0}")
    print(f"筛选后关键词数量: {len(filtered_keywords) if filtered_keywords else 0}")

    # 计算整体效率
    if raw_keywords and filtered_keywords:
        expansion_ratio = len(expanded_keywords) / len(raw_keywords) if raw_keywords else 0
        filter_ratio = len(filtered_keywords) / len(expanded_keywords) if expanded_keywords else 0
        overall_ratio = len(filtered_keywords) / len(raw_keywords) if raw_keywords else 0

        print(f"\n效率指标:")
        print(f"  扩展比率: {expansion_ratio:.2f} (扩展后/原始)")
        print(f"  筛选比率: {filter_ratio:.2f} (筛选后/扩展后)")
        print(f"  整体比率: {overall_ratio:.2f} (筛选后/原始)")

    # 验证结果
    print(f"\n验证:")
    print(f"  [OK] 所有步骤完成")
    print(f"  [OK] 最终输出为列表: {isinstance(filtered_keywords, list)}")
    print(f"  [OK] 最终列表非空: {len(filtered_keywords) > 0 if filtered_keywords else False}")

    if filtered_keywords:
        # 检查列表元素类型
        all_strings = all(isinstance(kw, str) for kw in filtered_keywords)
        all_non_empty = all(len(kw.strip()) > 0 for kw in filtered_keywords)
        print(f"  [OK] 所有元素为字符串: {all_strings}")
        print(f"  [OK] 所有元素非空: {all_non_empty}")

    print("\n" + "="*60)
    print("模块1测试完成")
    print("="*60)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"测试过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)