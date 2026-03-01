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

## 详细需求文档

### Metal Hardware & Lighting Accessories 产品PRD需求文档（仅SEO相关）
#### 1. 文档概述
##### 1.1 文档目的
本文档用于明确 Metal Hardware（五金配件）& Lighting Accessories（灯饰配件）相关的AI自动化SEO文章生成与发布工作流的核心需求、功能规格、交互逻辑、非功能需求等，作为产品设计、开发、测试等相关团队的统一工作依据，确保各环节对SEO工作流需求的认知一致，保障工作流落地符合预期。

##### 1.2 工作流定位
面向企业独立站（WordPress搭建）的SEO运营需求，构建AI自动化工作流，实现从关键词处理、文章生成到WordPress同步发布的全流程自动化，生成符合Google SEO规则的英文文章，提升独立站搜索排名，精准触达五金灯饰配件领域的潜在买家。

##### 1.3 适用范围
本文档适用于产品经理、开发工程师、测试工程师及所有参与AI自动化SEO工作流规划、开发、落地的相关人员。

##### 1.4 版本记录
|版本号|更新日期|更新人|更新内容|
|---|---|---|---|
|V1.0|【待补充】|【待补充】|初始版本，完成AI自动化SEO工作流PRD框架搭建及核心需求梳理|

#### 2. AI自动化SEO文章生成与发布工作流
##### 2.1 工作流背景与核心目标
**背景**：已通过WordPress搭建企业独立站，需构建AI自动化工作流，完成SEO英文文章的生成与发布，降低人工运营成本，提升独立站在Google等搜索引擎的排名，精准触达Metal Hardware & Lighting Accessories领域的潜在买家。

**核心目标**：实现“关键词上传→关键词扩展→关键词筛选→标题生成→文章生成→WordPress同步→定时发布”全流程自动化，所有文章为英文版本，内容贴合五金灯饰配件行业，符合Google SEO规则。

##### 2.2 完整工作流流程（核心功能需求）
###### 2.2.1 节点1：Excel关键词读取（入口功能）
- 子功能：提供Excel文件上传入口，支持常见Excel格式（.xlsx、.xls），工作流自动读取表格中的关键词（需明确表格中关键词所在列，支持用户手动选择列名），读取完成后生成关键词列表，供后续步骤调用。
- 交互逻辑：用户上传Excel文件→系统提示“上传成功”并自动解析文件→用户确认关键词所在列→系统生成关键词列表，显示关键词数量、预览前10条关键词→用户确认后进入下一步（关键词扩展）；若解析失败，提示“文件格式错误”“未检测到关键词列”等异常信息，引导用户重新上传或调整表格。
- PRD图对应：业务流程图（Excel上传→解析→关键词列选择→关键词列表生成）、原型图（Excel上传入口页面、关键词列选择页面、关键词列表预览页面）。
- 约束：Excel文件大小不超过10MB，单次上传关键词数量不超过100个，避免系统负载过高。

###### 2.2.2 节点2：关键词扩展（Google下拉框采集）
- 子功能：系统自动将节点1读取的每个关键词，依次输入Google搜索框，采集搜索框下拉推荐的关键词，完成关键词扩展；扩展后的关键词与原关键词汇总，生成初步关键词池。
- 交互逻辑：用户确认原关键词列表后，点击“开始扩展”→系统自动调用Google搜索接口（需配置接口权限），逐一生成关键词下拉推荐内容→采集完成后，显示扩展后的关键词池（区分原关键词与扩展关键词）→用户可预览、手动删除明显无关的关键词（可选）→进入下一步（关键词筛选）。
- 技术说明：需解决Google接口调用限制，避免IP被封禁；若接口调用失败，提供手动输入扩展关键词的备用入口。
- PRD图对应：业务流程图（关键词输入→Google下拉采集→关键词池生成→预览编辑）。

###### 2.2.3 节点3：关键词筛选与整合（AI辅助）
- 子功能：调用AI模型，根据预设Prompt，排除关键词池中与Metal Hardware & Lighting Accessories Processing无关的关键词，整合原关键词与有效扩展关键词，生成最终可用关键词列表；支持用户手动调整（添加、删除、修改）最终关键词。
- 固定Prompt（嵌入可编辑模块）：You are an SEO specialist and professional content writer. Your main task is to extract search keywords for search engines that match Metal Hardware & Lighting Accessories Processing.
- 交互逻辑：系统自动将关键词池传入AI模型→AI按Prompt筛选无关关键词，生成筛选报告（说明删除的无关关键词及原因）→系统整合有效关键词，生成最终列表→用户预览筛选结果，可手动调整→确认后进入下一步（标题生成）。
- PRD图对应：业务流程图（关键词池→AI筛选→筛选报告→手动调整→最终关键词列表）。

