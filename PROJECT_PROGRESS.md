# SEO内容自动化工作流 - 项目进度跟踪

## 项目概述
AI自动化SEO文章生成与发布工作流系统，实现从关键词提取到文章生成再到WordPress发布的完整自动化流程。

**最后更新**: 2026-05-04

## 模块划分

### 模块1：处理/拓展关键词模块
**功能范围**: 关键词的读取、扩展、筛选和整合
**子模块**:
- `excel_reader` - Excel关键词读取器
- `keyword_expander` - 关键词扩展器（Google搜索API）
- `keyword_filter` - AI关键词筛选器

### 模块2：根据关键词生成文章模块
**功能范围**: 基于关键词生成标题和文章内容
**子模块**:
- `title_generator` - AI文章标题生成器
- `content_generator` - AI文章内容生成器

### 模块3：发布模块
**功能范围**: 文章同步到WordPress和定时发布
**子模块**:
- `wordpress_integration` - WordPress API客户端

## 当前项目状态

### ✅ 已完成功能
| 模块 | 子模块 | 完成状态 | 测试状态 | 代码行数 | 备注 |
|------|--------|----------|----------|----------|------|
| 模块1 | excel_reader | ✅ 已完成 | ✅ 有测试 | 397行 | Excel读取功能完整 |
| 模块1 | keyword_expander | ✅ 已完成 | ✅ 有测试 | 645行 | 支持Google API和模拟数据 |
| 模块1 | keyword_filter | ✅ 已完成 | ✅ 有测试 | 559行 | AI筛选功能完整 |
| 模块2 | title_generator | ✅ 已完成 | ✅ 有测试 | 525行 | AI标题生成功能完整 |
| 模块2 | content_generator | ✅ 已完成 | ✅ 有测试 | 616行 | AI内容生成功能完整 |
| 模块3 | wordpress_integration | ✅ 基础完成 | ✅ 有测试 | 1155行 | WordPress REST API客户端和发布器 |

### 📋 待开发/测试任务

#### 模块1：处理/拓展关键词模块 ✅ 基本完成
- [x] **excel_reader模块** - 开发完成，有测试
  - [x] Excel文件读取功能（397行代码）
  - [x] 关键词列自动识别
  - [x] 数据验证和清洗
  - [x] 统计信息记录
  - [x] 单元测试覆盖

- [x] **keyword_expander模块** - 开发完成，有测试
  - [x] Google搜索API集成（645行代码）
  - [x] 模拟数据备用方案
  - [x] 请求延迟控制
  - [x] 扩展结果合并
  - [x] 单元测试覆盖

- [x] **keyword_filter模块** - 开发完成，有测试
  - [x] AI模型集成（559行代码）
  - [x] 批量处理优化
  - [x] 置信度阈值筛选
  - [x] 备用模型支持
  - [x] 单元测试覆盖

#### 模块2：根据关键词生成文章模块 ✅ 基本完成
- [x] **title_generator模块** - 开发完成，有测试
  - [x] 创建AI标题生成器类（525行代码）
  - [x] 集成AI模型API
  - [x] 实现Prompt模板管理
  - [x] 添加单元测试
  - [x] 支持批量处理和错误恢复

- [x] **content_generator模块** - 开发完成，有测试
  - [x] 创建AI内容生成器类（616行代码）
  - [x] 集成AI模型API
  - [x] 实现HTML格式输出
  - [x] 控制文章字数（约1500字）
  - [x] 添加单元测试

#### 模块3：发布模块 ✅ 基础完成
- [x] **wordpress_integration模块** - 基础开发完成
  - [x] 创建WordPress API客户端 (592行代码)
  - [x] 实现文章同步功能 (518行发布器代码)
  - [x] 支持定时发布功能
  - [x] 添加错误处理和重试机制
  - [x] 添加单元测试 (653行测试代码)
  - [ ] 媒体上传功能（基础框架已实现）
  - [ ] XML-RPC完整实现（REST API已完整）

### 🔄 集成测试需求
- [x] 模块1完整流程测试（Excel → 扩展 → 筛选）✅ **已完成 2026-03-04**
- [x] 模块1+2集成测试（关键词 → 标题 → 文章）✅ **已完成 2026-03-04**
- [ ] 完整端到端测试（Excel → WordPress）
- [ ] 性能测试（批量处理能力）
- [ ] 错误处理和恢复测试

## 开发优先级和计划

### 阶段1：开发模块2 - 文章生成模块（已完成）
1. **开发title_generator模块** - 从零开始开发标题生成器
   - 参考现有AI模块设计模式
   - 集成AI模型API
   - 实现Prompt模板管理
   - 添加单元测试

