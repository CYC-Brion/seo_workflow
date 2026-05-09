"""
三节点工作流集成测试
测试完整工作流：Excel读取 → 关键词扩展 → AI关键词筛选
"""
import tempfile
import os
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.modules.excel_reader.excel_processor import ExcelProcessor
from src.modules.keyword_expander.keyword_expander import KeywordExpander
from src.modules.keyword_filter.ai_filter import AIKeywordFilter


def _mock_expander_google_suggest(expander: KeywordExpander):
    """为 KeywordExpander 的 session.get 挂上 Google + Bing Suggest mock"""
    def suggest_response(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        import urllib.parse
        if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            query = qs.get("q", ["hardware"])[0]
            resp.json.return_value = [
                query,
                [f"{query} manufacturers", f"{query} suppliers", f"{query} wholesale"]
            ]
        elif "api.bing.com" in url:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            query = qs.get("query", ["hardware"])[0]
            resp.json.return_value = [
                query,
                [f"{query} parts", f"custom {query}"]
            ]
        else:
            resp.json.return_value = ["", []]
        return resp
    expander.session.get = Mock(side_effect=suggest_response)


class TestThreeNodeWorkflow:
    """三节点工作流集成测试类"""

    def create_test_excel_file(self, keywords: list) -> Path:
        """创建测试Excel文件"""
        data = {"keywords": keywords}
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = Path(f.name)
            df.to_excel(temp_path, index=False)
            return temp_path

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_workflow_with_mock_data(self, mock_get_ai_client):
        """测试使用模拟数据的完整工作流"""
        # 模拟AI客户端响应
        mock_client = Mock()
        mock_response = '["metal hardware", "lighting accessories", "hardware tools"]'
        mock_client.chat_completion.return_value.content = mock_response
        mock_client.chat_completion.return_value.usage = {"total_tokens": 50}
        mock_client.chat_completion.return_value.cost = 0.001
        mock_get_ai_client.return_value = mock_client

        # 1. 创建测试Excel文件
        test_keywords = ["metal hardware", "lighting accessories"]
        temp_path = self.create_test_excel_file(test_keywords)

        try:
            # 2. Excel读取节点
            print("\n=== 步骤1: Excel读取 ===")
            excel_processor = ExcelProcessor("excel-reader", {
                "keyword_column": "keywords",
                "deduplicate": False,
                "validate_keywords": False
            })
            raw_keywords = excel_processor.execute_impl(temp_path)
            print(f"读取关键词: {raw_keywords}")
            print(f"读取统计: {excel_processor.get_statistics()}")

            # 验证Excel读取结果
            assert isinstance(raw_keywords, list)
            assert len(raw_keywords) == 2
            assert "metal hardware" in raw_keywords
            assert "lighting accessories" in raw_keywords

            # 3. 关键词扩展节点（Google Suggest mock）
            print("\n=== 步骤2: 关键词扩展 ===")
            keyword_expander = KeywordExpander("keyword-expander", {
                "max_expansions_per_keyword": 5,
                "request_delay_seconds": 0,  # 测试时无需延迟
            })
            _mock_expander_google_suggest(keyword_expander)
            expanded_keywords = keyword_expander.execute_impl(raw_keywords)
            print(f"扩展后关键词数量: {len(expanded_keywords)}")
            print(f"扩展统计: {keyword_expander.get_statistics()}")

            # 验证关键词扩展结果
            assert isinstance(expanded_keywords, list)
            assert len(expanded_keywords) > len(raw_keywords)  # 应该有所扩展
            # 原始关键词应该还在
            assert "metal hardware" in expanded_keywords
            assert "lighting accessories" in expanded_keywords

            # 4. AI关键词筛选节点（使用模拟AI客户端）
            print("\n=== 步骤3: AI关键词筛选 ===")
            ai_filter = AIKeywordFilter("ai-filter", {
                "batch_size": 10,
                "confidence_threshold": 0.7,
                "enable_fallback": False
            })
            filtered_keywords = ai_filter.execute_impl(expanded_keywords)
            print(f"筛选后关键词数量: {len(filtered_keywords)}")
            print(f"筛选统计: {ai_filter.get_statistics()}")

            # 验证AI筛选结果
            assert isinstance(filtered_keywords, list)
            assert len(filtered_keywords) > 0
            # 应该保留相关关键词
            assert "metal hardware" in filtered_keywords
            assert "lighting accessories" in filtered_keywords

            # 5. 整体验证
            print("\n=== 工作流完成 ===")
            print(f"原始关键词数量: {len(test_keywords)}")
            print(f"扩展后关键词数量: {len(expanded_keywords)}")
            print(f"筛选后关键词数量: {len(filtered_keywords)}")

            # 最终关键词数量应大于原始数量（因为扩展）
            assert len(filtered_keywords) > len(test_keywords)

            # 最终关键词列表应为字符串列表
            for kw in filtered_keywords:
                assert isinstance(kw, str)
                assert len(kw.strip()) > 0

        finally:
            # 清理临时文件
            os.unlink(temp_path)

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_workflow_with_empty_keywords(self, mock_get_ai_client):
        """测试空关键词工作流（边界情况）"""
        mock_client = Mock()
        mock_get_ai_client.return_value = mock_client

        # 创建空关键词Excel文件
        temp_path = self.create_test_excel_file([])

        try:
            # 空文件应该返回空列表
            excel_processor = ExcelProcessor("excel-reader")
            raw_keywords = excel_processor.execute_impl(temp_path)
            assert raw_keywords == []

            # 后续节点: 空关键词应直接跳过
            keyword_expander = KeywordExpander("keyword-expander", {
                "max_expansions_per_keyword": 5
            })
            # 空列表触发 ValueError
            with pytest.raises(ValueError):
                keyword_expander.execute_impl(raw_keywords)

        finally:
            os.unlink(temp_path)

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_workflow_with_single_keyword(self, mock_get_ai_client):
        """测试单个关键词工作流"""
        mock_client = Mock()
        mock_response = '["metal hardware"]'
        mock_client.chat_completion.return_value.content = mock_response
        mock_client.chat_completion.return_value.usage = {"total_tokens": 20}
        mock_client.chat_completion.return_value.cost = 0.0005
        mock_get_ai_client.return_value = mock_client

        test_keywords = ["metal hardware"]
        temp_path = self.create_test_excel_file(test_keywords)

        try:
            # Excel读取
            excel_processor = ExcelProcessor("excel-reader", {
                "keyword_column": "keywords",
                "deduplicate": False
            })
            raw_keywords = excel_processor.execute_impl(temp_path)
            assert len(raw_keywords) == 1

            # 关键词扩展
            keyword_expander = KeywordExpander("keyword-expander", {
                "max_expansions_per_keyword": 3
            })
            _mock_expander_google_suggest(keyword_expander)
            expanded_keywords = keyword_expander.execute_impl(raw_keywords)
            assert len(expanded_keywords) > 1

            # AI筛选
            ai_filter = AIKeywordFilter("ai-filter", {
                "batch_size": 5,
                "confidence_threshold": 0.6
            })
            filtered_keywords = ai_filter.execute_impl(expanded_keywords)
            assert len(filtered_keywords) > 0
            assert "metal hardware" in filtered_keywords

        finally:
            os.unlink(temp_path)

    def test_workflow_with_invalid_excel_file(self):
        """测试无效Excel文件的工作流"""
        # 创建非Excel文件
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"not an excel file")

        try:
            excel_processor = ExcelProcessor("excel-reader")
            with pytest.raises(Exception):
                excel_processor.execute_impl(temp_path)
        finally:
            os.unlink(temp_path)

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_workflow_statistics_tracking(self, mock_get_ai_client):
        """测试工作流统计信息跟踪"""
        mock_client = Mock()
        mock_response = '["metal hardware", "lighting accessories"]'
        mock_client.chat_completion.return_value.content = mock_response
        mock_client.chat_completion.return_value.usage = {"total_tokens": 40}
        mock_client.chat_completion.return_value.cost = 0.0008
        mock_get_ai_client.return_value = mock_client

        test_keywords = ["metal hardware", "lighting accessories"]
        temp_path = self.create_test_excel_file(test_keywords)

        try:
            # 三个节点
            excel_processor = ExcelProcessor("excel-reader")
            keyword_expander = KeywordExpander("keyword-expander", {
                "max_expansions_per_keyword": 5
            })
            _mock_expander_google_suggest(keyword_expander)
            ai_filter = AIKeywordFilter("ai-filter")

            # 执行工作流
            raw_keywords = excel_processor.execute_impl(temp_path)
            expanded_keywords = keyword_expander.execute_impl(raw_keywords)
            filtered_keywords = ai_filter.execute_impl(expanded_keywords)

            # 检查每个节点的统计信息
            excel_stats = excel_processor.get_statistics()
            expander_stats = keyword_expander.get_statistics()
            filter_stats = ai_filter.get_statistics()

            assert "total_rows" in excel_stats
            assert "valid_keywords" in excel_stats

            assert "total_keywords" in expander_stats
            assert "keywords_expanded" in expander_stats

            assert "total_keywords" in filter_stats
            assert "relevant_keywords" in filter_stats
            assert "ai_calls" in filter_stats

            # 验证统计数据的合理性
            assert excel_stats["valid_keywords"] == len(test_keywords)
            assert expander_stats["total_keywords"] == len(raw_keywords)
            assert filter_stats["total_keywords"] == len(expanded_keywords)

        finally:
            os.unlink(temp_path)

    @patch('src.modules.keyword_filter.ai_filter.get_ai_client')
    def test_workflow_with_ai_error(self, mock_get_ai_client):
        """测试AI出错时的工作流（回退机制）"""
        # 模拟AI客户端抛出异常
        mock_client = Mock()
        mock_client.chat_completion.side_effect = Exception("AI服务不可用")
        mock_get_ai_client.return_value = mock_client

        test_keywords = ["metal hardware"]
        temp_path = self.create_test_excel_file(test_keywords)

        try:
            # 启用回退的AI筛选器
            ai_filter = AIKeywordFilter("ai-filter", {
                "enable_fallback": True,
                "confidence_threshold": 0.3
            })

            excel_processor = ExcelProcessor("excel-reader")
            keyword_expander = KeywordExpander("keyword-expander", {
                "max_expansions_per_keyword": 5
            })
            _mock_expander_google_suggest(keyword_expander)

            # 执行工作流（AI出错时应回退到保留所有关键词）
            raw_keywords = excel_processor.execute_impl(temp_path)
            expanded_keywords = keyword_expander.execute_impl(raw_keywords)

            # AI筛选器应该不会抛出异常，而是回退
            filtered_keywords = ai_filter.execute_impl(expanded_keywords)

            # 回退时应该保留所有关键词
            assert len(filtered_keywords) == len(expanded_keywords)

        finally:
            os.unlink(temp_path)


