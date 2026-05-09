"""
AI模型配置
配置不同工作流节点使用的AI模型
"""

# 各节点AI模型配置
# 如果有 Azure OpenAI，优先使用 Azure 部署；否则回退到标准 OpenAI
# deployment_name 从环境变量 AZURE_OPENAI_DEPLOYMENT 读取
import os as _os
_azure_deployment = _os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
_use_azure = bool(_os.getenv("AZURE_OPENAI_ENDPOINT", "")) and bool(_os.getenv("AZURE_OPENAI_API_KEY", ""))

NODE_MODELS = {
    "default": {
        "provider": "azure" if _use_azure else "openai",
        "model": _azure_deployment or "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4000,
        "timeout": 60,
        "cost_per_1k_tokens": 0.0025,
    },
    "keyword_filter": {
        "provider": "azure" if _use_azure else "openai",
        "model": _azure_deployment or "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1000,
        "timeout": 60,
        "cost_per_1k_tokens": 0.00015,  # USD
    },
    "title_generator": {
        "provider": "azure" if _use_azure else "openai",
        "model": _azure_deployment or "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 500,
        "timeout": 90,
        "cost_per_1k_tokens": 0.0025,  # USD
    },
    "content_generator": {
        "provider": "azure" if _use_azure else "openai",
        "model": _azure_deployment or "gpt-4o",
        "temperature": 0.8,
        "max_tokens": 8000,
        "timeout": 600,
        "cost_per_1k_tokens": 0.01,  # USD
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
# 留空表示不使用备用模型，AI 调用失败时将使用内置默认内容
FALLBACK_MODELS = {}

# 模型提供商API配置
PROVIDER_CONFIGS = {
    "azure": {
        "api_key_env_var": "AZURE_OPENAI_API_KEY",
        "base_url_env_var": "AZURE_OPENAI_ENDPOINT",
        "default_base_url": "",
        "timeout": 120,
        "max_retries": 3,
        "api_version_env_var": "AZURE_OPENAI_API_VERSION",
        "default_api_version": "2024-12-01-preview",
    },
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
