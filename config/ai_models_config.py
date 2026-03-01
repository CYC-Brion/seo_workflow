"""
AI模型配置
配置不同工作流节点使用的AI模型
"""

# 各节点AI模型配置
NODE_MODELS = {
    "keyword_filter": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "temperature": 0.3,
        "max_tokens": 1000,
        "cost_per_1k_tokens": 0.0015,  # USD
    },
    "title_generator": {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 500,
        "cost_per_1k_tokens": 0.03,  # USD
    },
    "content_generator": {
        "provider": "openai",
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "max_tokens": 4000,
        "cost_per_1k_tokens": 0.06,  # USD
    },
    "image_generator": {
        "provider": "openai",
        "model": "dall-e-3",
        "size": "1024x1024",
        "quality": "standard",
        "cost_per_image": 0.04,  # USD
    }
}

# 备用模型配置（主模型失败时使用）
FALLBACK_MODELS = {
    "keyword_filter": {
        "provider": "anthropic",
        "model": "claude-3-haiku",
        "temperature": 0.3,
        "max_tokens": 1000,
    },
    "title_generator": {
        "provider": "anthropic",
        "model": "claude-3-sonnet",
        "temperature": 0.7,
        "max_tokens": 500,
    },
    "content_generator": {
        "provider": "anthropic",
        "model": "claude-3-opus",
        "temperature": 0.8,
        "max_tokens": 4000,
    }
}

# 模型提供商API配置
PROVIDER_CONFIGS = {
    "openai": {
        "api_key_env_var": "OPENAI_API_KEY",
        "base_url_env_var": "OPENAI_BASE_URL",
        "default_base_url": "https://api.openai.com/v1",
        "timeout": 30,
        "max_retries": 3,
    },
    "anthropic": {
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "base_url_env_var": "ANTHROPIC_BASE_URL",
        "default_base_url": "https://api.anthropic.com",
        "timeout": 30,
        "max_retries": 3,
    },
    "google": {
        "api_key_env_var": "GOOGLE_API_KEY",
        "base_url_env_var": "GOOGLE_BASE_URL",
        "default_base_url": "https://generativelanguage.googleapis.com/v1",
        "timeout": 30,
        "max_retries": 3,
    }
}

# 成本控制
MAX_COST_PER_ARTICLE = 0.50  # 美元
ENABLE_COST_TRACKING = True
COST_LOG_FILE = "data/output/cost_log.json"
