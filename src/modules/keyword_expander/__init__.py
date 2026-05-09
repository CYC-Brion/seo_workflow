"""
关键词扩展模块
使用Google搜索API获取下拉推荐关键词
"""

from .keyword_expander import (
    KeywordExpansionResult,
    KeywordExpander,
    expand_keywords,
)

__all__ = [
    "KeywordExpansionResult",
    "KeywordExpander",
    "expand_keywords",
]