2. **开发content_generator模块** - 从零开始开发内容生成器
   - 设计文章生成逻辑
   - 实现HTML格式输出
   - 控制文章质量和字数
   - 添加单元测试

### 阶段2：开发模块3 - 发布模块 ✅ 已完成
1. **开发wordpress_integration模块** - WordPress API客户端已创建
   - ✅ 实现WordPress REST API客户端 (592行代码)
   - ✅ 实现文章同步和发布功能 (518行发布器代码)
   - ✅ 支持定时发布功能
   - ✅ 添加错误处理机制和重试逻辑
   - ✅ 添加单元测试 (653行测试代码)
   - ⚠️ 媒体上传功能（基础框架已实现，需要完整实现）
   - ⚠️ XML-RPC客户端（基础框架已实现，需要完整实现）

### 阶段3：集成测试和优化
1. ✅ 模块1内部集成测试验证 (已完成 2026-03-04)
2. 模块1+2集成测试（关键词 → 标题 → 文章）
3. 端到端集成测试（Excel → WordPress）
4. 性能优化和稳定性提升

### 阶段4：增强功能开发
1. Prompt管理模块
2. 图片插入功能
3. 多AI模型调度

## 技术债务和注意事项

### 已知问题
1. **Google API限制**: keyword_expander需要配置有效的API密钥，否则使用模拟数据
2. **AI成本控制**: keyword_filter需要监控AI调用成本
3. **错误处理**: 需要完善各模块的错误处理和恢复机制

### 配置要求
1. 需要配置`config/`目录下的配置文件
2. 需要Google API密钥（可选）
3. 需要AI模型API密钥（OpenAI/Claude等）
4. 需要WordPress站点配置

## 最近测试结果 (2026-03-04)

### 模块1完整工作流测试 ✅ 成功完成
**测试文件**: `test_module1_workflow.py`
**测试环境**: Python 3.10.18 (py10环境)
**测试流程**: Excel读取 → 关键词扩展 → AI关键词筛选

#### 测试结果
- **Excel读取**: 成功读取3个关键词 (`hardware`, `lamp holder`, `Lighting accessories`)
- **关键词扩展**: 3个原始关键词扩展为33个关键词（30个扩展）
- **AI筛选**: 33个关键词全部保留（100%相关率）
- **验证通过**: 所有步骤完成，输出格式正确，数据完整性验证通过

#### 测试详情
- **扩展关键词示例**:
  - `hardware` → `metal hardware manufacturers`, `metal hardware supplies`
  - `lamp holder` → `lamp holder suppliers`, `lamp holder wholesale`
  - `Lighting accessories` → `lighting accessories manufacturers`, `led lighting accessories`
- **性能指标**:
  - 扩展比率: 11.00 (扩展后/原始)
  - 筛选比率: 1.00 (筛选后/扩展后)
  - 整体比率: 11.00 (筛选后/原始)
- **测试报告**: [module1_actual_test_report_20260304.md](module1_actual_test_report_20260304.md)

#### 关键发现
1. **Excel文件格式正确**: 列名为`keywords`，包含3个关键词
2. **模拟数据工作正常**: 关键词扩展器正确使用模拟数据生成扩展
3. **AI模拟客户端工作正常**: 筛选器在测试模式下正确运行
4. **编码问题已解决**: 修复Windows控制台Unicode字符显示问题

## 测试覆盖情况

### 现有测试
- `tests/test_excel_reader/test_excel_processor.py` - Excel读取器测试
- `tests/test_keyword_expander/test_keyword_expander.py` - 关键词扩展器测试
- `tests/test_keyword_filter/test_ai_filter.py` - AI关键词筛选器测试
- `tests/test_integration/test_three_node_workflow.py` - 集成测试
- `tests/test_title_generator/test_ai_title_generator.py` - AI标题生成器测试
- `tests/test_content_generator/test_ai_content_generator.py` - AI内容生成器测试
- `tests/test_wordpress_integration/test_wp_api_client.py` - WordPress API客户端测试
- `tests/test_wordpress_integration/test_wordpress_publisher.py` - WordPress发布器测试

### 缺少测试
- 完整工作流端到端测试（Excel → WordPress）
- WordPress媒体上传功能测试
- WordPress XML-RPC客户端测试

## 下一步行动

### 2026-05-04 补完计划（当前进行中）

下面是要补完的内容（按执行顺序）：

#### 1. 补全 `src/modules/title_generator/__init__.py`
当前是空文件，需写入 `AITitleGenerator`、`TitleGenerationResult`、`generate_titles_with_ai` 的导出。

