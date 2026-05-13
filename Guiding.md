# SEO 内容自动化工作流操作指南

## 1. 项目目的
这个项目用于把 Excel 关键词表自动处理成可发布到 WordPress 的 SEO 文章，主流程是：

1. 读取 Excel 关键词
2. 扩展长尾关键词
3. AI 筛选行业相关关键词
4. AI 生成标题
5. AI 生成正文
6. 发布到 WordPress

现在默认采用 WordPress 原生 `future` 定时发布，不再依赖 GitHub Actions 定时轮询草稿。

## 2. Excel 格式
准备一个 `.xlsx` 文件，至少包含 `keywords` 列。

示例：

| keywords | category |
|----------|----------|
| lamp holder | Technical Guides |
| hardware accessories | Industry Insights |
| surface treatment | Technical Guides |

说明：

- `keywords`：必填
- `category`：可选
- 如果不填 `category`，默认使用 `Technical Guides`

## 3. 默认发布方式
当前 `config/wordpress_config.py` 已配置为默认定时发布：

```python
SCHEDULE_POSTS = True
DEFAULT_SCHEDULE_HOURS = 1
DEFAULT_SCHEDULE_INTERVAL_HOURS = 1
TIMEZONE = "UTC"
```

这表示：

- 第 1 篇文章：从执行命令开始，1 小时后发布
- 第 2 篇文章：2 小时后发布
- 第 3 篇文章：3 小时后发布
- 依次类推，每篇相隔 1 小时

发布到 WordPress 后，文章状态会显示为 `Scheduled`，到点后由 WordPress 自动变成 `Published`。

## 4. 直接运行真实工作流
如果你使用当前默认配置，直接运行：

```bash
python -m src.cli.main workflow run 测试用例.xlsx
```

这条命令会：

- 自动读取 Excel
- 自动扩词、筛词、生成标题和正文
- 自动推送到 WordPress
- 自动按默认排期写成 `Scheduled`

## 5. 常用运行方式

### 5.1 使用默认排期

```bash
python -m src.cli.main workflow run 测试用例.xlsx
```

### 5.2 指定首篇发布时间
例如 24 小时后开始发布：

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24
```

### 5.3 指定每篇发布时间间隔
例如第一篇 24 小时后发布，后面每篇相隔 12 小时：

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24 --schedule-interval-hours 12
```

### 5.4 所有文章同一时间排期

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24 --schedule-interval-hours 0
```

### 5.5 仅验证流程，不调用 AI 和 WordPress

```bash
python -m src.cli.main workflow run 测试用例.xlsx --dry-run
```

## 6. 运行后看什么
命令执行成功后，重点看两处：

1. 终端摘要
2. WordPress 后台文章状态

理想结果类似：

- `生成: N 标题, N 篇文章`
- `发布: 0 已发布, N 已排期, 0 草稿, 0 跳过`

在 WordPress 后台中：

- 新文章会出现在 `Scheduled`
- 发布时间会按设置好的间隔递增
- 到点后自动变成 `Published`

## 7. 如果只生成了很少的文章
这通常不是报错，而是以下原因之一：

- Excel 里原始关键词本来就少
- 关键词扩展接口没有返回太多长尾词
- AI 筛选后保留下来的词不多

当前项目的默认逻辑更接近：

- 1 个最终关键词 -> 1 个标题 -> 1 篇文章

所以文章数量主要取决于：

1. 原始关键词数量
2. 扩展出的有效长尾词数量
3. AI 筛选后的剩余关键词数量

## 8. Prompt 修改
所有 prompt 在 `config/prompts_config.py`。

常见修改位置：

- `KEYWORD_FILTER_PROMPT`：关键词筛选逻辑
- `TITLE_GENERATOR_PROMPT`：标题生成风格
- `CONTENT_PROMPT_TECHNICAL_GUIDES`：Technical Guides 正文风格
- `CONTENT_PROMPT_INDUSTRY_INSIGHTS`：Industry Insights 正文风格
- `CATEGORY_PROMPTS`：分类和 prompt 的映射

如果只是想微调文章长度、风格或语气，优先改这里。

## 9. 关键配置文件

| 文件 | 作用 |
|------|------|
| `config/wordpress_config.py` | WordPress 连接、默认排期、分类映射 |
| `config/prompts_config.py` | Prompt 模板 |
| `config/ai_models_config.py` | AI 模型配置 |
| `config/settings.py` | 项目全局配置 |
| `.env` | API Key 和环境变量 |

WordPress 账号信息现在应写在 `.env`，不再直接写进 `config/wordpress_config.py`。

建议至少配置：

```env
WORDPRESS_URL=https://yushengco.com/
WORDPRESS_USERNAME=
WORDPRESS_PASSWORD=
WORDPRESS_APPLICATION_PASSWORD=
SCHEDULE_POSTS=true
DEFAULT_SCHEDULE_HOURS=1
DEFAULT_SCHEDULE_INTERVAL_HOURS=1
WORDPRESS_TIMEZONE=UTC
```

## 10. WordPress 分类扩展
如果你要新增文章分类：

1. 先在 WordPress 后台创建 Category
2. 在 `config/wordpress_config.py` 的 `CATEGORY_MAPPING` 里补上分类名和分类 ID
3. 在 `config/prompts_config.py` 中新增对应分类的内容 prompt
4. 在 `CATEGORY_PROMPTS` 中注册映射

## 11. 当前推荐使用方式
目前推荐你这样使用项目：

1. 准备真实 Excel 数据
2. 直接运行：

```bash
python -m src.cli.main workflow run 你的文件.xlsx
```

3. 去 WordPress 后台检查：
   - 是否成功生成 `Scheduled` 文章
   - 排期时间是否正确
   - 分类是否正确
4. 等待自动发布时间到达，确认文章自动上线

## 12. 注意事项

- `TIMEZONE = "UTC"` 是代码内部计算时间所用时区，WordPress 后台显示时间还会受站点时区影响
- 如果 WordPress 原生计划发布正常，就不再需要 GitHub Actions 去自动发布草稿