###### 2.2.4 节点4：文章Title生成（AI驱动）
- 子功能：基于最终关键词列表，调用AI模型，为每个关键词生成3个符合要求的英文标题，标题需贴合行业、优化SEO、吸引点击，无内容重叠，严格遵循预设Prompt规则。
- 固定Prompt（嵌入可编辑模块）：
  - System Prompt：You are a specialist well-versed in the Metal Hardware & Lighting Accessories Processing and a professional content writer who generates compelling blog post titles that capture readers' attention based on specified keywords. While leveraging industry knowledge, prioritize natural phrasing and titles appropriate for the content—there is no need to include the industry name in the title. Create titles that incorporate elements of specificity, uniqueness, and engagement to encourage readers to click, while also optimizing them for search engines.
  - User Prompt：
    1. Some keywords are recommended by search engines, which may include synonyms or similar terms. Even if there are multiple keywords with the same meaning, create blog post titles based on the keywords from unique perspectives or different angles to introduce industry knowledge and professional concepts in an easy-to-understand manner, while ensuring the content does not overlap.
    2. When recommended keywords have different meanings, create titles for independent themes based on each keyword.
    3. Always include the keywords into the title.
    4. Titles should be engaging to attract user interest and clicks. Use diverse styles such as question forms or opinion-based prompts.
- 交互逻辑：用户确认最终关键词列表后，点击“生成标题”→AI模型按Prompt为每个关键词生成3个标题→系统显示所有标题（按关键词分组），标注对应关键词→用户可预览、手动修改标题（支持删除、编辑）→确认标题后进入下一步（文章内容生成）。
- 约束：标题为纯英文，长度控制在50-80个字符，避免过长或过短，不包含无关行业词汇。
- PRD图对应：业务流程图（最终关键词→AI生成标题→标题预览编辑→确认标题）、原型图（标题生成结果预览页面）。

###### 2.2.5 节点5：文章内容生成（AI驱动，英文）
- 子功能：基于节点4确认的标题，调用AI模型，生成对应的英文SEO文章，严格遵循预设Prompt规则，确保内容贴合五金灯饰配件行业、符合Google SEO要求、结构清晰、字数达标，输出指定格式。
- 固定Prompt（嵌入可编辑模块）：
  - System Prompt：You are a specialist well-versed in the Metal Hardware & Lighting Accessories Processing field and a professional content writer. Your role is to create engaging blog posts that provide valuable information to readers, based on the specified title and target keywords. Leverage industry knowledge related to the title, incorporate content that readers will find beneficial, and generate clear, compelling content that draws them in.
  - User Prompt：
    ##### Summary
    Based on each title, create high-quality English articles with SEO in mind.
    ##### Background
    You are an experienced SEO specialist with a deep understanding of the Metal Hardware & Lighting Accessories Processing field. Create high-quality SEO articles that comply with Google's SEO rules based on the following requirements. The article should be engaging and encourage readers to click.
    ##### Goals
    Follow the instructions below to create articles that match the theme, address user search intent, and improve website search rankings by adhering to SEO rules of major search engines like Google.
    1. Target Audience: Potential Buyers for Metal Hardware & Lighting Accessories
    2. Target Keyword: the keywords processed before
    - Note: Use the keyword naturally throughout the title and body. Avoid mechanical keyword stuffing; Additionally, paraphrasing should be appropriately used and word order adjusted to ensure that the English expression is smooth and natural, aligning with the reading habits of native English speakers.
    3. Use bullet points, headings, and lists to structure the article clearly for easy reader comprehension.
    4. The article should be around 1,500 words in length
    5. Naturally include the target keyword in the opening and concluding paragraphs of the article.
    ##### Article Details
    1. Title：Use the title generated in the previous node and output it in H1 format.
    2. Introduction:  Clarify the article's title and attract readers' interest. Briefly explain the article's purpose and craft an introduction that makes readers want to continue reading.
    3. Body:
    - Structure the article with 3-5 H2 headings, each providing logically organized content. Develop information step-by-step for clarity.
    - Include at least 3 paragraphs under each H2 heading to explain and deepen the content specifically.
    - Focus primarily on introducing industry knowledge and concepts, providing case studies or practical background as needed.
    4. Conclusion:（around 200 words）
    - Concisely summarize the article's key points and emphasize important themes and keywords.
    - Propose actions that prompt readers to take the next step or adopt a new perspective, such as suggesting problem-solving methods or next steps.
    ##### Article Format
    1. Use an h1 tag for the main heading (h1).
    2. Use h2 tags for subheadings (h2) with a font size of 24px.
    3. Bold all headings.
    4. Use p tags for the body text with a font size of 16px.
    5. Apply style="line-height: 2" to all HTML elements (<p>, <h>, <ul>, <div>, <li>, etc.).
    6. Output the article in HTML format. Include only the article's body in HTML tags, without any explanations or AI notes. The final response should be the formatted HTML code for the article body.
    ##### Final output: 
    "title": input.title,  
    "keyword": input.keyword, 
    "content": "HTML-formatted article content" (Do not contain the main heading!), 
    "slug": "concise-slug-related-to-article",  
    "excerpt": "80-100 character summary of the article"
