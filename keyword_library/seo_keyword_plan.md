# SEO / GEO 关键词执行说明

## 站点定位
- 主定位：灯具五金配件、灯具结构件、定制金属部件、OEM / ODM 工厂
- 核心产品：Floor Lamp Sets、Wall Lamp Sets、Table Lamp Sets、Custom Made Parts、Tubes、Panels、Universal Joints、Machined Parts
- 内容主线：产品词、技术词、采购决策词三条线并行

## 推荐投放顺序
1. 先做高意图产品词和工厂词
2. 再做技术解释词，覆盖材料、结构、工艺、QC
3. 最后做供应商对比、OEM / ODM、采购指南类关键词

## 分类策略
- `Technical Guides`：工艺、结构、材料、质量控制、安装维护
- `Industry Insights`：采购决策、供应商比较、OEM / ODM、趋势、成本分析

## 当前可用文件
- `seo_keyword_library_full.xlsx`：完整版关键词库，作为扩库和长周期运营主参考
- `seo_phase3_long_cycle.xlsx`：唯一主运行文件，默认采用 pillar 优先、ordinary 后补的长周期模式
- `seo_phase3_long_cycle_part2..part5*.xlsx`：长周期计划的分片，用于分批运行
- `done-seo_phase3_long_cycle_part1.xlsx`：part1 已完成发布，留档
- `seo_pending_43_standard_batch.xlsx` / `seo_pending_43_hourly_schedule.xlsx`：当前待发布批次的运行队列

## Heat-First 执行规则
- `keywords` 表负责关键词库和元数据，例如 `lane`、`priority`、`cluster`、`internal_link_targets`
- `plan` 表负责重点词优先级和方向覆盖，不再是 ordinary 的排除名单
- `pillar` 继续由 `plan` 驱动；同一关键词可以按不同 `direction` 重复出文
- `ordinary` 关键词只要通过筛选，就会在 pillar 队列之后继续补发
- 当前工作流仍然是 1 个最终任务 -> 1 个标题 -> 1 篇文章

## 运营注意点
- pillar 多方向一定写在 `plan` 表里，不要靠重复关键词行实现
- ordinary 关键词主要承担覆盖和续航，不需要每个都手工写进 `plan`
- `priority` 先使用 `A / B / C`，其中 `A` 更偏高商业意图和强转化词
- `internal_link_targets` 会优先解析显式目标页，短语规则只作为回退机制

---

## 项目发布计划与进展（持续更新）

> 最后更新：2026-08-30（Asia/Shanghai）  
> 更新规则：每次关键词研究、页面上线、文章发布、内链调整、数据复盘或重大技术变更完成后，都在本节追加一条带日期的记录；未完成事项必须保留在“下一阶段”。

### 当前目标

将现有“关键词研究 → AI 内容生成 → WordPress 定时发布”能力，升级为可持续转化的 SEO 体系：

`高意图搜索词 → 专业文章 → 核心承接页 → RFQ / Contact`

现阶段不以增加文章数量为唯一目标；优先让产品、工厂能力与询盘路径承接已发布文章的流量。

### 已完成

| 日期 | 事项 | 状态 | 结果 |
|---|---|---|---|
| 2026-08-22 | Google Ads Keyword Planner 首轮美国市场研究 | 已完成 | 基于 20 个核心种子词得到 260 个候选词；保留 Google Ads 搜索量、竞争度和出价数据。 |
| 2026-08-27 | 行业规则与 AI 筛选 | 已完成 | 94 个词通过行业 / AI 筛选；排除汽车、零售、本地搜索、维修意图及明显不相关词。 |
| 2026-08-27 | 首批发文队列 | 已完成 | 经过历史关键词查重、主题簇去重和商业意图排序，形成 12 个美国市场发文主题。队列文件：`output/archive/outputs/article_keyword_queue_2026_08_27/seo_article_keyword_queue_us.xlsx`（本地归档，output/ 不入库）。 |
| 2026-08-27 | 工作流“已精选词库”模式 | 已完成 | `workflow run --use-preselected-keywords` 会跳过二次扩词和 AI 筛选，保证审核词库与实际发文一一对应。 |
| 2026-08-27 至 2026-08-28 | 首批文章发布 | 已完成 | 12 篇文章按每小时 1 篇完成发布；WordPress 文章 ID：15307、15310、15313、15316、15319、15322、15325、15328、15342、15333、15336、15339。 |
| 2026-08-30 | 首批文章索引诊断 | 已完成 | 抽查 `led-bulb-skd-suppliers-factory-verification-and-qc-checklist`：HTTP 200、canonical 自指向、`index, follow`、robots 未屏蔽、已存在于 `post-sitemap1.xml` 且博客列表有链接。Search Console 的“Google 无法识别此网址 / 未检测到推荐站点地图”表示尚未抓取，不是拒绝收录。发现 sitemap index 的 `lastmod` 早于该批文章发布，需在后续技术检查中确认 / 刷新 Rank Math 站点地图缓存。 |
| 2026-08-30 | Search Console 与 Rank Math 复核 | 已完成 | Search Console 已于 2026-08-30 成功读取 `sitemap_index.xml`，发现 546 个网页；`post-sitemap.xml` 也于 2026-08-28 成功读取并发现 201 个网址。目标文章的实际网址测试通过（“网址可编入 Google 索引”），且已提交索引请求。Rank Math sitemap 已启用、目标 URL 未被排除，设置无待保存变更；首页“Latest News”已提供该文章的上下文内链。因此当前无需重复提交 sitemap 或强制刷新设置，等待 Google 正式抓取和编入索引。 |

