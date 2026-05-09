#!/usr/bin/env python3
"""
获取测试中扩展后的所有关键词
"""

import sys
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.modules.excel_reader.excel_processor import ExcelProcessor
from src.modules.keyword_expander.keyword_expander import KeywordExpander
from src.modules.keyword_filter.ai_filter import AIKeywordFilter
from unittest.mock import Mock, patch

def get_all_keywords():
    """获取所有扩展后的关键词"""
    print("获取扩展后的所有关键词...")
    print("="*60)

    # 测试文件路径
    test_file = Path("测试用例.xlsx")
    if not test_file.exists():
        print(f"[FAIL] 测试文件不存在: {test_file}")
        return

    print(f"使用测试文件: {test_file.absolute()}")

    # 步骤1: Excel读取
    try:
        excel_processor = ExcelProcessor(
            node_id="excel-reader-test",
            config={
                "keyword_column": "keywords",  # 假设列名为"keywords"
                "deduplicate": True,
                "validate_keywords": True,
                "max_keywords": 100
            }
        )
        raw_keywords = excel_processor.execute_impl(test_file)
        stats = excel_processor.get_statistics()
        print(f"Excel读取成功: {len(raw_keywords)} 个原始关键词")
        print(f"原始关键词: {raw_keywords}")
    except Exception as e:
        print(f"Excel读取失败: {e}")
        return

    # 步骤2: 关键词扩展
    try:
        keyword_expander = KeywordExpander(
            node_id="keyword-expander-test",
            config={
                "use_mock_data": True,  # 使用模拟数据
                "max_expansions_per_keyword": 10,
                "request_delay_seconds": 0,
                "enable_manual_fallback": True
            }
        )
        expanded_keywords = keyword_expander.execute_impl(raw_keywords)
        stats = keyword_expander.get_statistics()
        print(f"\n关键词扩展成功: {len(expanded_keywords)} 个扩展后关键词")
        print(f"原始关键词数量: {stats.get('total_keywords', 'N/A')}")
        print(f"成功扩展的关键词: {stats.get('keywords_expanded', 'N/A')}")
        print(f"总扩展数: {stats.get('total_expansions', 'N/A')}")
    except Exception as e:
        print(f"关键词扩展失败: {e}")
        return

    # 输出所有扩展后的关键词
    print(f"\n所有扩展后关键词 (共 {len(expanded_keywords)} 个):")
    print("="*60)

    # 按原始关键词分组显示
    keyword_sources = {}
    # 重建关键词来源（从扩展器内部逻辑推断）
    # 首先找出原始关键词
    original_keywords = raw_keywords.copy()

    # 尝试识别扩展关键词的来源
    for original_kw in original_keywords:
        related_keywords = [kw for kw in expanded_keywords if original_kw.lower() in kw.lower() or kw.lower().startswith(original_kw.lower())]
        keyword_sources[original_kw] = related_keywords

    # 显示分组
    for i, (original, expansions) in enumerate(keyword_sources.items()):
        print(f"\n{original}:")
        print("-" * 40)
        for j, kw in enumerate(expansions, 1):
            print(f"  {j}. {kw}")

    # 显示完整列表
    print(f"\n完整关键词列表:")
    print("-" * 40)
    for i, kw in enumerate(expanded_keywords, 1):
        print(f"{i:2d}. {kw}")

    print(f"\n总计: {len(expanded_keywords)} 个关键词")

    # 步骤3: AI关键词筛选
    print(f"\n" + "="*60)
    print("AI关键词筛选结果:")
    print("="*60)

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def run_ai_filter(mock_get_ai_client):
        try:
            # 模拟AI客户端响应
            mock_client = Mock()
            mock_response = '[' + ', '.join([f'"{kw}"' for kw in expanded_keywords[:20]]) + ']'
            mock_client.chat_completion.return_value.content = mock_response
            mock_client.chat_completion.return_value.usage = {"total_tokens": 100}
            mock_client.chat_completion.return_value.cost = 0.002
            mock_get_ai_client.return_value = mock_client

            ai_filter = AIKeywordFilter(
                node_id="ai-filter-test",
                config={
                    "batch_size": 50,
                    "confidence_threshold": 0.7,
                    "enable_fallback": True,
                    "industry": "Metal Hardware & Lighting Accessories Processing"
                }
            )

            filtered_keywords = ai_filter.execute_impl(expanded_keywords)
            stats = ai_filter.get_statistics()

            print(f"AI筛选成功: {len(filtered_keywords)} 个筛选后关键词")
            print(f"相关关键词: {stats.get('relevant_keywords', 'N/A')}")
            print(f"不相关关键词: {stats.get('irrelevant_keywords', 'N/A')}")

            print(f"\n筛选后关键词列表 (共 {len(filtered_keywords)} 个):")
            print("-" * 40)
            for i, kw in enumerate(filtered_keywords, 1):
                print(f"{i:2d}. {kw}")

        except Exception as e:
            print(f"AI筛选失败: {e}")

    run_ai_filter()

if __name__ == "__main__":
    get_all_keywords()