def test_convenience_functions():
    """测试便捷函数的工作流"""
    # 创建测试Excel文件
    test_keywords = ["test keyword"]
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = Path(f.name)
        data = {"keywords": test_keywords}
        df = pd.DataFrame(data)
        df.to_excel(temp_path, index=False)

    try:
        # 测试Excel读取便捷函数
        from src.modules.excel_reader.excel_processor import read_keywords_from_excel
        keywords_from_excel = read_keywords_from_excel(temp_path)
        assert keywords_from_excel == test_keywords

        # 测试关键词扩展便捷函数
        from src.modules.keyword_expander.keyword_expander import expand_keywords
        import urllib.parse as _up
        with patch('requests.Session.get') as mock_get:
            def suggest_response(url, *args, **kwargs):
                resp = MagicMock()
                resp.raise_for_status.return_value = None
                if "suggestqueries.google.com" in url or "www.google.com/complete" in url:
                    qs = _up.parse_qs(_up.urlparse(url).query)
                    query = qs.get("q", ["hardware"])[0]
                    resp.json.return_value = [query, [f"{query} suppliers"]]
                elif "api.bing.com" in url:
                    qs = _up.parse_qs(_up.urlparse(url).query)
                    query = qs.get("query", ["hardware"])[0]
                    resp.json.return_value = [query, [f"{query} parts"]]
                else:
                    resp.json.return_value = ["", []]
                return resp
            mock_get.side_effect = suggest_response

            expanded_keywords, expander_stats = expand_keywords(
                test_keywords,
                max_expansions_per_keyword=2,
            )
        assert len(expanded_keywords) > len(test_keywords)
        assert "total_keywords" in expander_stats

        # 测试AI筛选便捷函数（需要模拟AI客户端）
        with patch('src.modules.keyword_filter.ai_filter.get_ai_client') as mock_get_ai_client:
            mock_client = Mock()
            mock_response = '["test keyword"]'
            mock_client.chat_completion.return_value.content = mock_response
            mock_client.chat_completion.return_value.usage = {"total_tokens": 10}
            mock_client.chat_completion.return_value.cost = 0.0002
            mock_get_ai_client.return_value = mock_client

            from src.modules.keyword_filter.ai_filter import filter_keywords_with_ai
            filtered_keywords, filter_stats = filter_keywords_with_ai(
                expanded_keywords,
                batch_size=5,
                confidence_threshold=0.5
            )
            assert len(filtered_keywords) > 0
            assert "total_keywords" in filter_stats

    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])