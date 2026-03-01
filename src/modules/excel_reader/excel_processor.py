"""
Excel处理器
读取和处理Excel文件中的关键词数据
"""

import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re

from src.core import DataProcessingNode
from src.utils import get_logger, FileError, FileNotFoundError, FileFormatError


class ExcelProcessor(DataProcessingNode):
    """Excel关键词读取器"""

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化Excel处理器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - sheet_name: Excel工作表名称（默认: 0）
                - keyword_column: 关键词列名（默认: "keywords"）
                - header_row: 表头行索引（默认: 0）
                - max_rows: 最大读取行数（默认: None，读取所有）
                - skip_empty: 是否跳过空值（默认: True）
                - deduplicate: 是否去重（默认: True）
                - validate_keywords: 是否验证关键词格式（默认: True）
        """
        config = config or {}
        super().__init__(node_id, "excel_reader", config)

        # 配置参数
        self.sheet_name = config.get("sheet_name", 0)
        self.keyword_column = config.get("keyword_column", "keywords")
        self.header_row = config.get("header_row", 0)
        self.max_rows = config.get("max_rows")
        self.skip_empty = config.get("skip_empty", True)
        self.deduplicate = config.get("deduplicate", True)
        self.validate_keywords = config.get("validate_keywords", True)

        # 统计数据
        self.stats = {
            "total_rows": 0,
            "valid_keywords": 0,
            "invalid_keywords": 0,
            "empty_rows": 0,
            "duplicate_keywords": 0,
        }

        self.logger.info(
            f"Excel处理器初始化: {node_id}",
            config=self.config
        )

    def execute_impl(self, input_data: Any) -> Any:
        """执行Excel读取

        Args:
            input_data: 输入数据，可以是文件路径字符串或字典

        Returns:
            处理后的关键词列表
        """
        # 解析输入数据
        file_path = self._parse_input(input_data)

        # 验证文件
        self._validate_file(file_path)

        # 读取Excel文件
        df = self._read_excel(file_path)

        # 提取关键词
        keywords = self._extract_keywords(df)

        # 处理关键词
        processed_keywords = self._process_keywords(keywords)

        # 记录统计信息
        self._log_statistics()

        return processed_keywords

    def _parse_input(self, input_data: Any) -> Path:
        """解析输入数据，获取文件路径"""
        if isinstance(input_data, str):
            file_path = Path(input_data)
        elif isinstance(input_data, dict) and "file_path" in input_data:
            file_path = Path(input_data["file_path"])
        elif isinstance(input_data, Path):
            file_path = input_data
        else:
            raise FileError(
                message="输入数据必须是文件路径字符串或包含'file_path'的字典",
                file_path=str(input_data)[:100]
            )

        return file_path

    def _validate_file(self, file_path: Path) -> None:
        """验证文件"""
        # 检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(file_path=str(file_path))

        # 检查文件扩展名
        valid_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
        if file_path.suffix.lower() not in valid_extensions:
            raise FileFormatError(
                file_path=str(file_path),
                expected_format=", ".join(valid_extensions)
            )

        # 检查文件大小
        max_size_mb = self.config.get("max_file_size_mb", 100)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise FileError(
                message=f"文件太大: {file_size_mb:.2f}MB > {max_size_mb}MB",
                file_path=str(file_path),
                details={"file_size_mb": file_size_mb, "max_size_mb": max_size_mb}
            )

        self.logger.debug(f"文件验证通过: {file_path}")

    def _read_excel(self, file_path: Path) -> pd.DataFrame:
        """读取Excel文件"""
        try:
            self.logger.info(f"读取Excel文件: {file_path}")

            # 使用pandas读取Excel
            read_kwargs = {
                "sheet_name": self.sheet_name,
                "header": self.header_row,
                "nrows": self.max_rows,
                "engine": "openpyxl" if file_path.suffix.lower() in ['.xlsx', '.xlsm'] else None
            }

            # 移除None值
            read_kwargs = {k: v for k, v in read_kwargs.items() if v is not None}

            df = pd.read_excel(file_path, **read_kwargs)

            # 记录基本信息
            self.stats["total_rows"] = len(df)
            self.logger.info(
                f"Excel文件读取完成",
                file_path=str(file_path),
                total_rows=len(df),
                columns=list(df.columns)
            )

            return df

        except Exception as e:
            raise FileError(
                message=f"读取Excel文件失败: {str(e)}",
                file_path=str(file_path),
                details={"error": str(e)}
            )

    def _extract_keywords(self, df: pd.DataFrame) -> List[str]:
        """从DataFrame中提取关键词"""
        keywords = []

        # 检查关键词列是否存在
        if self.keyword_column not in df.columns:
            # 尝试查找包含"keyword"的列
            keyword_cols = [col for col in df.columns if "keyword" in col.lower()]
            if keyword_cols:
                self.keyword_column = keyword_cols[0]
                self.logger.warning(
                    f"未找到列 '{self.keyword_column}'，使用 '{self.keyword_column}' 代替"
                )
            else:
                # 使用第一列
                self.keyword_column = df.columns[0]
                self.logger.warning(
                    f"未找到关键词列，使用第一列 '{self.keyword_column}'"
                )

        # 提取关键词
        for idx, value in df[self.keyword_column].items():
            if pd.isna(value):
                if self.skip_empty:
                    self.stats["empty_rows"] += 1
                    continue
                else:
                    value = ""

            # 转换为字符串并清理
            keyword = str(value).strip()

            # 验证关键词
            if self.validate_keywords:
                is_valid, reason = self._validate_keyword(keyword)
                if not is_valid:
                    self.stats["invalid_keywords"] += 1
                    self.logger.debug(f"无效关键词: {keyword}", reason=reason)
                    if not self.config.get("keep_invalid", False):
                        continue

            if keyword:  # 非空字符串
                keywords.append(keyword)
                self.stats["valid_keywords"] += 1
            else:
                self.stats["empty_rows"] += 1

        self.logger.info(
            f"关键词提取完成",
            total_keywords=len(keywords),
            valid_keywords=self.stats["valid_keywords"],
            invalid_keywords=self.stats["invalid_keywords"],
            empty_rows=self.stats["empty_rows"]
        )

        return keywords

    def _validate_keyword(self, keyword: str) -> tuple[bool, str]:
        """验证关键词格式"""
        # 检查长度
        if len(keyword) < 2:
            return False, "太短（< 2字符）"
        if len(keyword) > 100:
            return False, "太长（> 100字符）"

        # 检查是否只包含特殊字符
        if not re.search(r'[a-zA-Z0-9]', keyword):
            return False, "不包含字母或数字"

        # 检查是否包含不安全的字符
        unsafe_patterns = [
            r'[<>"\']',  # HTML标签和引号
            r'[\x00-\x1F\x7F]',  # 控制字符
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, keyword):
                return False, "包含不安全字符"

        return True, "有效"

    def _process_keywords(self, keywords: List[str]) -> List[str]:
        """处理关键词列表"""
        processed_keywords = keywords.copy()

        # 去重
        if self.deduplicate:
            original_count = len(processed_keywords)
            # 先转换为小写去重，保留原始大小写（第一个出现的）
            seen = set()
            unique_keywords = []
            for kw in processed_keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    seen.add(kw_lower)
                    unique_keywords.append(kw)

            duplicate_count = original_count - len(unique_keywords)
            processed_keywords = unique_keywords
            self.stats["duplicate_keywords"] = duplicate_count

            if duplicate_count > 0:
                self.logger.info(f"去重完成", removed_duplicates=duplicate_count)

        # 排序（可选）
        if self.config.get("sort_keywords", True):
            processed_keywords.sort(key=lambda x: x.lower())
            self.logger.debug("关键词已排序")

        # 限制数量（可选）
        max_keywords = self.config.get("max_keywords")
        if max_keywords and len(processed_keywords) > max_keywords:
            original_count = len(processed_keywords)
            processed_keywords = processed_keywords[:max_keywords]
            self.logger.warning(
                f"关键词数量超过限制",
                original_count=original_count,
                max_keywords=max_keywords,
                kept_count=len(processed_keywords)
            )

        return processed_keywords

    def _log_statistics(self) -> None:
        """记录统计信息"""
        total_processed = (
            self.stats["valid_keywords"] +
            self.stats["invalid_keywords"] +
            self.stats["empty_rows"]
        )

        if total_processed > 0:
            validity_rate = self.stats["valid_keywords"] / total_processed * 100
        else:
            validity_rate = 0

        self.logger.info(
            "Excel处理统计",
            total_rows=self.stats["total_rows"],
            valid_keywords=self.stats["valid_keywords"],
            invalid_keywords=self.stats["invalid_keywords"],
            empty_rows=self.stats["empty_rows"],
            duplicate_keywords=self.stats["duplicate_keywords"],
            validity_rate=f"{validity_rate:.1f}%",
            final_count=self.stats["valid_keywords"] - self.stats["duplicate_keywords"]
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.stats.copy()

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        try:
            file_path = self._parse_input(input_data)
            self._validate_file(file_path)
            return True
        except Exception as e:
            self.logger.warning(f"输入验证失败: {e}")
            return False

    def validate_output(self, output_data: Any) -> bool:
        """验证输出数据"""
        if not isinstance(output_data, list):
            self.logger.warning(f"输出数据不是列表: {type(output_data)}")
            return False

        if len(output_data) == 0:
            self.logger.warning("输出数据为空列表")
            return False

        # 检查列表中的元素是否都是字符串
        for i, item in enumerate(output_data):
            if not isinstance(item, str):
                self.logger.warning(f"输出数据包含非字符串元素: 索引 {i}, 类型 {type(item)}")
                return False

            if not item.strip():
                self.logger.warning(f"输出数据包含空字符串: 索引 {i}")
                return False

        return True

    def pre_execute(self, input_data: Any) -> Any:
        """执行前处理"""
        self.logger.info("开始处理Excel文件")
        self.stats = {k: 0 for k in self.stats}  # 重置统计
        return input_data

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.info(f"Excel处理完成，获取 {len(output_data)} 个关键词")
        return output_data


# 工具函数
def read_keywords_from_excel(
    file_path: Union[str, Path],
    sheet_name: Union[int, str] = 0,
    keyword_column: str = "keywords",
    **kwargs
) -> List[str]:
    """
    从Excel文件读取关键词的便捷函数

    Args:
        file_path: Excel文件路径
        sheet_name: 工作表名称或索引
        keyword_column: 关键词列名
        **kwargs: 其他ExcelProcessor配置参数

    Returns:
        关键词列表
    """
    processor = ExcelProcessor(
        node_id="excel_reader_tool",
        config={
            "sheet_name": sheet_name,
            "keyword_column": keyword_column,
            **kwargs
        }
    )

    return processor.execute_impl(file_path)


__all__ = [
    "ExcelProcessor",
    "read_keywords_from_excel",
]