- 交互逻辑：用户确认标题后，点击“生成文章”→AI模型按Prompt生成对应英文文章，输出指定格式（包含title、keyword、content、slug、excerpt）→系统显示文章预览（可查看HTML格式和可视化效果）→用户可手动编辑文章内容、调整slug和excerpt→确认文章无误后，进入下一步（同步WordPress）。
- 约束：文章为纯英文，字数控制在1400-1600字，关键词自然分布，无堆砌，HTML格式符合要求，excerpt为80-100字符的英文摘要，slug简洁且与文章主题相关（全小写、无特殊符号、用连字符连接）。
- PRD图对应：业务流程图（确认标题→AI生成文章→文章预览编辑→确认文章）、原型图（文章预览页面、HTML编辑页面）。

###### 2.2.6 节点6：文章同步与定时发布（对接WordPress）
- 子功能1：文章同步至WordPress后台，生成草稿，无需手动操作；子功能2：支持对生成的草稿设置定时发布时间，实现自动化发布。
- 交互逻辑：用户确认文章后，点击“同步至WordPress”→系统提示“请输入WordPress账号配置信息”（URL、用户名、密码、API密钥）→用户输入并确认配置→系统验证配置有效性，验证通过后，自动将文章同步至WordPress后台，生成草稿（标注“AI生成”标签）→同步成功后，用户可选择“立即发布”或“定时发布”→选择定时发布时，设置具体发布日期和时间（支持精确到小时、分钟），系统保存设置，到点自动发布；同步失败时，提示失败原因（如配置错误、网络问题），引导用户调整后重新同步。
- 技术说明：需对接WordPress API，确保文章格式（HTML、图片）同步无误；定时发布功能需系统后台持续运行，或对接定时任务调度工具。
- 约束：WordPress账号需具备文章发布权限；定时发布时间需设置在当前时间之后，支持批量设置多个文章的发布时间（按顺序顺延）。
- PRD图对应：业务流程图（确认文章→输入WordPress配置→验证配置→同步草稿→设置发布方式→完成）、原型图（WordPress配置页面、定时发布设置页面）。

##### 2.3 模糊需求解决方案
###### 2.3.1 Prompt灵活修改方案
采用“Prompt管理模块”设计，不将Prompt写死在代码中，单独嵌入工作流后台，支持用户灵活观测、修改、保存不同Prompt，具体如下：
- 新增“Prompt管理”模块，按工作流节点分类（关键词筛选、标题生成、文章生成），每个节点对应独立的Prompt编辑框，显示当前使用的Prompt内容。
- 支持用户编辑Prompt，编辑后可保存为“版本”（如“标题生成Prompt-V1”“标题生成Prompt-V2”），方便切换不同版本，观测AI生成效果。
- 支持Prompt预览功能，编辑后可快速生成测试内容（如测试标题、测试段落），验证Prompt效果后再应用到正式工作流。
- 保留Prompt修改日志，记录每次修改的内容、修改人、修改时间，便于追溯和回滚至历史版本。

###### 2.3.2 文章图片插入功能实现
支持两种图片插入方式，用户可在工作流设置中选择默认方式，也可在文章生成后手动调整，具体如下：
- 方式1：调用WordPress媒体库图片（推荐）
  - 功能：用户提前在WordPress媒体后台上传五金灯饰配件行业通用图片（如产品图、生产场景图），系统自动读取媒体库图片URL，在文章前部（引言之后、正文之前）随机插入1张图片，实现插图效果。
  - 配置：在工作流设置中，用户可设置图片插入位置（文章前部/指定H2标题后）、图片尺寸（统一尺寸，如800*450px）、图片alt属性（自动提取文章关键词，优化SEO）。
