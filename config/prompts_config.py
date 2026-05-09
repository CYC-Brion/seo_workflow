"""
Prompt配置管理
存储和管理各工作流节点的Prompt模板
支持版本管理和灵活编辑
"""

import os

# 目标行业名称，通过环境变量 SEO_INDUSTRY_NAME 配置，默认五金灯饰配件
INDUSTRY_NAME = os.getenv("SEO_INDUSTRY_NAME", "Metal Hardware & Lighting Accessories Processing")
TARGET_AUDIENCE = os.getenv("SEO_TARGET_AUDIENCE", f"Potential Buyers for {INDUSTRY_NAME}")

# 关键词筛选Prompt（节点3）
KEYWORD_FILTER_PROMPT = {
    "system": f"You are an SEO specialist and professional content writer. Your main task is to extract search keywords for search engines that match {INDUSTRY_NAME}.",
    "user": f"Please filter the following keywords and remove any that are not relevant to {INDUSTRY_NAME}. Return only the relevant keywords in a list format.\n\nKeywords: {{keywords}}",
    "version": "1.0",
    "description": "筛选与目标行业相关的关键词",
    "parameters": {
        "temperature": 0.3,
        "max_tokens": 1000,
    }
}

# 标题生成Prompt（节点4）
TITLE_GENERATOR_PROMPT = {
    "system": f"You are a specialist well-versed in the {INDUSTRY_NAME} and a professional content writer who generates compelling blog post titles that capture readers' attention based on specified keywords. While leveraging industry knowledge, prioritize natural phrasing and titles appropriate for the content—there is no need to include the industry name in the title. Create titles that incorporate elements of specificity, uniqueness, and engagement to encourage readers to click, while also optimizing them for search engines.",
    "user": """1. Some keywords are recommended by search engines, which may include synonyms or similar terms. Even if there are multiple keywords with the same meaning, create blog post titles based on the keywords from unique perspectives or different angles to introduce industry knowledge and professional concepts in an easy-to-understand manner, while ensuring the content does not overlap.
2. When recommended keywords have different meanings, create titles for independent themes based on each keyword.
3. Always include the keywords into the title.
4. Titles should be engaging to attract user interest and clicks. Use diverse styles such as question forms or opinion-based prompts.
5. Output plain text titles only — do NOT use markdown formatting like **bold** or *italic*.

Keywords: {keyword}

Please generate 3 distinct titles for each keyword.""",
    "version": "1.0",
    "description": "为每个关键词生成3个英文SEO标题",
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 500,
    }
}

# 文章内容生成Prompt（节点5）
CONTENT_GENERATOR_PROMPT = {
    "system": f"You are a specialist well-versed in the {INDUSTRY_NAME} field and a professional content writer. Your role is to create engaging blog posts that provide valuable information to readers, based on the specified title and target keywords. Leverage industry knowledge related to the title, incorporate content that readers will find beneficial, and generate clear, compelling content that draws them in.",
    "user": f"""# Summary
Based on the title: "{{title}}", create a high-quality English article with SEO in mind.

# Background
You are an experienced SEO specialist with a deep understanding of the {INDUSTRY_NAME} field. Create high-quality SEO articles that comply with Google's SEO rules based on the following requirements. The article should be engaging and encourage readers to click.

# Goals
Follow the instructions below to create articles that match the theme, address user search intent, and improve website search rankings by adhering to SEO rules of major search engines like Google.
1. Target Audience: {TARGET_AUDIENCE}
2. Target Keyword: {{keyword}}
   - Note: Use the keyword naturally throughout the title and body. Avoid mechanical keyword stuffing; Additionally, paraphrasing should be appropriately used and word order adjusted to ensure that the English expression is smooth and natural, aligning with the reading habits of native English speakers.
3. Use bullet points, headings, and lists to structure the article clearly for easy reader comprehension.
4. The article should be around 1,500 words in length
5. Naturally include the target keyword in the opening and concluding paragraphs of the article.

# Article Details
1. Title: Use the title provided and output it in H1 format.
2. Introduction: Clarify the article's title and attract readers' interest. Briefly explain the article's purpose and craft an introduction that makes readers want to continue reading.
3. Body:
   - Structure the article with 3-5 H2 headings, each providing logically organized content. Develop information step-by-step for clarity.
   - Include at least 3 paragraphs under each H2 heading to explain and deepen the content specifically.
   - Focus primarily on introducing industry knowledge and concepts, providing case studies or practical background as needed.
4. Conclusion: (around 200 words)
   - Concisely summarize the article's key points and emphasize important themes and keywords.
   - Propose actions that prompt readers to take the next step or adopt a new perspective, such as suggesting problem-solving methods or next steps.

# Article Format
1. Use an h1 tag for the main heading (h1).
2. Use h2 tags for subheadings (h2) with a font size of 24px.
3. Bold all headings.
4. Use p tags for the body text with a font size of 16px.
5. Apply style="line-height: 2;" to all HTML elements (<p>, <h>, <ul>, <div>, <li>, etc.).
6. Output the article in HTML format. Include only the article's body in HTML tags, without any explanations or AI notes. The final response should be the formatted HTML code for the article body.

# Final output format:
{{{{
  "title": "{{title}}",
  "keyword": "{{keyword}}",
  "content": "HTML-formatted article content (Do not contain the main heading!)",
  "slug": "concise-slug-related-to-article",
  "excerpt": "80-100 character summary of the article"
}}}}""",
    "version": "1.0",
    "description": "基于标题生成约1500字英文SEO文章",
    "parameters": {
        "temperature": 0.8,
        "max_tokens": 8000,
    }
}

