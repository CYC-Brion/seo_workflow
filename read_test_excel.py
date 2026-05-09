#!/usr/bin/env python
"""
读取测试用例Excel文件，查看内容
"""
import pandas as pd
import sys
from pathlib import Path

def read_excel_file(file_path):
    """读取Excel文件并显示内容"""
    try:
        print(f"读取文件: {file_path}")

        # 读取Excel文件
        df = pd.read_excel(file_path)

        print(f"工作表数量: {len(df.columns)}")
        print(f"数据形状: {df.shape}")
        print(f"列名: {list(df.columns)}")

        print("\n=== 文件内容 ===")
        for i, col in enumerate(df.columns):
            print(f"列 {i}: '{col}'")

        # 显示前几行数据
        print("\n=== 前5行数据 ===")
        print(df.head())

        # 尝试查找关键词列
        keyword_column = None
        possible_keyword_columns = ['keywords', 'keyword', '关键词', 'key', 'kw']

        for col in df.columns:
            col_lower = str(col).lower()
            for possible in possible_keyword_columns:
                if possible in col_lower:
                    keyword_column = col
                    break
            if keyword_column:
                break

        if keyword_column:
            print(f"\n检测到关键词列: '{keyword_column}'")
            keywords = df[keyword_column].dropna().tolist()
            print(f"关键词数量: {len(keywords)}")
            print(f"关键词示例: {keywords[:10]}")
            return keywords
        else:
            print("\n未找到标准关键词列，使用第一列")
            first_col = df.columns[0]
            keywords = df[first_col].dropna().tolist()
            print(f"使用列 '{first_col}'，关键词数量: {len(keywords)}")
            print(f"关键词示例: {keywords[:10]}")
            return keywords

    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        return []

if __name__ == "__main__":
    excel_file = Path("D:/工作流项目/测试用例.xlsx")
    if excel_file.exists():
        keywords = read_excel_file(excel_file)
        print(f"\n=== 总结 ===")
        print(f"总关键词数量: {len(keywords)}")
        print(f"关键词列表: {keywords}")
    else:
        print(f"文件不存在: {excel_file}")