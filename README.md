# SEO Content Automation Workflow

## 项目概述
AI自动化SEO文章生成与发布工作流系统，实现从关键词提取到文章生成再到WordPress发布的完整自动化流程。

## 核心功能
1. **Excel关键词读取** - 支持.xlsx/.xls格式文件上传，自动解析关键词
2. **Google关键词扩展** - 调用Google搜索API获取下拉推荐关键词
3. **AI关键词筛选** - 使用AI模型筛选与五金灯饰配件行业无关的关键词
4. **AI文章标题生成** - 为每个关键词生成3个英文SEO标题
5. **AI文章内容生成** - 生成约1500字英文SEO文章，输出HTML格式
6. **WordPress同步与发布** - 对接WordPress API，支持定时发布

## 增强功能
- **Prompt管理模块** - 灵活编辑和管理各节点Prompt
- **图片插入功能** - 支持WordPress媒体库图片和AI生成图片
- **多AI模型调度** - 不同节点可配置不同AI模型

## 项目结构
```
seo-content-automation/
├── config/              # 配置文件
├── src/                 # 源代码
│   ├── core/           # 核心工作流引擎
│   ├── modules/        # 工作流节点模块
│   ├── enhanced_features/ # 增强功能模块
│   ├── utils/          # 工具函数库
│   ├── api/            # API接口层
│   └── cli/            # 命令行接口
├── tests/              # 测试目录
├── examples/           # 使用示例
├── notebooks/          # Jupyter笔记本
├── scripts/            # 可执行脚本
├── data/               # 数据目录
├── docs/               # 文档目录
└── logs/               # 日志目录
```

## 快速开始
```bash
# 1. 克隆项目
git clone <repository-url>

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置API密钥和WordPress设置
cp config/settings.example.py config/settings.py
# 编辑config/settings.py文件，填入您的API密钥和配置

# 6. 运行示例工作流
python scripts/run_workflow.py
```

## 配置说明
1. **AI模型配置** - 在config/ai_models_config.py中配置OpenAI、Claude等API密钥
2. **WordPress配置** - 在config/wordpress_config.py中配置WordPress站点URL、用户名、密码
3. **Prompt配置** - 在config/prompts_config.py中管理各节点的Prompt模板

## 许可证
MIT License
