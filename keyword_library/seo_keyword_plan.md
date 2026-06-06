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
- `seo_phase3_ordinary.xlsx`：ordinary 辅助批次文件
- `seo_phase3_pillar.xlsx`：pillar 辅助批次文件

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
