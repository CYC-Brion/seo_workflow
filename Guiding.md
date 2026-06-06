# SEO 内容自动化工作流操作指南

## 1. 项目目的
这个项目用于把 Excel 关键词表自动处理成可发布到 WordPress 的 SEO 文章，主流程是：

1. 读取 Excel 关键词并去重
2. 可选读取同文件里的 `plan` 表，组装混合发文顺序
3. 扩展长尾关键词
4. AI 筛选行业相关关键词
5. AI 生成标题
6. AI 生成正文并自动插入站内链接
7. 计算排期并发布到 WordPress

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
- 如果要跑混合方案，可以额外加 `plan` 表，常用列有 `week`、`lane`、`keyword`、`category`、`direction`、`title_angle`、`internal_link_targets`
- `lane` 只是运营分层标签，不会单独改变代码行为；真正控制标题和内容角度的是 `direction` / `title_angle`

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

- 自动读取 Excel，并先做关键词去重
- 如果存在 `plan` 表，则优先按 `plan` 组装 pillar / 重点任务，再补上通过筛选的 ordinary 关键词
- 自动扩词、筛词、生成标题和正文
- 正文阶段会自动插入站内链接
- 自动计算排期并推送到 WordPress
- 自动按默认排期写成 `future`，在 WordPress 后台显示为 `Scheduled`
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
- Excel 读取阶段已经去重，重复关键词不会被重复保留
- 关键词扩展接口没有返回太多长尾词
- AI 筛选后保留下来的词不多
- 如果你用了 `plan` 表，但对应关键词没有通过筛选，也不会进入最终发文任务

当前项目的默认逻辑更接近：

- 1 个最终关键词 -> 1 个标题 -> 1 篇文章

所以文章数量主要取决于：

1. 原始关键词数量
2. 扩展出的有效长尾词数量
3. AI 筛选后的剩余关键词数量

如果你想让同一个 pillar 词输出多篇文章，不要在 `keywords` 表里重复堆同一个词；应该把它放进 `plan` 表里，用不同的 `direction` / `title_angle` 生成多条任务。

## 8. Prompt 修改
所有 prompt 在 `config/prompts_config.py`。

常见修改位置：

- `KEYWORD_FILTER_PROMPT`：关键词筛选逻辑
- `TITLE_GENERATOR_PROMPT`：标题生成风格
- `CONTENT_PROMPT_TECHNICAL_GUIDES`：Technical Guides 正文风格
- `CONTENT_PROMPT_INDUSTRY_INSIGHTS`：Industry Insights 正文风格
- `CATEGORY_PROMPTS`：分类和 prompt 的映射

当前推荐的内容调教方向：

- `pillar` 文章优先写成 supplier comparison、buyer checklist、factory capability、OEM/ODM decision 这类高商业意图内容
- `ordinary` 文章优先写成 process、finish、QC、tolerance、application 这类长尾技术内容
- 正文要更像制造商或 sourcing advisor 的经验输出，而不是泛百科文章
- 每篇文章都要回答买家为什么要关心、哪里容易踩坑、要验证什么、下一步应该看哪个页面或发起什么询盘

如果只是想微调文章长度、风格或语气，优先改这里。

## 9. 关键配置文件

| 文件 | 作用 |
|------|------|
| `config/wordpress_config.py` | WordPress 连接、默认排期、分类映射 |
| `config/prompts_config.py` | Prompt 模板 |
| `config/ai_models_config.py` | AI 模型配置 |
| `config/settings.py` | 项目全局配置 |
| `.env` | API Key 和环境变量 |

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

## 12. 企业 SEO 获客三阶段策略

如果你的目标是通过 SEO 获取企业询盘，建议不要只追求流量，也不要一开始就把所有关键词都做成扩张型内容。更适合你的，是“默认稳健 + 少量支柱词扩张”的混合方案。

### 12.1 第一阶段：先搭转化底座

这个阶段的目标不是追求最大流量，而是确保来了流量能转化。

重点先完善这些页面：

1. 首页
2. 产品分类页
3. 核心产品页
4. 服务页
5. 关于我们
6. 联系我们 / RFQ 页面

这个阶段要重点补齐：

- 工厂实力说明
- 产品参数和应用场景
- 认证、测试、专利、案例
- 明确的询盘入口
- FAQ 和常见问题

### 12.2 第二阶段：按混合方案铺内容

这个阶段开始做内容增长，但不是所有词都一视同仁。真正落地时，建议用 `plan` 表控制发文顺序和方向，而不是只靠 `keywords` 表本身。

建议分两类：

- 普通词：保持 1 个关键词 -> 1 个标题 -> 1 篇文章
- 支柱词：1 个关键词在 `plan` 表里出现 2 到 3 次，用不同 `direction` / `title_angle` 拆成 2 到 3 篇文章

适合做支柱扩张的关键词类型：

- lighting hardware manufacturer
- OEM vs ODM lighting hardware
- lighting hardware supplier comparison
- how to choose a reliable lamp parts manufacturer

适合继续稳健推进的关键词类型：

