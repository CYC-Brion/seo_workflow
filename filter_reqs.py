#!/usr/bin/env python3
"""
过滤requirements.txt文件
移除python>=3.8和wordpress-api>=2.0行
"""
import sys

def filter_requirements(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == 'python>=3.8':
            continue
        if stripped.startswith('wordpress-api>='):
            continue
        filtered_lines.append(line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)

    print(f"过滤完成，原始行数: {len(lines)}，过滤后行数: {len(filtered_lines)}")
    return True

if __name__ == '__main__':
    input_file = 'requirements.txt'
    output_file = 'requirements_filtered.txt'
    filter_requirements(input_file, output_file)