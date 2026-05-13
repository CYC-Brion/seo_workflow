# SEO Content Automation Workflow

## Overview
This project turns an Excel keyword list into scheduled WordPress SEO posts.

Main pipeline:

1. Read keywords from Excel
2. Expand long-tail keywords
3. Filter industry-relevant keywords with AI
4. Generate titles with AI
5. Generate article content with AI
6. Publish to WordPress

The primary publishing strategy is now WordPress native `future` scheduling.
GitHub Actions is no longer used as the default hourly auto-publisher.

## Current Default Behavior
The default scheduling configuration is:

```python
SCHEDULE_POSTS = True
DEFAULT_SCHEDULE_HOURS = 1
DEFAULT_SCHEDULE_INTERVAL_HOURS = 1
TIMEZONE = "UTC"
```

That means:

- the first article is scheduled 1 hour after the workflow starts
- each following article is scheduled 1 hour after the previous one

## Excel Format
Prepare an `.xlsx` file with at least a `keywords` column.

Example:

| keywords | category |
|----------|----------|
| lamp holder | Technical Guides |
| hardware accessories | Industry Insights |
| surface treatment | Technical Guides |

Notes:

- `keywords` is required
- `category` is optional
- if `category` is empty, `Technical Guides` is used

## Run The Real Workflow
With the current defaults, run:

```bash
python -m src.cli.main workflow run 测试用例.xlsx
```

This will:

- read the Excel file
- expand and filter keywords
- generate titles and article content
- push posts to WordPress
- create them as `Scheduled` posts

## Common Commands

### Use default scheduling

```bash
python -m src.cli.main workflow run 测试用例.xlsx
```

### Start publishing 24 hours later

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24
```

### Start 24 hours later and stagger by 12 hours

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24 --schedule-interval-hours 12
```

### Schedule all posts at the same time

```bash
python -m src.cli.main workflow run 测试用例.xlsx --schedule-hours 24 --schedule-interval-hours 0
```

### Dry run

```bash
python -m src.cli.main workflow run 测试用例.xlsx --dry-run
```

## What To Check After A Run
Look at:

1. the terminal summary
2. the WordPress admin post list

Expected summary shape:

```text
生成: N 标题, N 篇文章
发布: 0 已发布, N 已排期, 0 草稿, 0 跳过
```

Expected WordPress state:

- new posts appear under `Scheduled`
- publish times are staggered according to your settings
- posts become `Published` automatically at the scheduled time

## Environment Variables
Sensitive WordPress credentials should live in `.env`, not in source files.

Required WordPress variables:

```env
WORDPRESS_URL=https://yushengco.com/
WORDPRESS_USERNAME=
WORDPRESS_PASSWORD=
WORDPRESS_APPLICATION_PASSWORD=
```

Scheduling variables:

```env
SCHEDULE_POSTS=true
DEFAULT_SCHEDULE_HOURS=1
DEFAULT_SCHEDULE_INTERVAL_HOURS=1
WORDPRESS_TIMEZONE=UTC
WORDPRESS_VERIFY_SSL=true
WORDPRESS_TIMEOUT=30
WORDPRESS_MAX_RETRIES=3
```

## Important Files

| File | Purpose |
|------|---------|
| `config/wordpress_config.py` | WordPress connection, scheduling defaults, category mapping |
| `config/prompts_config.py` | Prompt templates |
| `config/ai_models_config.py` | AI model configuration |
| `config/settings.py` | Project-level settings |
| `Guiding.md` | Detailed operational guide |

## Prompt Customization
Prompts are managed in `config/prompts_config.py`.

Useful sections:

- `KEYWORD_FILTER_PROMPT`
- `TITLE_GENERATOR_PROMPT`
- `CONTENT_PROMPT_TECHNICAL_GUIDES`
- `CONTENT_PROMPT_INDUSTRY_INSIGHTS`
- `CATEGORY_PROMPTS`

## Legacy GitHub Workflow
`.github/workflows/auto-publish.yml` is retained only as a manual fallback for old draft-based publishing.

- it no longer runs on a cron schedule
- it should not be treated as the primary publishing mechanism

## Notes

- WordPress scheduling is now the source of truth for automatic publishing
- if the WordPress site schedules correctly, GitHub cron is unnecessary
- if you lose network during AI generation, some content batches may fail and need a targeted rerun
