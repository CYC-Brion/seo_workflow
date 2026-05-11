# SEO 内容自动化工作流 — 操作指南

## 一、生成文章

### 1. 准备 Excel

| keywords | category |
|----------|----------|
| lamp holder | Technical Guides |
| hardware | Industry Insights |
| surface treatment | Technical Guides |

- `keywords` 列：必填
- `category` 列：可选，填 `Technical Guides` 或 `Industry Insights`，不填默认 Technical Guides

### 2. 运行

```bash
# 生成文章，全部存为草稿
python -m src.cli.main workflow run 测试用例.xlsx

# 仅验证流程，不调用 AI 和 WordPress
python -m src.cli.main workflow run 测试用例.xlsx --dry-run
```

### 3. 发布

自动发布由 **GitHub Actions** 负责，每小时执行一次，无需电脑开机。

```bash
# 手动发布一篇（测试用）
python -m src.cli.main workflow publish-next
```

### 4. 检查自动发布状态

打开仓库的 GitHub Actions 面板 → 点 `SEO Auto Publish Draft` → 查看每次运行的日志。

有草稿时的日志示例：
```
=== 2026-05-11 03:07:00 UTC 开始 ===
发布 #14435: Lighting Accessories Meaning...
已发布 #14435: ...
```

没有草稿时：
```
没有草稿，跳过
```

---

## 二、修改 Prompt

所有 prompt 在 `config/prompts_config.py`，改完保存即生效。

### 文件结构

```
KEYWORD_FILTER_PROMPT                 ← 关键词筛选（节点3）
TITLE_GENERATOR_PROMPT                ← 标题生成（节点4）
CONTENT_PROMPT_TECHNICAL_GUIDES       ← Technical Guides 文章
CONTENT_PROMPT_INDUSTRY_INSIGHTS      ← Industry Insights 文章
CATEGORY_PROMPTS                      ← 分类→prompt 映射
```

### 改哪个

| 想改的内容 | 改这里 |
|-----------|--------|
| 筛选关键词的逻辑 | `KEYWORD_FILTER_PROMPT` |
| 标题风格 | `TITLE_GENERATOR_PROMPT` |
| Technical Guides 文章写法 | `CONTENT_PROMPT_TECHNICAL_GUIDES` |
| Industry Insights 文章写法 | `CONTENT_PROMPT_INDUSTRY_INSIGHTS` |
| 模型温度、字数 | 每个 prompt 末尾的 `parameters` |

### 改法示例

让 Technical Guides 文章更短：打开 `config/prompts_config.py`，找到 `CONTENT_PROMPT_TECHNICAL_GUIDES`：

```python
# Goals 下第 4 条，改字数
4. The article should be around 800 words  # 原 1,500

# 末尾 parameters，改 max_tokens
"parameters": {"temperature": 0.8, "max_tokens": 4000,}  # 原 8000
```

保存即生效，下次 `run` 自动使用新 prompt。

### 验证

```bash
# 先用 1 个关键词测试
python -m src.cli.main workflow run 测试用例.xlsx
```

---

## 三、其他配置

| 文件 | 内容 |
|------|------|
| `config/ai_models_config.py` | 模型选择、超时时间、温度 |
| `config/wordpress_config.py` | 默认分类 ID、定时发布 |
| `config/prompts_config.py` | Prompt 模板 |
| `.env` | API 密钥、行业名称 |

### 行业名称

在 `.env` 中改：
```
SEO_INDUSTRY_NAME=Metal Hardware & Lighting Accessories Processing
```

### 新增分类

1. WordPress 后台创建新 Category
2. `config/wordpress_config.py` → `CATEGORY_MAPPING` 加一行
3. `config/prompts_config.py` → 新增 `CONTENT_PROMPT_XXX` → 在 `CATEGORY_PROMPTS` 注册
