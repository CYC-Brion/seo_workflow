# SEO / GEO 关键词实施建议

## 站点定位
- 主定位：灯具五金配件、灯具结构件、定制金属部件、ODM/OEM 工厂
- 核心产品：floor lamp sets、wall lamp sets、table lamp sets、custom made parts、tubes、panels、universal joints、machined parts
- 内容主线：产品词、技术词、采购决策词三条线并行

## 推荐投放顺序
1. 先做高意图产品词和工厂词
2. 再做技术解释词，覆盖材料、结构、工艺、QC
3. 最后做供应商对比、OEM/ODM、采购指南类关键词

## 关键词分类策略
- Technical Guides：适合做工艺、结构、材料、质量控制、安装维护
- Industry Insights：适合做采购决策、供应商比较、OEM/ODM、趋势、成本分析

## 推荐内容节奏
- 产品页：1 个关键词聚焦 1 个产品或 1 个规格
- 技术文：1 个关键词对应 1 个明确技术问题
- 对比文：围绕“如何选择”“如何比较”“如何避坑”来写

## 直接可用的工作流文件
- `seo_workflow_pack.xlsx`：可直接导入工作流
- `seo_phase2_mixed.xlsx`：混合执行入口，`plan` 表会按 ordinary / pillar / direction 交错产出
- `seo_phase2_ordinary.xlsx`：普通词批次
- `seo_phase2_pillar.xlsx`：pillar 批次
- `seo_keyword_plan.md`：关键词实施说明

## 混合执行规则
- 真正的 mixed 模式请优先跑 `seo_phase2_mixed.xlsx`
- `keywords` 表只负责种子词，`plan` 表决定发文顺序、lane 和 pillar direction
- 同一个 pillar 关键词如果在 `plan` 里出现 3 次，就会按 3 个方向生成 3 篇文章
- 现在的工作流仍是 1 个 plan row -> 1 个标题 -> 1 篇文章，混合效果来自 `plan` 的重复编排，而不是关键词自动复制

## 备注
- 目前只使用项目里已支持的两个分类：Technical Guides、Industry Insights
- 如果后续要扩展到 News 或其他分类，建议先补 WordPress 分类映射和 prompt 映射
