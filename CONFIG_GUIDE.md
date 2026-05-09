# SEO 内容自动化工作流 — 配置指南

运行完整工作流前，需要配置以下信息。

---

## 1. 环境变量（必须设置）

### OpenAI API 密钥（必填）

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."

# Windows CMD
set OPENAI_API_KEY=sk-...

# Linux / macOS
export OPENAI_API_KEY="sk-..."
```

### Anthropic API 密钥（可选，用于 AI 调用失败时的回退模型）

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 行业名称（可选，用于 AI prompt 模板）

```bash
export SEO_INDUSTRY_NAME="Metal Hardware & Lighting Accessories Processing"
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥，**必填** | 无 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥，回退时使用 | 无 |
| `SEO_INDUSTRY_NAME` | 目标行业名称，写入 AI prompt | Metal Hardware & Lighting Accessories Processing |

---

## 2. WordPress 配置

编辑 `config/wordpress_config.py`：

```python
WORDPRESS_URL = "https://你的站点.com"
WORDPRESS_USERNAME = "管理员用户名"
WORDPRESS_APPLICATION_PASSWORD = "xxxx xxxx xxxx xxxx"
DEFAULT_CATEGORY_ID = 1
```

### 如何获取 WP 应用密码

1. 登录 WordPress 后台
2. 进入 **用户 → 个人资料**
3. 滚动到 **应用程序密码** 部分
4. 输入名称（如 "SEO Workflow"），点击 **添加**
5. 复制生成的密码（格式为 `xxxx xxxx xxxx xxxx`）

| 设置 | 说明 |
|------|------|
| `WORDPRESS_URL` | WordPress 站点 URL，如 `https://your-site.com` |
| `WORDPRESS_USERNAME` | 管理员用户名 |
| `WORDPRESS_APPLICATION_PASSWORD` | 应用程序密码（见上方获取方式） |
| `DEFAULT_CATEGORY_ID` | 默认分类 ID（默认为 1，需确认站点上存在该分类） |

---

## 3. AI 模型选择

编辑 `config/ai_models_config.py` 可修改每个节点使用的模型：

| 节点 | 默认模型 | 回退模型（主模型失败时） |
|------|---------|------------------------|
| keyword_filter（关键词筛选） | gpt-4o-mini | claude-3-5-haiku |
| title_generator（标题生成） | gpt-4o | claude-3-5-sonnet |
| content_generator（内容生成） | gpt-4o | claude-3-opus |

如需更换模型，编辑 `config/ai_models_config.py` 中对应节点的 `model` 字段即可。

---

## 4. Prompt 模板（可选）

编辑 `config/prompts_config.py` 可自定义 AI prompt 模板。prompt 中的 `{INDUSTRY_NAME}` 会自动替换为环境变量 `SEO_INDUSTRY_NAME` 的值。如需切换行业，只需修改该环境变量，无需手动改 prompt 文本。

---

## 5. 测试用例 Excel

项目根目录下的 `测试用例.xlsx` 包含 3 个测试关键词：

```
keywords
metal hardware
lamp holder
Lighting accessories
```

你也可以使用自己的 Excel 文件，只需确保有一列名为 `keywords`。

---

## 6. 运行命令

```bash
# 1. 先安装依赖
pip install -r requirements.txt

# 2. 跑测试（27 个测试，全部使用 Mock，无需配置 API）
python -m pytest tests/ -v --tb=short

# 3. Dry-run 模式（无需 API 密钥，使用 mock 数据走通全流程）
python -m src.cli.main workflow run 测试用例.xlsx --dry-run -o ./output

# 4. 真实运行（需要配置 API 密钥和 WordPress 信息）
python -m src.cli.main workflow run 测试用例.xlsx -o ./output

# 5. 查看工作流状态/列表
python -m src.cli.main workflow status
python -m src.cli.main workflow list

# 6. 取消某个工作流
python -m src.cli.main workflow cancel <workflow_id>
```
