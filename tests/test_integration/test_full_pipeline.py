"""
完整端到端集成测试
Excel → 关键词扩展 → AI筛选 → 标题生成 → 内容生成 → WordPress发布
所有 AI 客户端和 WordPress 客户端均使用 Mock，无需真实 API 密钥。
"""
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pandas as pd

from src.modules.excel_reader.excel_processor import ExcelProcessor
from src.modules.keyword_expander.keyword_expander import KeywordExpander
from src.modules.keyword_filter.ai_filter import AIKeywordFilter
from src.modules.title_generator.ai_title_generator import AITitleGenerator
from src.modules.content_generator.ai_content_generator import AIContentGenerator
from src.modules.wordpress_integration.wordpress_publisher import WordPressPublisher


class TestFullPipeline:
    """完整6节点端到端管线测试"""

    @staticmethod
    def create_test_excel(keywords: list) -> Path:
        """创建临时测试 Excel 文件"""
        df = pd.DataFrame({"keywords": keywords})
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp_path = Path(tmp.name)
        df.to_excel(tmp_path, index=False)
        tmp.close()
        return tmp_path

    @staticmethod
    def _setup_mock_ai_filter():
        """Mock AIKeywordFilter 的 AI 客户端"""
        mock_client = Mock()
        mock_client.chat_completion.return_value = Mock(
            content='["metal hardware manufacturers", "lighting accessories suppliers", '
                    '"hardware processing services", "custom metal parts", '
                    '"precision lighting components"]',
            usage={"total_tokens": 100},
            cost=0.002,
        )
        return mock_client

    @staticmethod
    def _setup_mock_ai_titles():
        """Mock AITitleGenerator 的 AI 客户端"""
        mock_client = Mock()

        def title_side_effect(messages, **kwargs):
            user_msg = messages[1].content if len(messages) > 1 else ""
            import re
            kws = re.findall(r"'([^']+)'", user_msg)
            titles = [f"Complete Guide to {kw}" for kw in kws] if kws else ["Default SEO Title"]
            return Mock(
                content=json.dumps(titles),
                usage={"total_tokens": 50},
                cost=0.005,
            )

        mock_client.chat_completion.side_effect = title_side_effect
        return mock_client

    @staticmethod
    def _setup_mock_ai_content():
        """Mock AIContentGenerator 的 AI 客户端"""
        mock_client = Mock()

        def content_side_effect(messages, **kwargs):
            user_msg = messages[1].content if len(messages) > 1 else ""
            import re
            title_match = re.search(r'title:\s*"([^"]+)"', user_msg)
            kw_match = re.search(r'keyword:\s*"([^"]+)"', user_msg)
            title = title_match.group(1) if title_match else "Default Title"
            kw = kw_match.group(1) if kw_match else "default"

            html_content = (
                f"<article><h2>{title}</h2>"
                f"<p>This is a comprehensive article about {kw}. "
                f"It covers everything you need to know about {kw} in the industry.</p>"
                f"<h3>Key Features</h3>"
                f"<ul><li>Quality {kw} products</li><li>Professional service</li></ul>"
                f"<p>Contact us for more information about {kw}.</p></article>"
            )
            return Mock(
                content=json.dumps({
                    "title": title,
                    "keyword": kw,
                    "content": html_content,
                    "slug": kw.replace(" ", "-").lower(),
                    "excerpt": f"Learn about {kw} in this comprehensive guide."
                }),
                usage={"total_tokens": 300},
                cost=0.03,
            )

        mock_client.chat_completion.side_effect = content_side_effect
        return mock_client

    @staticmethod
    def _setup_mock_wp_client():
        """Mock WordPress 客户端"""
        mock_wp = Mock()
        mock_wp.test_connection.return_value = True

        post_id_counter = [1000]

        def create_post_side_effect(post_data):
            post_id_counter[0] += 1
            return {
                "id": post_id_counter[0],
                "link": f"https://example.com/?p={post_id_counter[0]}",
                "date": "2026-05-04T12:00:00",
                "status": "draft",
            }

        mock_wp.create_post.side_effect = create_post_side_effect
        mock_wp.upload_media.return_value = {"id": 500, "url": "https://example.com/wp-content/uploads/img.jpg"}
        return mock_wp

    @patch("src.modules.keyword_filter.ai_filter.get_ai_client")
    @patch("src.modules.title_generator.ai_title_generator.get_ai_client")
    @patch("src.modules.content_generator.ai_content_generator.get_ai_client")
    @patch("src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client")
    def test_full_pipeline_with_mocks(
        self, mock_get_wp, mock_get_content_ai, mock_get_title_ai, mock_get_filter_ai
    ):
        """测试完整6节点管线（Mock AI + Mock WP）"""
        print("\n" + "=" * 60)
        print("端到端测试: Excel → Keywords → Filter → Titles → Content → WP")
        print("=" * 60)

        # 设置 Mock
        mock_get_filter_ai.return_value = self._setup_mock_ai_filter()
        mock_get_title_ai.return_value = self._setup_mock_ai_titles()
        mock_get_content_ai.return_value = self._setup_mock_ai_content()
        mock_get_wp.return_value = self._setup_mock_wp_client()

        # 创建测试 Excel
        test_keywords = ["metal hardware", "lighting accessories", "hardware processing"]
        excel_path = self.create_test_excel(test_keywords)
        print(f"创建测试 Excel: {excel_path}, 关键词: {test_keywords}")

        try:
            # === 节点1: Excel 读取 ===
            print("\n[1/6] Excel 读取...")
            excel = ExcelProcessor("excel_reader", config={
                "keyword_column": "keywords", "deduplicate": True, "validate_keywords": False,
            })
            result = excel.execute(str(excel_path))
            assert result.status.value == "completed", f"Excel读取失败: {result.error_message}"
            keywords = result.output_data
            assert isinstance(keywords, list)
            assert len(keywords) == 3
            print(f"  ✅ {len(keywords)} 个关键词: {keywords}")

            # === 节点2: 关键词扩展 ===
            print("\n[2/6] 关键词扩展...")
            expander = KeywordExpander("keyword_expander", config={
                "use_mock_data": True, "max_expansions_per_keyword": 5,
            })
            result = expander.execute(keywords)
            assert result.status.value == "completed"
            expanded = result.output_data
            assert isinstance(expanded, list)
            assert len(expanded) > len(keywords), f"扩展后应多于原始: {len(expanded)} <= {len(keywords)}"
            print(f"  ✅ {len(keywords)} → {len(expanded)} 个关键词")

            # === 节点3: AI 关键词筛选 ===
            print("\n[3/6] AI 关键词筛选...")
            ai_filter = AIKeywordFilter("keyword_filter", config={
                "batch_size": 50, "confidence_threshold": 0.7, "enable_fallback": True,
            })
            result = ai_filter.execute(expanded)
            assert result.status.value == "completed"
            filtered = result.output_data
            assert isinstance(filtered, list)
            assert len(filtered) > 0
            print(f"  ✅ {len(expanded)} → {len(filtered)} 个关键词")

            # === 节点4: AI 标题生成 ===
            print("\n[4/6] AI 标题生成...")
            title_gen = AITitleGenerator("title_generator", config={
                "batch_size": 10, "max_titles_per_keyword": 1, "enable_fallback": True,
            })
            result = title_gen.execute(filtered)
            assert result.status.value == "completed"
            titles = result.output_data
            assert isinstance(titles, list)
            assert len(titles) >= len(filtered)
            print(f"  ✅ 生成 {len(titles)} 个标题, 预览: {titles[0][:60]}...")

            # === 节点5: AI 内容生成 ===
            print("\n[5/6] AI 内容生成...")
            content_inputs = []
            for i, title in enumerate(titles):
                kw = filtered[i] if i < len(filtered) else filtered[-1]
                content_inputs.append({"keyword": kw, "title": title})

            content_gen = AIContentGenerator("content_generator", config={
                "batch_size": 3, "target_word_count": 800, "html_format": True, "enable_fallback": True,
            })
            result = content_gen.execute(content_inputs)
            assert result.status.value == "completed"
            contents = result.output_data
            assert isinstance(contents, list)
            assert len(contents) == len(titles)
            assert all(isinstance(c, str) and "<" in c for c in contents)
            print(f"  ✅ 生成 {len(contents)} 篇文章, 平均 {sum(len(c) for c in contents) // len(contents)} 字符")

            # === 节点6: WordPress 发布 ===
            print("\n[6/6] WordPress 发布...")
            wp_inputs = []
            for i, title in enumerate(titles):
                kw = filtered[i] if i < len(filtered) else filtered[-1]
                content = contents[i] if i < len(contents) else ""
                wp_inputs.append({"title": title, "content": content, "keyword": kw})

            publisher = WordPressPublisher("wordpress_publisher", config={
                "batch_size": 5, "api_type": "rest", "default_status": "draft",
                "auto_create_categories": False, "auto_create_tags": False,
                "enable_media_upload": False,
            })
            result = publisher.execute(wp_inputs)
            assert result.status.value == "completed", f"WP发布失败: {result.error_message}"
            wp_results = result.output_data
            assert len(wp_results) == len(wp_inputs)
            # WordPressPublishResult 是 dataclass，部分字段为 None 时表示跳过
            published = sum(1 for r in wp_results if getattr(r, "post_id", None))
            print(f"  ✅ 发布完成: {published}/{len(wp_results)} 篇文章已发布")

            # === 最终验证 ===
            print(f"\n{'=' * 60}")
            print(f"管线验证通过!")
            print(f"  Excel:     {len(keywords)} 个关键词")
            print(f"  扩展:      {len(keywords)} → {len(expanded)}")
            print(f"  筛选:      {len(expanded)} → {len(filtered)}")
            print(f"  标题:      {len(titles)} 个")
            print(f"  内容:      {len(contents)} 篇")
            print(f"  发布:      {published} 篇")
            print(f"{'=' * 60}")

            # 验证数据传递完整性
            assert len(filtered) > 0
            assert len(titles) > 0
            assert len(contents) > 0
            assert len(wp_results) > 0

        finally:
            if excel_path.exists():
                os.unlink(excel_path)

    def test_full_pipeline_dry_run(self):
        """测试 Dry-run 模式（无 AI 和 WP 调用）"""
        print("\n" + "=" * 60)
        print("Dry-run 测试: 不使用 AI / WP")
        print("=" * 60)

        test_keywords = ["metal hardware", "lighting accessories"]
        excel_path = self.create_test_excel(test_keywords)

        try:
            # 节点1
            excel = ExcelProcessor("excel_reader", config={
                "keyword_column": "keywords", "deduplicate": True,
            })
            keywords = excel.execute_impl(str(excel_path))

            # 节点2 — 使用 mock 数据
            expander = KeywordExpander("keyword_expander", config={
                "use_mock_data": True, "max_expansions_per_keyword": 5,
            })
            expanded = expander.execute_impl(keywords)

            # 节点3 — 跳过 AI，直接传递
            filtered = expanded

            # 节点4 — 默认标题（不设 AI 客户端）
            title_gen = AITitleGenerator("title_generator", config={
                "batch_size": 10, "enable_fallback": True,
            })
            titles = title_gen.execute_impl(filtered)

            # 节点5 — 默认内容
            content_inputs = [
                {"keyword": filtered[i] if i < len(filtered) else "", "title": t}
                for i, t in enumerate(titles)
            ]
            content_gen = AIContentGenerator("content_generator", config={
                "batch_size": 3, "html_format": True, "enable_fallback": True,
            })
            contents = content_gen.execute_impl(content_inputs)

            # 验证
            assert len(keywords) == 2
            assert len(expanded) > len(keywords)
            assert len(titles) == len(filtered)
            assert len(contents) == len(titles)
            print(f"  ✅ Dry-run 通过: {len(keywords)} 关键词 → {len(contents)} 篇文章")

        finally:
            if excel_path.exists():
                os.unlink(excel_path)

    def test_pipeline_data_structures(self):
        """验证节点间数据结构匹配"""
        print("\n" + "=" * 60)
        print("数据结构验证")
        print("=" * 60)

        # 模拟中间数据
        keywords = ["kw1", "kw2", "kw3"]

        # 内容生成器接受 dict 列表或字符串列表
        content_gen = AIContentGenerator("test_cg", config={"enable_fallback": True})
        dict_input = [{"keyword": k, "title": f"Title for {k}"} for k in keywords]
        string_input = ["kw1", "kw2"]

        # 验证两种输入格式都能被接受
        prepared_dict = content_gen._validate_and_prepare_input(dict_input)
        assert len(prepared_dict) == 3
        assert all("keyword" in d and "title" in d for d in prepared_dict)

        prepared_str = content_gen._validate_and_prepare_input(string_input)
        assert len(prepared_str) == 2
        assert all("keyword" in d and "title" in d for d in prepared_str)

        # WordPress 发布器接受 dict 列表
        publisher = WordPressPublisher("test_wp", config={
            "api_type": "rest", "enable_media_upload": False,
        })
        # Mock connection test
        publisher.wp_client = Mock()
        publisher.wp_client.test_connection.return_value = True
        publisher.wp_client.get_categories.return_value = []
        publisher.wp_client.get_tags.return_value = []

        wp_dict_input = [
            {"title": f"Title {i}", "content": f"<p>Content {i}</p>", "keyword": k}
            for i, k in enumerate(keywords)
        ]
        wp_prepared = publisher._validate_and_prepare_input(wp_dict_input)
        assert len(wp_prepared) == 3
        assert all(hasattr(p, "title") and hasattr(p, "content") for p in wp_prepared)

        print("  ✅ 所有数据结构验证通过")

    def test_empty_excel_handling(self):
        """测试空 Excel 文件的处理"""
        print("\n" + "=" * 60)
        print("边界情况: 空 Excel")
        print("=" * 60)

        df = pd.DataFrame({"keywords": []})
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp_path = Path(tmp.name)
        df.to_excel(tmp_path, index=False)
        tmp.close()

        try:
            excel = ExcelProcessor("excel_reader", config={"keyword_column": "keywords"})
            result = excel.execute(str(tmp_path))
            assert result.status.value == "failed", "空 Excel 应该返回失败"
            print("  ✅ 空 Excel 正确处理")
        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)

    def test_single_keyword_pipeline(self):
        """测试单个关键词的完整流程"""
        print("\n" + "=" * 60)
        print("边界情况: 单个关键词")
        print("=" * 60)

        keyword = ["only one keyword"]
        excel_path = self.create_test_excel(keyword)

        try:
            excel = ExcelProcessor("excel_reader", config={"keyword_column": "keywords"})
            keywords = excel.execute_impl(str(excel_path))
            assert len(keywords) == 1

            expander = KeywordExpander("keyword_expander", config={
                "use_mock_data": True, "max_expansions_per_keyword": 3,
            })
            expanded = expander.execute_impl(keywords)
            assert len(expanded) > 0

            title_gen = AITitleGenerator("title_generator", config={"enable_fallback": True})
            titles = title_gen.execute_impl(expanded)
            assert len(titles) > 0

            content_gen = AIContentGenerator("content_generator", config={"enable_fallback": True})
            inputs = [{"keyword": expanded[0], "title": titles[0]}]
            contents = content_gen.execute_impl(inputs)
            assert len(contents) == 1

            print(f"  ✅ 单个关键词流程通过: {keyword[0]} → {len(expanded)} 扩展 → {len(titles)} 标题 → {len(contents)} 文章")
        finally:
            if excel_path.exists():
                os.unlink(excel_path)


if __name__ == "__main__":
    import sys
    print("运行完整端到端集成测试...")
    tester = TestFullPipeline()

    try:
        tester.test_full_pipeline_dry_run()
        tester.test_pipeline_data_structures()
        tester.test_empty_excel_handling()
        tester.test_single_keyword_pipeline()
        print("\n✅ 所有端到端测试通过!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ 测试断言失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