- 产品词
- 材料词
- 结构件词
- 规格词

### 12.3 第三阶段：根据数据放大有效主题

这个阶段的核心是用数据决定下一批内容，而不是凭感觉堆量。

重点看这些指标：

- 搜索曝光量
- 点击率
- 页面停留时间
- 询盘量
- 哪些主题能带来高意图访问

如果某类词带来更多询盘，就继续围绕它做同主题扩展；如果某些词只有流量没有转化，就补充页面的 CTA、FAQ、案例和对比内容。

## 13. 适合你官网的 SEO 获客路线图

下面这套路线图更适合你现在的站点结构，可以直接和当前工作流配合使用。

### 13.1 第 1 阶段：先把转化页面做扎实

建议先做 1 到 2 周，完成这些页面：

1. 首页：突出工厂、产品、能力、询盘入口
2. 产品分类页：Floor Lamp Sets、Wall Lamp Sets、Table Lamp Sets、Custom Made Parts 等
3. 核心产品页：每个核心产品至少 1 页，写清材料、尺寸、工艺、应用
4. 服务页：ODM / OEM / 深度合作 / 设计支持 / QC / 交付
5. 联系页：表单、邮箱、电话、WhatsApp、询盘按钮

这一阶段的目标是：让任何搜索进来的企业客户，都能快速看懂你能做什么、怎么合作、怎么联系你。

### 13.2 第 2 阶段：内容流量和转化并行

建议从第 3 到第 6 周开始执行，内容上采用混合方案：

- 普通词继续走 1 个关键词 -> 1 个标题 -> 1 篇文章的稳健模式
- 支柱词不要靠 `keywords` 表重复堆词，而是放到 `plan` 表里，用不同的 `direction` / `title_angle` 生成多篇
- 每周先发 3 篇普通词内容，再补 1 到 2 篇支柱词专题
- 每篇文章都反向链接到相关产品页或服务页

内容配比建议：

- 60% 产品与技术说明
- 25% 采购与供应商对比
- 15% 行业趋势与品牌能力说明

这阶段文章长度建议保持在 1200 到 1800 字，支柱专题可以到 1800 到 2200 字，但前提是内容角度必须明显不同，不能重复。

### 13.3 第 3 阶段：放大有效词，做专题簇

当你看到某些页面开始稳定带来曝光和询盘后，就可以把它们做成专题簇。

举例：

- 主词：lighting hardware manufacturer
- 子词：lighting hardware material selection / lighting hardware supplier comparison / OEM vs ODM lighting hardware
- 支撑页：产品页、服务页、FAQ、案例页

这个阶段要做的不是无脑加文章，而是把一个主题做深、做全、做成搜索引擎和客户都能读懂的专题。

### 13.4 Excel 和工作流怎么配合

实际操作上建议你这样分：

1. `standard_keywords.xlsx`：普通词，走稳健模式，默认 1:1
2. `pillar_keywords.xlsx`：支柱词种子库，配合 `plan` 表写出不同方向
3. `plan` 表：决定发文顺序、`lane`、`direction`、`title_angle`、内链目标
4. 每次发文前先确认分类是 `Technical Guides` 还是 `Industry Insights`
5. 先发标准词，再发支柱词，最后按数据回补同主题内容

### 13.5 你当前最适合的执行顺序

推荐顺序是：

1. 先完成转化底座
2. 再用稳健模式持续发普通关键词内容
3. 再挑 3 到 5 个支柱词做扩张，并用 `plan` 拆方向
4. 再根据询盘数据决定是否扩大专题簇

这样做的好处是：不会因为追流量把站点写散，也不会因为太保守而错过核心主题的流量机会。

### 13.6 第 2 阶段 8 周执行表

这部分可以直接作为当前工作流的发文排期。建议每周发 3 篇，其中 2 篇走普通词稳健模式，1 篇放到支柱词专题簇里，先铺产品与技术流量，再把采购决策词补进来。真正跑的时候，优先用 `keyword_library/seo_phase3_long_cycle.xlsx`，因为它已经把 pillar 优先和 ordinary 后补的长周期规则固定下来了。

如果你要直接跑工作流，可以把下面这 24 个关键词放进一个新的 Excel 文件里，保留 `keywords` 和 `category` 两列即可；其他列是给你做排期和人工检查用的，工作流会自动忽略。

这里的 24 个词不是全部内容库，而是第 2 阶段的“种子词”：8 周 × 每周 3 篇 = 24 篇起跑内容。它们的作用是先把 3 条内容通道铺起来，后面再根据表现继续扩展同主题的二级词和 FAQ 词。

