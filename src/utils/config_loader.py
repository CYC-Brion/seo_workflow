"""
配置加载和管理工具
统一加载项目配置文件，提供配置验证和访问接口
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .logger import get_logger

logger = get_logger("config_loader")


@dataclass
class AIModelConfig:
    """AI模型配置"""
    provider: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int = 30
    max_retries: int = 3
    cost_per_1k_tokens: Optional[float] = None
    cost_per_image: Optional[float] = None
    size: Optional[str] = None
    quality: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIModelConfig":
        """从字典创建配置对象"""
        return cls(
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1000),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            cost_per_1k_tokens=data.get("cost_per_1k_tokens"),
            cost_per_image=data.get("cost_per_image"),
            size=data.get("size"),
            quality=data.get("quality"),
        )


@dataclass
class ProviderConfig:
    """模型提供商配置"""
    api_key_env_var: str
    base_url_env_var: str
    default_base_url: str
    timeout: int
    max_retries: int
    api_version_env_var: Optional[str] = None
    default_api_version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        """从字典创建配置对象"""
        return cls(
            api_key_env_var=data.get("api_key_env_var", ""),
            base_url_env_var=data.get("base_url_env_var", ""),
            default_base_url=data.get("default_base_url", ""),
            timeout=data.get("timeout", 30),
            max_retries=data.get("max_retries", 3),
            api_version_env_var=data.get("api_version_env_var"),
            default_api_version=data.get("default_api_version"),
        )


@dataclass
class WordPressConfig:
    """WordPress配置"""
    url: str
    username: str
    password: str
    application_password: str
    api_url: str
    xmlrpc_url: str
    default_post_status: str
    default_post_type: str
    default_category_id: int
    default_tag_ids: List[int]
    media_upload_path: str
    allowed_image_extensions: List[str]
    max_image_size_mb: int
    schedule_posts: bool
    default_schedule_hours: int
    timezone: str
    verify_ssl: bool
    timeout: int
    max_retries: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordPressConfig":
        """从字典创建配置对象"""
        return cls(
            url=data.get("WORDPRESS_URL", ""),
            username=data.get("WORDPRESS_USERNAME", ""),
            password=data.get("WORDPRESS_PASSWORD", ""),
            application_password=data.get("WORDPRESS_APPLICATION_PASSWORD", ""),
            api_url=data.get("WORDPRESS_API_URL", ""),
            xmlrpc_url=data.get("WORDPRESS_XMLRPC_URL", ""),
            default_post_status=data.get("DEFAULT_POST_STATUS", "draft"),
            default_post_type=data.get("DEFAULT_POST_TYPE", "post"),
            default_category_id=data.get("DEFAULT_CATEGORY_ID", 1),
            default_tag_ids=data.get("DEFAULT_TAG_IDS", []),
            media_upload_path=data.get("MEDIA_UPLOAD_PATH", "ai-generated"),
            allowed_image_extensions=data.get("ALLOWED_IMAGE_EXTENSIONS", [".jpg", ".jpeg", ".png", ".gif", ".webp"]),
            max_image_size_mb=data.get("MAX_IMAGE_SIZE_MB", 5),
            schedule_posts=data.get("SCHEDULE_POSTS", False),
            default_schedule_hours=data.get("DEFAULT_SCHEDULE_HOURS", 24),
            timezone=data.get("TIMEZONE", "UTC"),
            verify_ssl=data.get("VERIFY_SSL", True),
            timeout=data.get("TIMEOUT", 30),
            max_retries=data.get("MAX_RETRIES", 3),
        )


@dataclass
class ProjectConfig:
    """项目全局配置"""
    base_dir: Path
    data_dir: Path
    input_dir: Path
    output_dir: Path
    cache_dir: Path
    logs_dir: Path

    openai_api_key: str
    anthropic_api_key: str
    openai_base_url: str
    anthropic_base_url: str

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_openai_api_version: str

    default_ai_model: str
    max_keywords_per_batch: int
    max_file_size_mb: int
    article_word_count: int
    titles_per_keyword: int

    request_timeout: int
    max_retries: int
    retry_delay: int

    log_level: str
    log_format: str
    log_file: Path

    debug: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """从字典创建配置对象"""
        return cls(
            base_dir=Path(data.get("BASE_DIR", "")),
            data_dir=Path(data.get("DATA_DIR", "")),
            input_dir=Path(data.get("INPUT_DIR", "")),
            output_dir=Path(data.get("OUTPUT_DIR", "")),
            cache_dir=Path(data.get("CACHE_DIR", "")),
            logs_dir=Path(data.get("LOGS_DIR", "")),

            openai_api_key=data.get("OPENAI_API_KEY", ""),
            anthropic_api_key=data.get("ANTHROPIC_API_KEY", ""),
            openai_base_url=data.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            anthropic_base_url=data.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),

            azure_openai_endpoint=data.get("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=data.get("AZURE_OPENAI_API_KEY", ""),
            azure_openai_deployment=data.get("AZURE_OPENAI_DEPLOYMENT", ""),
            azure_openai_api_version=data.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),

            default_ai_model=data.get("DEFAULT_AI_MODEL", "gpt-4"),
            max_keywords_per_batch=data.get("MAX_KEYWORDS_PER_BATCH", 100),
            max_file_size_mb=data.get("MAX_FILE_SIZE_MB", 10),
            article_word_count=data.get("ARTICLE_WORD_COUNT", 1500),
            titles_per_keyword=data.get("TITLES_PER_KEYWORD", 3),

            request_timeout=data.get("REQUEST_TIMEOUT", 30),
            max_retries=data.get("MAX_RETRIES", 3),
            retry_delay=data.get("RETRY_DELAY", 5),

            log_level=data.get("LOG_LEVEL", "INFO"),
            log_format=data.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file=Path(data.get("LOG_FILE", "logs/workflow.log")),

            debug=data.get("DEBUG", False),
        )


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config_loaded = False
        self._project_config: Optional[ProjectConfig] = None
        self._ai_model_configs: Dict[str, Dict[str, AIModelConfig]] = {}
        self._fallback_model_configs: Dict[str, AIModelConfig] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}
        self._wordpress_config: Optional[WordPressConfig] = None
        self._prompts_config: Dict[str, Any] = {}

        self.logger = get_logger("config_manager")

    def load_all_configs(self) -> bool:
        """加载所有配置文件"""
        try:
            self.logger.info("开始加载配置文件")

            # 加载项目设置
            self._load_project_config()

            # 加载AI模型配置
            self._load_ai_model_configs()

            # 加载WordPress配置
            self._load_wordpress_config()

            # 加载Prompt配置
            self._load_prompts_config()

            # 验证配置
            self._validate_configs()

            self._config_loaded = True
            self.logger.info("所有配置文件加载成功")
            return True

        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}", exc_info=True)
            return False

    def _load_project_config(self) -> None:
        """加载项目全局配置"""
        try:
            from config import settings
            config_dict = {k: v for k, v in vars(settings).items() if not k.startswith('_')}
            self._project_config = ProjectConfig.from_dict(config_dict)
            self.logger.info("项目全局配置加载成功")
        except ImportError as e:
            self.logger.error(f"无法导入settings模块: {str(e)}")
            raise

    def _load_ai_model_configs(self) -> None:
        """加载AI模型配置"""
        try:
            from config import ai_models_config

            # 加载节点模型配置
            node_models = getattr(ai_models_config, "NODE_MODELS", {})
            for node_name, model_config in node_models.items():
                self._ai_model_configs[node_name] = AIModelConfig.from_dict(model_config)

            # 加载备用模型配置
            fallback_models = getattr(ai_models_config, "FALLBACK_MODELS", {})
            for node_name, model_config in fallback_models.items():
                self._fallback_model_configs[node_name] = AIModelConfig.from_dict(model_config)

            # 加载提供商配置
            provider_configs = getattr(ai_models_config, "PROVIDER_CONFIGS", {})
            for provider_name, provider_config in provider_configs.items():
                self._provider_configs[provider_name] = ProviderConfig.from_dict(provider_config)

            self.logger.info("AI模型配置加载成功")

        except ImportError as e:
            self.logger.error(f"无法导入ai_models_config模块: {str(e)}")
            raise

    def _load_wordpress_config(self) -> None:
        """加载WordPress配置"""
        try:
            from config import wordpress_config
            config_dict = {k: v for k, v in vars(wordpress_config).items() if not k.startswith('_')}
            self._wordpress_config = WordPressConfig.from_dict(config_dict)
            self.logger.info("WordPress配置加载成功")
        except ImportError as e:
            self.logger.warning(f"无法导入wordpress_config模块: {str(e)}，将使用默认配置")
            # 使用默认配置
            self._wordpress_config = WordPressConfig.from_dict({})

    def _load_prompts_config(self) -> None:
        """加载Prompt配置"""
        try:
            from config import prompts_config
            # 存储整个prompts_config模块的变量
            config_dict = {k: v for k, v in vars(prompts_config).items() if not k.startswith('_')}
            self._prompts_config = config_dict
            self.logger.info("Prompt配置加载成功")
        except ImportError as e:
            self.logger.warning(f"无法导入prompts_config模块: {str(e)}，将使用空配置")
            self._prompts_config = {}

    def _validate_configs(self) -> None:
        """验证配置的完整性"""
        errors = []

        # 验证项目配置
        if not self._project_config:
            errors.append("项目全局配置未加载")

        # 验证AI配置
        if not self._ai_model_configs:
            errors.append("AI模型配置未加载")

        # 验证必要的API密钥
        if self._project_config:
            has_openai = bool(self._project_config.openai_api_key)
            has_azure = bool(self._project_config.azure_openai_api_key)
            has_anthropic = bool(self._project_config.anthropic_api_key)
            if not (has_openai or has_azure or has_anthropic):
                errors.append("至少需要配置 OpenAI、Azure OpenAI 或 Anthropic 中的一种 API 密钥")

        if errors:
            error_msg = "配置验证失败: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info("配置验证通过")

    @property
    def project_config(self) -> ProjectConfig:
        """获取项目配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._project_config

    @property
    def ai_model_configs(self) -> Dict[str, Dict[str, AIModelConfig]]:
        """获取AI模型配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._ai_model_configs

    @property
    def fallback_model_configs(self) -> Dict[str, AIModelConfig]:
        """获取备用模型配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._fallback_model_configs

    @property
    def provider_configs(self) -> Dict[str, ProviderConfig]:
        """获取提供商配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._provider_configs

    @property
    def wordpress_config(self) -> WordPressConfig:
        """获取WordPress配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._wordpress_config

    @property
    def prompts_config(self) -> Dict[str, Any]:
        """获取Prompt配置"""
        if not self._config_loaded:
            self.load_all_configs()
        return self._prompts_config

    def get_node_model_config(self, node_name: str) -> AIModelConfig:
        """获取指定节点的AI模型配置"""
        if not self._config_loaded:
            self.load_all_configs()

        if node_name not in self._ai_model_configs:
            raise ValueError(f"未找到节点 '{node_name}' 的AI模型配置")

        return self._ai_model_configs[node_name]

    def get_fallback_model_config(self, node_name: str) -> Optional[AIModelConfig]:
        """获取指定节点的备用模型配置"""
        if not self._config_loaded:
            self.load_all_configs()

        return self._fallback_model_configs.get(node_name)

    def get_provider_config(self, provider_name: str) -> ProviderConfig:
        """获取指定提供商的配置"""
        if not self._config_loaded:
            self.load_all_configs()

        if provider_name not in self._provider_configs:
            raise ValueError(f"未找到提供商 '{provider_name}' 的配置")

        return self._provider_configs[provider_name]

    def get_prompt_template(self, prompt_name: str, version: str = "1.0") -> Dict[str, Any]:
        """获取指定Prompt模板"""
        if not self._config_loaded:
            self.load_all_configs()

        prompt_versions = self._prompts_config.get("PROMPT_VERSIONS", {})
        if prompt_name not in prompt_versions:
            raise ValueError(f"未找到Prompt '{prompt_name}'")

        versions = prompt_versions[prompt_name]
        if version not in versions:
            raise ValueError(f"未找到Prompt '{prompt_name}' 的版本 '{version}'")

        return versions[version]

    def get_current_prompt_version(self, prompt_name: str) -> str:
        """获取当前使用的Prompt版本"""
        if not self._config_loaded:
            self.load_all_configs()

        current_versions = self._prompts_config.get("CURRENT_VERSIONS", {})
        return current_versions.get(prompt_name, "1.0")

    def check_api_keys(self) -> Dict[str, bool]:
        """检查API密钥配置状态"""
        result = {}

        if self._project_config:
            result["openai"] = bool(self._project_config.openai_api_key)
            result["azure"] = bool(self._project_config.azure_openai_api_key)
            result["anthropic"] = bool(self._project_config.anthropic_api_key)

        if self._wordpress_config:
            result["wordpress"] = bool(
                self._wordpress_config.url and
                self._wordpress_config.username and
                (self._wordpress_config.password or self._wordpress_config.application_password)
            )

        return result


# 全局配置管理器实例
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """获取全局配置管理器"""
    return config_manager


__all__ = [
    "ConfigManager",
    "AIModelConfig",
    "ProviderConfig",
    "WordPressConfig",
    "ProjectConfig",
    "config_manager",
    "get_config",
]