#### 2. 更新 `src/modules/__init__.py`
取消注释后4个模块的导入，更新 `__all__` 列表：
- `KeywordExpander` (from keyword_expander)
- `AITitleGenerator` (from title_generator)
- `AIContentGenerator` (from content_generator)
- `WordPressPublisher` (from wordpress_integration)

#### 3. 实现 CLI workflow 命令 (`src/cli/main.py`)
- **`workflow run`**: 逐步串联 6 个节点执行完整 pipeline，处理数据格式转换。
  数据流：
  ```
  ExcelProcessor → list[str] keywords
    → KeywordExpander → list[str] expanded
    → AIKeywordFilter → list[str] filtered
    → AITitleGenerator → list[str] titles
    → AIContentGenerator([{"keyword":kw, "title":t}]) → list[str] HTML
    → WordPressPublisher([{"title":t, "content":c, "keyword":kw}]) → publish results
  ```
  支持 `--dry-run`（跳过 AI 和 WP 调用，使用默认数据）和 `--output-dir`（保存中间结果 JSON）。
- **`workflow status`**: 从 StateManager 加载最近状态并展示。
- **`workflow list`**: 列出所有已保存的工作流状态。
- **`workflow cancel`**: 将指定 workflow_id 标记为已取消。

#### 4. 修复 WordPress 特色图片上传 (`wordpress_publisher.py:242-252`)
当前是占位代码，仅记录日志。需实现：下载图片 URL → bytes → 调用 `wp_client.upload_media()` → 设置 `featured_media_id`。

#### 5. 更新配置
- **`config/prompts_config.py`**: 行业名称从环境变量 `SEO_INDUSTRY_NAME` 读取，默认 "Metal Hardware & Lighting Accessories Processing"
- **`config/ai_models_config.py`**: 模型名称更新为当前版本（gpt-4o-mini / gpt-4o / claude-3-5-sonnet 等）
- **`config/settings.py`**: `DEFAULT_AI_MODEL` 改为 `gpt-4o`

#### 6. 创建端到端集成测试 (`tests/test_integration/test_full_pipeline.py`)
Mock AI 客户端和 WordPress 客户端，验证 6 节点全流程数据传递正确。

#### 7. keyword_expander 优化（已完成 2026-05-04）
- [x] 添加 `requests.Session` + 指数退避重试（urllib3 Retry）
- [x] 删除 `_expand_keyword` 与 `_expand_with_google_api` 的冗余降级逻辑，合并为单链
- [x] 统一 User-Agent 为类常量
- [x] 添加 `_check_robots_txt()` 方法，请求前检查域名是否允许抓取
- [x] Google Suggest 端点缓存：记住上次成功的端点，后续优先尝试

---

## 用户需要配置的信息

完成代码补完后，跑通完整流程需要以下配置：

### API 密钥（环境变量）
| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必填） | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥（可选，用于回退） | `sk-ant-...` |
| `SEO_INDUSTRY_NAME` | 目标行业名称，用于 AI prompt | `Metal Hardware & Lighting Accessories Processing` |

### WordPress 信息 (`config/wordpress_config.py`)
| 设置 | 说明 |
|------|------|
| `WORDPRESS_URL` | WordPress 站点 URL，如 `https://your-site.com` |
| `WORDPRESS_USERNAME` | 管理员用户名 |
| `WORDPRESS_APPLICATION_PASSWORD` | 应用密码（WP 后台 → 用户 → 个人资料 → 应用程序密码） |
| `DEFAULT_CATEGORY_ID` | 默认分类 ID（默认为 1，需确认你站点上存在） |

### AI 模型选择 (`config/ai_models_config.py`)
| 节点 | 默认模型 | 回退模型 |
|------|---------|---------|
| keyword_filter | gpt-4o-mini | claude-3-5-haiku |
| title_generator | gpt-4o | claude-3-5-sonnet |
| content_generator | gpt-4o | claude-3-opus |

### Prompt 模板 (`config/prompts_config.py`)
三个 prompt（筛选/标题/内容）都硬编码了行业描述。设置环境变量 `SEO_INDUSTRY_NAME` 即可切换行业，无需手动改 prompt 文本。

### 运行命令
```bash
# Dry-run 模式（无需 API 密钥，使用默认数据走通全流程）
python -m src.cli.main workflow run 测试用例.xlsx --dry-run

# 真实运行（需要配置 API 密钥和 WordPress 信息）
python -m src.cli.main workflow run 测试用例.xlsx -o ./output

# 查看工作流状态
python -m src.cli.main workflow status
python -m src.cli.main workflow list
```

---
**文档维护说明**: 此文档用于跟踪项目开发进度，防止上下文污染。各模块应独立开发和测试，确保模块间解耦。

**更新频率**: 每次重要开发进展后更新此文档。