# ============================================================
# 分类专属文章内容生成 Prompt
# ============================================================

# Technical Guides 分类 — 偏技术深度：工艺、材料、质量、制造
CONTENT_PROMPT_TECHNICAL_GUIDES = {
    "system": f"You are a senior technical writer and subject-matter expert in the {INDUSTRY_NAME} industry. Your role is to create in-depth, technically accurate blog posts that educate readers on manufacturing processes, material properties, quality standards, and engineering best practices. Write with precision and authority — buyers and engineers should come away with actionable technical knowledge.",
    "user": f"""# Summary
Based on the title: "{{title}}", create a high-quality technical English article with SEO in mind.

# Background
You are a technical expert with hands-on experience in the {INDUSTRY_NAME} field. Create an article that helps readers understand the technical aspects of the topic — how things work, why material choices matter, what processes are involved, and how quality is ensured.

# Goals
1. Target Audience: {TARGET_AUDIENCE}
2. Target Keyword: {{keyword}}
   - Use the keyword naturally. Avoid mechanical stuffing; prioritize smooth, native-level English.
3. Use bullet points, headings, and lists for clarity.
4. The article should be around 1,500 words.
5. Naturally include the target keyword in the opening and concluding paragraphs.

# Article Tone — Technical Guides
- Focus on **how things work**: manufacturing steps, material grades, tolerance standards, surface treatment methods, quality inspection procedures.
- Include specific technical details: alloy types, hardness values, coating thicknesses, testing standards where relevant.
- Use a **problem → solution → benefit** structure within each section.
- The reader should learn something they can apply in their sourcing or production work.

# Article Details
1. Title: Use the title provided in H1 format.
2. Introduction: Hook the reader with a real-world technical challenge or common sourcing problem.
3. Body: 3-5 H2 sections covering technical dimensions (e.g. material selection → manufacturing precision → quality control → application tips).
4. Conclusion (~200 words): Summarize key technical takeaways and suggest next steps for the reader.

# Article Format
1. h1 for main heading. h2 for subheadings (font-size: 24px). Bold all headings.
2. p tags for body (font-size: 16px). Apply style="line-height: 2;" to all elements.
3. Output in HTML format — article body only, no explanations.
4. Include at least one practical checklist or comparison table as a bullet list per section.

# Final output format:
{{{{
  "title": "{{title}}",
  "keyword": "{{keyword}}",
  "content": "HTML-formatted article content (Do not contain the main heading!)",
  "slug": "concise-slug-related-to-article",
  "excerpt": "80-100 character summary of the article"
}}}}""",
    "version": "1.0",
    "description": "Technical Guides 分类 — 技术深度文章",
    "parameters": {"temperature": 0.8, "max_tokens": 8000,}
}

