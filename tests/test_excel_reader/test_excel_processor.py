"""
Excel处理器单元测试
"""
import tempfile
import os
from pathlib import Path
import pandas as pd
import pytest

from src.modules.excel_reader.excel_processor import ExcelProcessor, read_keywords_from_excel


class TestExcelProcessor:
    """ExcelProcessor测试类"""

    def test_initialization(self):
        """测试初始化"""
        processor = ExcelProcessor("test-processor")
        assert processor.node_id == "test-processor"
        assert processor.node_type == "excel_reader"
        assert processor.config == {}
        assert processor.status.name == "PENDING"

    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        config = {
            "sheet_name": 1,
            "keyword_column": "keyword",
            "header_row": 1,
            "max_rows": 10,
            "skip_empty": False,
            "deduplicate": False,
            "validate_keywords": False
        }
        processor = ExcelProcessor("test-processor", config)
        assert processor.sheet_name == 1
        assert processor.keyword_column == "keyword"
        assert processor.header_row == 1
        assert processor.max_rows == 10
        assert processor.skip_empty == False
        assert processor.deduplicate == False
        assert processor.validate_keywords == False

    def test_validate_file_existence(self):
        """测试文件存在性验证"""
        processor = ExcelProcessor("test-processor")

        # 测试不存在的文件
        with pytest.raises(Exception) as exc_info:
            processor._validate_file(Path("nonexistent.xlsx"))
        assert "文件未找到" in str(exc_info.value) or "FileNotFound" in str(exc_info.value)

    def test_validate_file_extension(self):
        """测试文件扩展名验证"""
        processor = ExcelProcessor("test-processor")

        # 创建临时文件（错误扩展名）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception) as exc_info:
                processor._validate_file(temp_path)
            # 检查错误消息是否包含"文件格式"或"FileFormat"
            error_msg = str(exc_info.value)
            assert "文件格式" in error_msg or "FileFormat" in error_msg
        finally:
            # 确保文件被删除
            try:
                temp_path.unlink(missing_ok=True)
            except:
                pass

    def test_create_test_excel_file(self):
        """创建测试Excel文件"""
        # 创建DataFrame
        data = {
            "keywords": ["hardware tools", "lighting accessories", "metal parts", "", "hardware accessories"],
            "category": ["tools", "lighting", "hardware", "unknown", "hardware"]
        }
        df = pd.DataFrame(data)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = Path(f.name)
            df.to_excel(temp_path, index=False)
            return temp_path

    def test_read_excel_file(self):
        """测试读取Excel文件"""
        processor = ExcelProcessor("test-processor")

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            df = processor._read_excel(temp_path)
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 5
            assert "keywords" in df.columns
            assert "category" in df.columns
        finally:
            os.unlink(temp_path)

    def test_extract_keywords(self):
        """测试关键词提取"""
        processor = ExcelProcessor("test-processor")

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            df = processor._read_excel(temp_path)
            keywords = processor._extract_keywords(df)

            # 应该提取4个非空关键词（第4行为空）
            assert len(keywords) == 4
            assert "hardware tools" in keywords
            assert "lighting accessories" in keywords
            assert "metal parts" in keywords
            assert "hardware accessories" in keywords
        finally:
            os.unlink(temp_path)

    def test_extract_keywords_with_custom_column(self):
        """测试使用自定义列名提取关键词"""
        processor = ExcelProcessor("test-processor", {"keyword_column": "category"})

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            df = processor._read_excel(temp_path)
            keywords = processor._extract_keywords(df)

            # 应该从category列提取关键词
            assert len(keywords) == 5  # 所有行都有category值
            assert "tools" in keywords
            assert "lighting" in keywords
            assert "hardware" in keywords
            assert "unknown" in keywords
            assert "五金" in keywords
        finally:
            os.unlink(temp_path)

    def test_validate_keyword(self):
        """测试关键词验证"""
        processor = ExcelProcessor("test-processor")

        # 有效关键词
        is_valid, reason = processor._validate_keyword("hardware tools")
        assert is_valid == True
        assert reason == "有效"

        # 太短的关键词
        is_valid, reason = processor._validate_keyword("a")
        assert is_valid == False
        assert "太短" in reason

        # 太长的关键词
        is_valid, reason = processor._validate_keyword("a" * 101)
        assert is_valid == False
        assert "太长" in reason

        # 只包含特殊字符的关键词
        is_valid, reason = processor._validate_keyword("!!!")
        assert is_valid == False
        assert "不包含字母或数字" in reason

        # 包含HTML标签的关键词
        is_valid, reason = processor._validate_keyword("<script>alert()</script>")
        assert is_valid == False
        assert "包含不安全字符" in reason

    def test_process_keywords(self):
        """测试关键词处理（去重、排序）"""
        processor = ExcelProcessor("test-processor", {"deduplicate": True, "sort_keywords": True})

        keywords = ["zebra", "apple", "zebra", "banana", "apple"]
        processed = processor._process_keywords(keywords)

        # 应该去重并排序
        assert len(processed) == 3
        assert processed == ["apple", "banana", "zebra"]

    def test_process_keywords_without_deduplication(self):
        """测试不去重的关键词处理"""
        processor = ExcelProcessor("test-processor", {"deduplicate": False})

        keywords = ["zebra", "apple", "zebra", "banana", "apple"]
        processed = processor._process_keywords(keywords)

        # 应该保留重复项
        assert len(processed) == 5
        assert processed == keywords

    def test_process_keywords_with_limit(self):
        """测试带数量限制的关键词处理"""
        processor = ExcelProcessor("test-processor", {"max_keywords": 2})

        keywords = ["zebra", "apple", "banana", "orange"]
        processed = processor._process_keywords(keywords)

        # 应该只保留前2个
        assert len(processed) == 2
        assert processed == ["zebra", "apple"]

    def test_execute_with_file_path(self):
        """测试使用文件路径执行"""
        processor = ExcelProcessor("test-processor")

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            keywords = processor.execute(temp_path)
            assert isinstance(keywords, list)
            assert len(keywords) == 4
        finally:
            os.unlink(temp_path)

    def test_execute_with_dict_input(self):
        """测试使用字典输入执行"""
        processor = ExcelProcessor("test-processor")

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            input_data = {"file_path": str(temp_path)}
            keywords = processor.execute(input_data)
            assert isinstance(keywords, list)
            assert len(keywords) == 4
        finally:
            os.unlink(temp_path)

    def test_validate_input_method(self):
        """测试输入验证方法"""
        processor = ExcelProcessor("test-processor")

        # 创建测试文件
        temp_path = self.test_create_test_excel_file()
        try:
            # 有效输入
            assert processor.validate_input(str(temp_path)) == True
            assert processor.validate_input({"file_path": str(temp_path)}) == True

            # 无效输入
            assert processor.validate_input(None) == False
            assert processor.validate_input(123) == False
        finally:
            os.unlink(temp_path)

    def test_validate_output_method(self):
        """测试输出验证方法"""
        processor = ExcelProcessor("test-processor")

        # 有效输出
        assert processor.validate_output(["keyword1", "keyword2"]) == True

        # 无效输出
        assert processor.validate_output(None) == False
        assert processor.validate_output([]) == False
        assert processor.validate_output("not a list") == False
        assert processor.validate_output([123, "keyword"]) == False
        assert processor.validate_output(["", "keyword"]) == False


class TestReadKeywordsFromExcel:
    """read_keywords_from_excel函数测试类"""

    def test_convenience_function(self):
        """测试便捷函数"""
        # 创建测试文件
        data = {"keywords": ["test1", "test2", "test3"]}
        df = pd.DataFrame(data)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = Path(f.name)
            df.to_excel(temp_path, index=False)
            try:
                keywords = read_keywords_from_excel(temp_path, keyword_column="keywords")
                assert keywords == ["test1", "test2", "test3"]
            finally:
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])