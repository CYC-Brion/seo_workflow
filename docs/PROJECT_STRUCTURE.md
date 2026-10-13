# 目录结构与路径约定

这份文档记录的是**代码实际的行为**，不是理想设计。加新目录前先读「路径解析规则」一节 ——
这个项目曾经因为路径按当前工作目录解析而出现「看起来成功、其实写到了别处」的问题。

## 顶层布局

| 目录 / 文件 | 入库 | 说明 |
|---|---|---|
| `src/` | ✅ | 流水线代码。入口是 `src/cli/main.py`，实际编排逻辑在 `handle_workflow_run` |
| `config/` | ✅ | **Python 模块**形式的配置，不是 JSON/YAML。提示词也在 `config/prompts_config.py`，没有 `prompts/` 目录 |
| `tests/` | ✅ | pytest 用例 |
| `scripts/` | ✅ | 运维与生成工具；`scripts/archive/` 放遗留和一次性脚本 |
| `docs/` | ✅ | 文档与需求材料 |
| `keyword_library/` | ✅ | 输入关键词工作簿（体积小，随仓库版本化） |
| `output/` | ❌ 忽略 | 运行产物：`workflow_<id>.json`、`articles/`、`pdf/`、`pending_*/`；`output/archive/` 放本地一次性调试运行 |
| `data/` | ❌ 忽略 | `data/input`、`data/output/`（中间研究 JSON）、`data/cache/states/`（工作流状态） |
| `logs/` | ❌ 忽略 | `workflow.log` |
| `pic/` | ❌ 忽略 | 编辑图片库，`pic/editorial_library/`（约 566MB，**绝不能入库**） |
| `.env` | ❌ 忽略 | 真实凭证。模板见 `.env.example` |

## src/ 内部

- `src/cli/main.py` —— CLI 入口与六步流水线的编排
- `src/core/` —— `base_node.py`（节点基类）、`workflow_engine.py`、`state_manager.py`、`task_scheduler.py`
- `src/modules/` —— `excel_reader/`、`keyword_expander/`、`keyword_filter/`、`title_generator/`、`content_generator/`、`wordpress_integration/`
- `src/enhanced_features/image_integration/` —— `editorial_image_library.py`（图库选择）
- `src/utils/` —— `logger.py`、`config_loader.py`、`ai_client.py`、`exception_handler.py`
- `src/api/` —— **空壳**，`main.py` 及各 `__init__.py` 都是 0 字节，实际入口是 `src/cli/`。同样地 `src/enhanced_features/prompt_management/` 也是空壳

## 路径解析规则

**唯一锚点是 [`config/settings.py`](../config/settings.py) 的 `BASE_DIR`（`Path(__file__).parent.parent`）。**

不要写 CWD 相对的字符串路径（`"output/..."`、`"data/cache/states"`）。这类写法只在
「从仓库根启动」时正确，换个工作目录就会静默写到别处、或读不到输入。

- 运行时代码：`from config.settings import BASE_DIR`，再从它派生。
- 独立脚本：`ROOT = Path(__file__).resolve().parents[1]`，再从它派生。
- `config/settings.py` 也导出了 `DATA_DIR` / `OUTPUT_DIR` / `CACHE_DIR` / `LOGS_DIR`。

### 两个「output」不要合并

这是这套布局里最容易踩的坑：

- **`<仓库根>/output/`** —— CLI 的运行产物（`workflow_*.json`、`articles/`）。
  `scripts/schedule_pending_articles.py` 和 `scripts/build_article_keyword_queue.py`
  都从这个位置读 `workflow_*.json`。
- **`data/output/`** —— `config.settings.OUTPUT_DIR` 指向这里，放的是**中间研究产物**
  （Google Ads 关键词研究 JSON、待发布队列 JSON）。

两者名字像但用途不同。把 CLI 的输出目录改成 `settings.OUTPUT_DIR` 会让那两个脚本读不到文件。

### import 时就会建目录

`config/settings.py` 在 **import 时**就 `mkdir` 了 `data/input`、`data/output`、`data/cache`、`logs/`；
`src/utils/logger.py` 在 import 时打开日志文件；`src/core/state_manager.py` 在 import 时建状态目录。

后果：改了路径引用却没改全时，旧位置会被静默重建，看起来一切正常。**验证路径改动必须实际跑一次
流水线并检查文件落点，光跑测试不够。**

## 已移除的东西

- **GitHub Actions 自动发布** —— `.github/workflows/auto-publish.yml` 已删除。
  发布只走本地 CLI + WordPress 原生 future 排期，仓库不会再自行发布任何内容。
  现在 `.github/workflows/` 下只有 `secret-scan.yml`。
- **历史中的 `.env`** —— 曾经有 3 个提交包含真实凭证。已在历史改写中清除，
  并配了 `secret-scan.yml` 防复发。

## scripts/archive/

存放已被取代或一次性的脚本：`run-all-batches.bat`、`run-p3b1.bat`、
`schedule_publish.py`、`setup_scheduled_task.ps1`（其内部引用的
`schedule_publish.bat` 根本不存在，本来就是坏的）、以及
`create_google_ads_api_tool_document.py`（Google Ads Basic Access 申请用的
PDF，依赖 `reportlab`，未列入 `pyproject.toml` 的依赖，需要时自行安装）。