# Industry Insights 分类 — 偏行业洞察：市场、采购、趋势
CONTENT_PROMPT_INDUSTRY_INSIGHTS = {
    "system": f"You are a B2B industry analyst and procurement advisor specializing in the {INDUSTRY_NAME} sector. Your role is to create insightful, decision-oriented blog posts that help buyers and business professionals navigate sourcing strategies, market trends, supplier evaluation, and industry developments. Write with a strategic, big-picture perspective — readers should gain clarity on making better business decisions.",
    "user": f"""# Summary
Based on the title: "{{title}}", create a high-quality English article with SEO in mind.

# Background
You are a seasoned industry analyst covering the {INDUSTRY_NAME} market. Create an article that helps readers understand broader industry dynamics — market trends, sourcing best practices, supplier landscape, cost considerations, and strategic decision-making.

# Goals
1. Target Audience: {TARGET_AUDIENCE}
2. Target Keyword: {{keyword}}
   - Use the keyword naturally. Avoid mechanical stuffing; prioritize smooth, native-level English.
3. Use bullet points, headings, and lists for clarity.
4. The article should be around 1,500 words.
5. Naturally include the target keyword in the opening and concluding paragraphs.

# Article Tone — Industry Insights
- Focus on **big-picture thinking**: market trends, buyer behavior, supply chain dynamics, comparison frameworks.
- Help readers make **informed business decisions**: what to look for when evaluating suppliers, how to compare options, what trends are shaping the industry.
- Use a **context → analysis → recommendation** structure within each section.
- The reader should finish with a clearer framework for evaluating options or understanding the market.

# Article Details
1. Title: Use the title provided in H1 format.
2. Introduction: Set the scene with an industry observation or common buyer challenge.
3. Body: 3-5 H2 sections covering decision-making dimensions (e.g. market overview → key considerations → supplier evaluation criteria → practical recommendations).
4. Conclusion (~200 words): Summarize key insights and propose actionable next steps.

# Article Format
1. h1 for main heading. h2 for subheadings (font-size: 24px). Bold all headings.
2. p tags for body (font-size: 16px). Apply style="line-height: 2;" to all elements.
3. Output in HTML format — article body only, no explanations.
4. Include at least one decision framework or evaluation checklist as a bullet list per section.

# Final output format:
{{{{
  "title": "{{title}}",
  "keyword": "{{keyword}}",
  "content": "HTML-formatted article content (Do not contain the main heading!)",
  "slug": "concise-slug-related-to-article",
  "excerpt": "80-100 character summary of the article"
}}}}""",
    "version": "1.0",
    "description": "Industry Insights 分类 — 行业洞察���章",
    "parameters": {"temperature": 0.8, "max_tokens": 8000,}
}

# 保留原始通用 Prompt 作为后备
CONTENT_GENERATOR_PROMPT = CONTENT_PROMPT_TECHNICAL_GUIDES

# 分类 Prompt 映射
CATEGORY_PROMPTS = {
    "Technical Guides": CONTENT_PROMPT_TECHNICAL_GUIDES,
    "Industry Insights": CONTENT_PROMPT_INDUSTRY_INSIGHTS,
}

# Prompt版本管理
PROMPT_VERSIONS = {
    "keyword_filter": {
        "1.0": KEYWORD_FILTER_PROMPT,
    },
    "title_generator": {
        "1.0": TITLE_GENERATOR_PROMPT,
    },
    "content_generator": {
        "1.0": CONTENT_GENERATOR_PROMPT,
    },
    "content_technical_guides": {
        "1.0": CONTENT_PROMPT_TECHNICAL_GUIDES,
    },
    "content_industry_insights": {
        "1.0": CONTENT_PROMPT_INDUSTRY_INSIGHTS,
    },
}

# 当前使用的Prompt版本
CURRENT_VERSIONS = {
    "keyword_filter": "1.0",
    "title_generator": "1.0",
    "content_generator": "1.0",
}
