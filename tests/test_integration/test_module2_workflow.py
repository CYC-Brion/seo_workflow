"""
模块二工作流集成测试
测试完整工作流：关键词 → 标题生成 → 内容生成
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from unittest.mock import Mock, patch

from src.modules.excel_reader.excel_processor import ExcelProcessor
from src.modules.title_generator.ai_title_generator import AITitleGenerator
from src.modules.content_generator.ai_content_generator import AIContentGenerator


class TestModule2Workflow:
    """模块二工作流集成测试类"""

    def create_test_excel_file(self, keywords: list) -> Path:
        """创建测试Excel文件"""
        data = {"keywords": keywords}
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = Path(f.name)
            df.to_excel(temp_path, index=False)
            return temp_path

    @patch('src.modules.title_generator.ai_title_generator.get_ai_client')
    @patch('src.modules.content_generator.ai_content_generator.get_ai_client')
    def test_module2_workflow_with_mock_data(self, mock_get_content_client, mock_get_title_client):
        """测试使用模拟数据的模块二完整工作流"""
        print("\n" + "="*60)
        print("模块二集成测试：关键词 → 标题 → 内容")
        print("="*60)

        # 1. 模拟标题生成AI客户端响应
        mock_title_client = Mock()
        # 为不同关键词返回不同的标题响应
        title_responses = {
            "hardware": '["Complete Guide to Hardware", "Professional Hardware Solutions"]',
            "Lighting accessories": '["Lighting Accessories: Everything You Need to Know", "Advanced Lighting Accessories Guide"]',
            "lamp holder": '["Lamp Holder Installation Guide", "Choosing the Right Lamp Holder"]'
        }

        def title_chat_completion_side_effect(messages, **kwargs):
            # 从消息中提取关键词
            import re
            user_message = messages[1].content if len(messages) > 1 else ""
            keyword_match = re.search(r"keyword:\s*'([^']+)'", user_message)
            if keyword_match:
                keyword = keyword_match.group(1)
                response_content = title_responses.get(keyword, '["Default Title"]')
            else:
                response_content = '["Default Title"]'

            mock_response = Mock()
            mock_response.content = response_content
            mock_response.usage = {"total_tokens": 50}
            mock_response.cost = 0.005
            return mock_response

        mock_title_client.chat_completion.side_effect = title_chat_completion_side_effect
        mock_get_title_client.return_value = mock_title_client

        # 2. 模拟内容生成AI客户端响应
        mock_content_client = Mock()
        # 为不同标题返回不同的内容响应
        content_responses = {
            "Complete Guide to Hardware": '<article><h1>Complete Guide to Hardware</h1><p>This is a comprehensive guide about hardware in the metal industry.</p></article>',
            "Lighting Accessories: Everything You Need to Know": '<article><h1>Lighting Accessories: Everything You Need to Know</h1><p>Detailed information about lighting accessories.</p></article>',
            "Lamp Holder Installation Guide": '<article><h1>Lamp Holder Installation Guide</h1><p>Step-by-step guide for lamp holder installation.</p></article>'
        }

        def content_chat_completion_side_effect(messages, **kwargs):
            # 从消息中提取标题
            import re
            user_message = messages[1].content if len(messages) > 1 else ""
            title_match = re.search(r"title:\s*'([^']+)'", user_message)
            if title_match:
                title = title_match.group(1)
                response_content = content_responses.get(title, '<article><h1>Default Article</h1><p>Default content.</p></article>')
            else:
                response_content = '<article><h1>Default Article</h1><p>Default content.</p></article>'

            mock_response = Mock()
            mock_response.content = response_content
            mock_response.usage = {"total_tokens": 200}
            mock_response.cost = 0.02
            return mock_response

        mock_content_client.chat_completion.side_effect = content_chat_completion_side_effect
        mock_get_content_client.return_value = mock_content_client

        # 3. 创建测试Excel文件（使用实际测试用例文件路径）
        test_excel_path = Path("D:/工作流项目/测试用例.xlsx")
        if not test_excel_path.exists():
            # 如果实际文件不存在，创建临时测试文件
            test_keywords = ["hardware", "Lighting accessories", "lamp holder"]
            test_excel_path = self.create_test_excel_file(test_keywords)
            use_temp_file = True
        else:
            use_temp_file = False
            print(f"使用实际测试用例文件: {test_excel_path}")

        try:
            # 4. Excel读取节点（如果需要）
            print("\n=== 步骤1: Excel读取 ===")
            excel_processor = ExcelProcessor("excel-reader", {
                "keyword_column": "keywords",
                "deduplicate": False,
                "validate_keywords": False
            })

            raw_keywords = excel_processor.execute_impl(str(test_excel_path))
            print(f"读取关键词: {raw_keywords}")
            print(f"读取统计: {excel_processor.get_statistics()}")

            # 验证Excel读取结果
            assert isinstance(raw_keywords, list)
            assert len(raw_keywords) > 0
            print(f"[OK] Excel读取成功，获得 {len(raw_keywords)} 个关键词")

            # 5. 标题生成节点
            print("\n=== 步骤2: 标题生成 ===")
            title_generator = AITitleGenerator("title-generator", {
                "batch_size": 3,
                "max_titles_per_keyword": 2,
                "enable_fallback": False
            })


            generated_titles = title_generator.execute_impl(raw_keywords)
            print(f"生成的标题: {generated_titles}")
            print(f"标题生成统计: {title_generator.get_statistics()}")

            # 验证标题生成结果
            assert isinstance(generated_titles, list)
            assert len(generated_titles) >= len(raw_keywords)  # 至少每个关键词一个标题
            print(f"[OK] 标题生成成功，获得 {len(generated_titles)} 个标题")

            # 6. 准备内容生成输入（需要关键词和标题的对应关系）
            print("\n=== 步骤3: 准备内容生成输入 ===")
            # 由于title_generator返回标题列表但不直接映射到关键词，
            # 我们假设每个标题对应原始关键词列表中的对应位置
            # 在实际应用中，可能需要更复杂的映射逻辑
            content_inputs = []
            for i, title in enumerate(generated_titles):
                if i < len(raw_keywords):
                    keyword = raw_keywords[i]
                else:
                    # 如果标题比关键词多，使用最后一个关键词
                    keyword = raw_keywords[-1]
                content_inputs.append({"keyword": keyword, "title": title})

            print(f"内容生成输入: {content_inputs}")

            # 7. 内容生成节点
            print("\n=== 步骤4: 内容生成 ===")
            content_generator = AIContentGenerator("content-generator", {
                "batch_size": 3,
                "target_word_count": 800,  # 测试时使用较小的字数
                "html_format": True,
                "enable_fallback": False
            })


            generated_contents = content_generator.execute_impl(content_inputs)
            print(f"生成的内容数量: {len(generated_contents)}")
            print(f"内容生成统计: {content_generator.get_statistics()}")

            # 显示第一个内容的预览
            if generated_contents:
                first_content_preview = generated_contents[0][:200] + "..." if len(generated_contents[0]) > 200 else generated_contents[0]
                print(f"第一个内容预览: {first_content_preview}")

            # 验证内容生成结果
            assert isinstance(generated_contents, list)
            assert len(generated_contents) == len(content_inputs)  # 应该为每个输入生成内容
            print(f"[OK] 内容生成成功，获得 {len(generated_contents)} 个内容")

            # 8. 整体验证
            print("\n=== 步骤5: 整体验证 ===")

            # 验证所有内容都是有效的HTML/文本
            for i, content in enumerate(generated_contents):
                assert isinstance(content, str)
                assert len(content.strip()) > 0
                # 检查是否包含基本的HTML结构（如果启用HTML格式）
                if content_generator.html_format:
                    assert "<" in content and ">" in content
                print(f"  内容 {i+1}: {len(content)} 字符")

            # 计算整体统计
            total_keywords = len(raw_keywords)
            total_titles = len(generated_titles)
            total_contents = len(generated_contents)

            print(f"\n=== 集成测试结果 ===")
            print(f"原始关键词: {total_keywords}")
            print(f"生成标题: {total_titles}")
            print(f"生成内容: {total_contents}")
            print(f"标题/关键词比率: {total_titles/total_keywords:.2f}")
            print(f"内容/标题比率: {total_contents/total_titles:.2f}")

            # 最终验证
            assert total_keywords > 0
            assert total_titles >= total_keywords
            assert total_contents == total_titles

            print("[OK] 模块二集成测试通过！")
            print("="*60)

        finally:
            # 清理临时文件
            if use_temp_file and test_excel_path.exists():
                os.unlink(test_excel_path)
                print(f"已删除临时文件: {test_excel_path}")

    def test_module2_with_default_titles(self):
        """测试使用默认标题的模块二工作流（不使用AI模拟）"""
        print("\n" + "="*60)
        print("模块二集成测试：使用默认标题和内容")
        print("="*60)

        # 使用简单的测试关键词
        test_keywords = ["hardware", "lighting fixtures"]

        print("\n=== 步骤1: 标题生成（使用默认标题） ===")
        title_generator = AITitleGenerator("title-generator-test", {
            "batch_size": 2,
            "enable_fallback": False
        })

        # 不设置AI客户端，使其使用默认标题
        titles = title_generator.execute_impl(test_keywords)
        print(f"生成的默认标题: {titles}")

        assert isinstance(titles, list)
        assert len(titles) == len(test_keywords)
        print(f"[OK] 默认标题生成成功")

        print("\n=== 步骤2: 准备内容生成输入 ===")
        content_inputs = []
        for i, title in enumerate(titles):
            keyword = test_keywords[i] if i < len(test_keywords) else test_keywords[-1]
            content_inputs.append({"keyword": keyword, "title": title})

        print(f"内容生成输入: {content_inputs}")

        print("\n=== 步骤3: 内容生成（使用默认内容） ===")
        content_generator = AIContentGenerator("content-generator-test", {
            "batch_size": 2,
            "target_word_count": 500,
            "html_format": True,
            "enable_fallback": False
        })

        # 不设置AI客户端，使其使用默认内容
        contents = content_generator.execute_impl(content_inputs)
        print(f"生成的默认内容数量: {len(contents)}")

        # 显示内容预览
        if contents:
            for i, content in enumerate(contents[:2]):  # 只显示前两个
                preview = content[:150] + "..." if len(content) > 150 else content
                print(f"  内容 {i+1} 预览: {preview}")

        assert isinstance(contents, list)
        assert len(contents) == len(content_inputs)
        print(f"[OK] 默认内容生成成功")

        # 验证内容格式
        for content in contents:
            assert isinstance(content, str)
            assert len(content.strip()) > 0
            # 默认内容应该包含HTML标签
            assert "<" in content and ">" in content

        print("\n=== 测试结果 ===")
        print(f"测试关键词: {len(test_keywords)}")
        print(f"生成标题: {len(titles)}")
        print(f"生成内容: {len(contents)}")
        print("[OK] 默认内容测试通过！")
        print("="*60)


if __name__ == "__main__":
    """命令行运行测试"""
    import sys

    print("运行模块二集成测试...")
    tester = TestModule2Workflow()

    try:
        # 运行第一个测试（需要模拟AI客户端）
        print("\n运行测试1: 使用模拟AI客户端")
        tester.test_module2_workflow_with_mock_data()

        # 运行第二个测试（使用默认内容）
        print("\n运行测试2: 使用默认标题和内容")
        tester.test_module2_with_default_titles()

        print("\n所有测试通过！")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n测试发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)