### 下一阶段：核心承接页 + 内链地图

#### 里程碑 A：页面盘点与 URL 决策

状态：进行中  
目标：确认现有页面中哪些可直接承担商业搜索意图；仅在必要时新建页面，避免与产品分类和服务页重复。

优先确认以下 4 类承接页：

| 承接页主题 | 搜索 / 商业意图 | 页面必须回答的问题 |
|---|---|---|
| Lighting Hardware Manufacturer / Supplier | 找灯具五金工厂、供应商 | 可做哪些灯具五金件？材料、工艺、能力、MOQ、交期和询盘方式是什么？ |
| Lamp Parts Supplier | 找灯具配件、灯座、底座与结构零件供应商 | 可供应 / 定制哪些零件？如何确认尺寸、表面处理、装配与质量？ |
| Custom Lighting Parts / OEM & ODM | 有图纸、需要打样、OEM / ODM 或定制加工 | 从 RFQ、图纸审查、样品到量产分别如何进行？ |
| Manufacturing & Quality Capability | 需要验证工厂、QC、公差和表面处理能力 | 工厂如何控制材料、工艺、公差、表面处理、检验和包装？ |

每个承接页的最低内容标准：

- 唯一的商业主关键词、H1 和 meta title / description。
- 产品 / 零件范围、材料、工艺与表面处理能力。
- MOQ、样品、交期、质量控制与定制流程。
- 真实工厂、工艺、检验或产品证据图。
- 相关产品分类链接、FAQ、`Send RFQ` / `Discuss Your Drawing` / `Request Sample` CTA。

#### 里程碑 B：首批文章内链地图

状态：待执行（须在里程碑 A 确认最终 URL 后进行）

| 已发布文章主题 | 主承接页 | 次级链接 |
|---|---|---|
| Lamp parts、lamp base、chandelier、bulb holder、lantern parts | Lamp Parts Supplier | Custom Lighting Parts / OEM & ODM；Contact / RFQ |
| Lighting components、LED lighting components | Lighting Hardware Manufacturer / Supplier | Manufacturing & Quality Capability；相关产品分类 |
| Custom lighting and hardware、LED bulb body、LED bulb SKD、LED bulb assembly | Custom Lighting Parts / OEM & ODM | Services；Contact / RFQ |
| QC、tolerance、finish、factory verification 段落 | Manufacturing & Quality Capability | 对应产品 / 零件承接页 |

每篇文章最终至少保留 3 个上下文相关链接：

1. 正文前半段链接到对应核心承接页。
2. 技术或采购建议段链接到对应产品、工艺或质量能力页。
3. 结尾链接到 Services 或 Contact / RFQ 页面。

#### 里程碑 C：内容扩张与复盘

状态：待执行

后续内容配比：

- 60% 产品、零件、材料、尺寸、公差、工艺和表面处理。
- 25% 采购决策、供应商比较、OEM / ODM、质量控制。
- 15% 工厂能力、案例、合作方式与信任内容。

发布后 2–4 周复盘一次 Google Search Console：索引状态、曝光、查询词、CTR、承接页访问与询盘。第二批关键词必须根据这些数据确定，不直接按词库规模继续发文。

### 下一步执行顺序

1. 盘点现有产品分类、服务和联系页，确定上述 4 类承接页的最终 URL 与“保留 / 改造 / 新建”决策。
2. 输出每个承接页的页面蓝图：关键词、标题、模块、证据素材、CTA、FAQ 与内部链接。
3. 在已发布的 12 篇文章中补齐对应核心承接页链接。
4. 每周检查 sitemap、索引、canonical、标题 / 描述、结构化数据和移动端 CTA；确认 Search Console 持续成功读取 `https://yushengco.com/sitemap_index.xml`，仅在读取失败或新增 URL 长期未发现时再刷新 Rank Math 设置 / 缓存。
5. 以 Search Console 首轮数据决定第二批主题簇与关键词队列。