| 周次 | 普通词 | 支柱词 | 核心目标 | 主要内链落点 |
|------|--------|--------|----------|--------------|
| 第 1 周 | lighting hardware components guide / lighting hardware supplier comparison | lighting hardware manufacturer | 先把主词做成支柱，再用比较词接住决策流量 | 首页、About Us、Services |
| 第 2 周 | lighting manufacturing process / lighting fixture assembly process | lighting hardware sourcing guide | 建立制造流程与采购流程信任 | 首页、Services、RFQ 页面 |
| 第 3 周 | floor lamp parts manufacturer / floor lamp kit accessory manufacturer | floor lamp parts supplier review criteria | 抢占 Floor Lamp 相关长尾流量 | Floor Lamp Sets、Custom Made Parts |
| 第 4 周 | wall lamp parts manufacturer / wall lamp bracket hardware | wall lamp accessory supplier selection | 把墙灯结构件和采购词串起来 | Wall Lamp Sets、Services |
| 第 5 周 | table lamp parts supplier / table lamp support structure | table lamp hardware quality comparison | 覆盖台灯结构与质量决策词 | Table Lamp Sets、About Us |
| 第 6 周 | custom metal hardware parts / machined metal parts factory | OEM vs ODM lighting hardware | 推进定制与合作模式转化 | Custom Made Parts、Services、RFQ |
| 第 7 周 | aluminum lamp tube components / steel lamp tube supplier | custom lighting parts factory comparison | 把管件材料与供应商比较结合起来 | Tubes、Panels、Services |
| 第 8 周 | surface treatment for lighting hardware / lighting parts quality control | factory audit checklist for lighting parts | 用工艺与 QC 词收口，增强成交信任 | 首页、QC 相关页、Contact |

建议直接跑的 Excel 文件名可以用：`keyword_library/seo_phase3_long_cycle.xlsx`

这个文件里建议至少有两张表：

1. `keywords`：给工作流直接读取，至少包含 `keywords`、`category`
2. `plan`：给你人工查看，包含 `week`、`lane`、`keyword`、`category`、`title_angle`、`internal_link_targets`

执行时建议保持以下规则：

1. 每篇文章只围绕 1 个主关键词，不要在一篇里塞太多相近词。
2. 技术文写“是什么、怎么做、为什么重要”，决策文写“怎么选、怎么比、怎么避坑”。
3. 每篇至少回链 2 个页面，优先首页、分类页、服务页、RFQ 页。
4. 如果某篇文章有明显询盘信号，下一篇就围绕同专题补 FAQ、对比或案例，而不是立刻换主题。
5. 支柱词优先做成专题簇，普通词保持 1 个关键词 -> 1 个标题 -> 1 篇文章的稳健模式。

### 13.6.1 lane 怎么跑

当前工作流本身会先读 `keywords` 表，再可选读 `plan` 表；现在 `plan` 只负责 pillar 优先级和方向覆盖，不再拦截 ordinary 关键词。实际跑法建议如下：

1. `ordinary` lane：直接放进主工作流，走默认 1:1 稳健模式
2. `pillar` lane：单独放到一个小文件里跑，优先用来做专题簇和转化页回链
3. 默认主入口是 `keyword_library/seo_phase3_long_cycle.xlsx`；`ordinary` 和 `pillar` 分拆文件只作为辅助运营文件

### 13.6.2 pillar 如何按不同方向输出

当前版本里，Excel 读取器会按关键词去重，所以同一个 `keywords` 值重复出现时，只会保留一条。也就是说，**不能靠在 `keywords` 表里重复同一个 pillar 关键词来做多方向输出**。

可落地的做法有两种：

1. 方向拆成不同种子词
   - 例如把 `lighting hardware manufacturer` 拆成 `lighting hardware manufacturer`、`lighting hardware sourcing guide`、`lighting hardware supplier comparison`、`OEM vs ODM lighting hardware`
   - 每个种子词对应一个方向，分别跑出不同文章
2. 方向由标题模板决定
   - 同一个主题簇里，分别用 `What Is`、`How to Choose`、`Comparison`、`Checklist` 这几类标题角度去跑
   - 这样即使主题接近，内容意图也会明显不同

如果你后面想让“同一个 pillar 关键词”稳定输出多个方向，正确做法是把它写进 `plan` 表多次，并让每一行带不同的 `direction` 或 `title_angle`；现有代码已经会读取这些字段。

### 13.7 标题和内容模板

建议你在当前工作流里把模板理解成“自动标题生成的提示框架”，不是人工写标题：

- 产品/技术词：What Is {keyword} / How {keyword} Works / {keyword} Explained
- 供应商/决策词：How to Choose {keyword} Supplier / {keyword} Comparison / {keyword} Checklist
- OEM/ODM 词：OEM vs ODM {keyword} / {keyword} for Custom Projects
- 质量与工艺词：{keyword} Quality Control / {keyword} Material Selection / {keyword} Surface Treatment

工作流实际执行时，标题仍然是 AI 自动生成；这些模板的作用是告诉模型每类关键词应该朝什么标题结构走，这样你在 Excel 里继续扩词也不会把内容风格打乱。

## 14. 注意事项

- 当前 WordPress 配置文件里仍有明文账号默认值，后续建议迁移到 `.env`
- `TIMEZONE = "UTC"` 是代码内部计算时间所用时区，WordPress 后台显示时间还会受站点时区影响
- 如果 WordPress 原生计划发布正常，就不再需要 GitHub Actions 去自动发布草稿