- 方式2：AI生成贴合文章内容的图片
  - 功能：调用AI图片生成模型（如MidJourney、DALL·E），根据文章标题和核心内容，生成贴合主题的英文插图（如五金配件生产流程、灯饰配件安装场景），自动插入文章指定位置。
  - 配置：用户需在工作流后台配置AI图片生成模型的API密钥，设置图片尺寸、风格（贴合行业，简洁专业）、生成数量（1张/篇），生成后系统自动上传至WordPress媒体库，再插入文章。
  - 补充：支持手动替换图片，文章生成后，用户可上传自定义图片替换AI生成或媒体库调用的图片。

###### 2.3.3 多AI模型调用方案
支持在不同工作流节点调用不同的AI模型，根据各节点需求选择最优模型，提升生成效果，具体设计如下：
- 节点3（关键词筛选）：推荐调用轻量化AI模型（如GPT-3.5），高效筛选无关关键词，降低成本，兼顾速度和准确性。
- 节点4（标题生成）：推荐调用擅长文案创作的AI模型（如GPT-4、Claude），生成更具吸引力、更贴合SEO的标题，提升点击量。
- 节点5（文章生成）：推荐调用具备行业深度的AI模型（如GPT-4 Turbo、通义千问行业版），确保文章内容专业、逻辑清晰，贴合五金灯饰配件行业知识，符合Google SEO规则。
- 配置：在工作流后台新增“AI模型配置”模块，每个节点可独立选择AI模型，输入对应模型的API密钥，支持切换模型、测试模型效果，根据生成质量灵活调整。

#### 3. 非功能需求
- 性能需求：单篇文章生成时间≤3分钟，100个关键词批量处理（含扩展、筛选、标题、文章生成）≤1小时；WordPress同步响应时间≤10秒，定时发布无延迟。
- 安全性需求：WordPress账号配置信息加密存储，不泄露；AI模型API密钥加密管理；生成的文章内容需过滤违规、低俗、侵权内容，图片需确保版权合规（AI生成图片需选择可商用模型）。
- 可维护性需求：工作流各节点可独立启停，便于故障排查；支持日志记录（各节点操作日志、AI生成日志、同步日志），便于追溯问题；支持版本更新，不影响现有工作流运行。
- 兼容性需求：支持与主流WordPress版本（6.0及以上）对接，确保同步功能正常；支持不同AI模型API对接，适配常见模型接口规范。

#### 4. 约束条件与注意事项
- 关键词相关：上传的关键词需与五金灯饰配件行业相关，避免上传无关关键词，否则会影响扩展、筛选及文章生成质量。
- AI生成相关：AI生成的标题、文章需用户手动审核，确认无语法错误、内容准确、贴合行业后，再同步至WordPress，避免生成不符合需求的内容。
- WordPress配置相关：若WordPress后台设置了权限限制、插件拦截，需提前关闭或配置白名单，确保工作流能正常调用API同步文章。
- 版权相关：AI生成的文章、图片需确保无版权纠纷，建议对AI生成内容进行原创性检测，避免侵权；WordPress媒体库上传的图片需具备商用版权。
- 网络相关：工作流运行需保持稳定网络，确保Google接口、AI模型API、WordPress API能正常调用，避免因网络中断导致流程失败。

#### 5. PRD图说明（可视化补充）
本文档配套以下PRD图，确保工作流逻辑清晰、可落地：
- 产品结构图：展示AI自动化SEO工作流各模块层级关系，明确系统整体框架。
- 核心业务流程图：涵盖关键词处理、标题生成、文章生成、WordPress同步等全流程，明确用户与系统的交互逻辑。
- 页面流程图：展示各功能页面之间的跳转关系，如Excel上传页面→关键词列表页面→标题生成页面→文章预览页面。
- 原型图（线框图）：展示各页面布局、元素位置、按钮样式、表单样式等，无需高保真，聚焦功能布局。
- 状态流转图：明确文章生成、同步、发布的状态变化，如“标题生成中→标题确认→文章生成中→文章确认→同步中→同步成功→定时发布/立即发布”。

#### 6. 附录
##### 6.1 术语定义
- AI自动化SEO工作流：通过AI技术实现从关键词读取、扩展、筛选，到文章生成、同步WordPress后台并定时发布的全流程自动化，核心用于提升企业独立站SEO排名。
- Prompt：AI生成内容的指令话术，用于引导AI生成符合需求的关键词、标题、文章等内容。
- Slug：文章的URL友好标识，简洁且与文章主题相关，用于优化SEO检索。
- Metal Hardware & Lighting Accessories：五金配件及灯饰配件，为文章核心主题，所有生成内容需围绕该领域展开。

##### 6.2 联系方式
产品负责人：【待补充】
开发负责人：【待补充】
测试负责人：【待补充】

（注：文档部分内容可能由 AI 生成)## 许可证
MIT License
