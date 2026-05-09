"""
配置加载器单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.utils.config_loader import (
    ConfigManager,
    AIModelConfig,
    ProviderConfig,
    WordPressConfig,
    ProjectConfig,
    config_manager,
    get_config,
)


class TestConfigManager:
    """配置管理器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.config_manager = ConfigManager()

    def test_initialization(self):
        """测试初始化"""
        assert self.config_manager._config_loaded == False
        assert self.config_manager._project_config is None
        assert self.config_manager._ai_model_configs == {}
        assert self.config_manager._fallback_model_configs == {}
        assert self.config_manager._provider_configs == {}
        assert self.config_manager._wordpress_config is None
        assert self.config_manager._prompts_config == {}

    @patch('src.utils.config_loader.config')
    def test_load_all_configs_success(self, mock_config):
        """测试成功加载所有配置"""
        # 模拟settings模块
        mock_settings = Mock()
        mock_settings.BASE_DIR = "/test/path"
        mock_settings.DATA_DIR = "/test/path/data"
        mock_settings.OPENAI_API_KEY = "test-openai-key"
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.DEFAULT_AI_MODEL = "gpt-4"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.DEBUG = False

        # 模拟ai_models_config模块
        mock_ai_models_config = Mock()
        mock_ai_models_config.NODE_MODELS = {
            "keyword_filter": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 1000,
            }
        }
        mock_ai_models_config.FALLBACK_MODELS = {
            "keyword_filter": {
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "temperature": 0.5,
                "max_tokens": 1000,
            }
        }
        mock_ai_models_config.PROVIDER_CONFIGS = {
            "openai": {
                "api_key_env_var": "OPENAI_API_KEY",
                "base_url_env_var": "OPENAI_BASE_URL",
                "default_base_url": "https://api.openai.com/v1",
                "timeout": 30,
                "max_retries": 3,
            }
        }

        # 模拟wordpress_config模块
        mock_wordpress_config = Mock()
        mock_wordpress_config.WORDPRESS_URL = "https://example.com"
        mock_wordpress_config.WORDPRESS_USERNAME = "admin"
        mock_wordpress_config.WORDPRESS_PASSWORD = "password"
        mock_wordpress_config.WORDPRESS_APPLICATION_PASSWORD = "app_password"

        # 模拟prompts_config模块
        mock_prompts_config = Mock()
        mock_prompts_config.PROMPT_VERSIONS = {
            "keyword_filter": {
                "1.0": {
                    "system": "系统提示",
                    "user": "用户提示 {keywords}",
                    "parameters": {"temperature": 0.3}
                }
            }
        }
        mock_prompts_config.CURRENT_VERSIONS = {
            "keyword_filter": "1.0"
        }

        # 模拟config模块的导入
        mock_config.settings = mock_settings
        mock_config.ai_models_config = mock_ai_models_config
        mock_config.wordpress_config = mock_wordpress_config
        mock_config.prompts_config = mock_prompts_config

        # 执行加载
        result = self.config_manager.load_all_configs()

        assert result == True
        assert self.config_manager._config_loaded == True
        assert self.config_manager._project_config is not None
        assert self.config_manager._ai_model_configs != {}
        assert self.config_manager._wordpress_config is not None
        assert self.config_manager._prompts_config != {}

    @patch('src.utils.config_loader.config')
    def test_load_all_configs_failure(self, mock_config):
        """测试加载配置失败"""
        # 模拟导入错误
        mock_config.settings = Mock()
        mock_config.settings.side_effect = ImportError("模块不存在")

        result = self.config_manager.load_all_configs()

        assert result == False
        assert self.config_manager._config_loaded == False

    @patch('src.utils.config_loader.config')
    def test_load_all_configs_missing_api_keys(self, mock_config):
        """测试加载缺少API密钥的配置"""
        # 模拟settings模块（没有API密钥）
        mock_settings = Mock()
        mock_settings.BASE_DIR = "/test/path"
        mock_settings.DATA_DIR = "/test/path/data"
        mock_settings.OPENAI_API_KEY = ""  # 空密钥
        mock_settings.ANTHROPIC_API_KEY = ""  # 空密钥
        mock_settings.DEFAULT_AI_MODEL = "gpt-4"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.DEBUG = False

        # 模拟其他模块
        mock_ai_models_config = Mock()
        mock_ai_models_config.NODE_MODELS = {}
        mock_ai_models_config.FALLBACK_MODELS = {}
        mock_ai_models_config.PROVIDER_CONFIGS = {}

        mock_wordpress_config = Mock()
        mock_wordpress_config.WORDPRESS_URL = ""
        mock_wordpress_config.WORDPRESS_USERNAME = ""
        mock_wordpress_config.WORDPRESS_PASSWORD = ""

        mock_prompts_config = Mock()
        mock_prompts_config.PROMPT_VERSIONS = {}
        mock_prompts_config.CURRENT_VERSIONS = {}

        mock_config.settings = mock_settings
        mock_config.ai_models_config = mock_ai_models_config
        mock_config.wordpress_config = mock_wordpress_config
        mock_config.prompts_config = mock_prompts_config

        # 执行加载，应该抛出验证错误
        with pytest.raises(ValueError) as exc_info:
            self.config_manager.load_all_configs()

        assert "至少需要配置 OpenAI、Azure OpenAI 或 Anthropic 中的一种 API 密钥" in str(exc_info.value)

    def test_project_config_property(self):
        """测试项目配置属性"""
        # 初始状态下配置未加载
        assert self.config_manager._config_loaded == False

        # 模拟load_all_configs方法
        with patch.object(self.config_manager, 'load_all_configs') as mock_load:
            mock_load.return_value = True

            # 创建模拟项目配置
            mock_project_config = Mock(spec=ProjectConfig)
            self.config_manager._project_config = mock_project_config
            self.config_manager._config_loaded = True

            # 访问属性
            config = self.config_manager.project_config

            assert config == mock_project_config
            mock_load.assert_not_called()  # 配置已加载，不应调用load_all_configs

    def test_project_config_property_auto_load(self):
        """测试项目配置属性自动加载"""
        # 初始状态下配置未加载
        assert self.config_manager._config_loaded == False

        with patch.object(self.config_manager, 'load_all_configs') as mock_load:
            mock_load.return_value = True

            # 创建模拟项目配置
            mock_project_config = Mock(spec=ProjectConfig)
            self.config_manager._project_config = mock_project_config

            # 访问属性，应该触发自动加载
            config = self.config_manager.project_config

            mock_load.assert_called_once()
            assert config == mock_project_config

    def test_ai_model_configs_property(self):
        """测试AI模型配置属性"""
        # 模拟配置
        mock_ai_configs = {
            "keyword_filter": AIModelConfig(
                provider="openai",
                model="gpt-4",
                temperature=0.3,
                max_tokens=1000
            )
        }
        self.config_manager._ai_model_configs = mock_ai_configs
        self.config_manager._config_loaded = True

        configs = self.config_manager.ai_model_configs

        assert configs == mock_ai_configs

    def test_fallback_model_configs_property(self):
        """测试备用模型配置属性"""
        # 模拟配置
        mock_fallback_configs = {
            "keyword_filter": AIModelConfig(
                provider="anthropic",
                model="claude-3-haiku",
                temperature=0.5,
                max_tokens=1000
            )
        }
        self.config_manager._fallback_model_configs = mock_fallback_configs
        self.config_manager._config_loaded = True

        configs = self.config_manager.fallback_model_configs

        assert configs == mock_fallback_configs

    def test_provider_configs_property(self):
        """测试提供商配置属性"""
        # 模拟配置
        mock_provider_configs = {
            "openai": ProviderConfig(
                api_key_env_var="OPENAI_API_KEY",
                base_url_env_var="OPENAI_BASE_URL",
                default_base_url="https://api.openai.com/v1",
                timeout=30,
                max_retries=3
            )
        }
        self.config_manager._provider_configs = mock_provider_configs
        self.config_manager._config_loaded = True

        configs = self.config_manager.provider_configs

        assert configs == mock_provider_configs

    def test_wordpress_config_property(self):
        """测试WordPress配置属性"""
        # 模拟配置
        mock_wp_config = WordPressConfig.from_dict({
            "WORDPRESS_URL": "https://example.com",
            "WORDPRESS_USERNAME": "admin",
            "WORDPRESS_PASSWORD": "password",
        })
        self.config_manager._wordpress_config = mock_wp_config
        self.config_manager._config_loaded = True

        config = self.config_manager.wordpress_config

        assert config == mock_wp_config

    def test_prompts_config_property(self):
        """测试Prompt配置属性"""
        # 模拟配置
        mock_prompts_config = {
            "PROMPT_VERSIONS": {
                "keyword_filter": {
                    "1.0": {"system": "系统提示"}
                }
            }
        }
        self.config_manager._prompts_config = mock_prompts_config
        self.config_manager._config_loaded = True

        config = self.config_manager.prompts_config

        assert config == mock_prompts_config

    def test_get_node_model_config(self):
        """测试获取节点模型配置"""
        # 模拟配置
        mock_ai_config = AIModelConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.3,
            max_tokens=1000
        )
        self.config_manager._ai_model_configs = {
            "keyword_filter": mock_ai_config
        }
        self.config_manager._config_loaded = True

        config = self.config_manager.get_node_model_config("keyword_filter")

        assert config == mock_ai_config

    def test_get_node_model_config_not_found(self):
        """测试获取不存在的节点模型配置"""
        self.config_manager._ai_model_configs = {}
        self.config_manager._config_loaded = True

        with pytest.raises(ValueError) as exc_info:
            self.config_manager.get_node_model_config("nonexistent")

        assert "未找到节点 'nonexistent' 的AI模型配置" in str(exc_info.value)

    def test_get_fallback_model_config(self):
        """测试获取备用模型配置"""
        # 模拟配置
        mock_fallback_config = AIModelConfig(
            provider="anthropic",
            model="claude-3-haiku",
            temperature=0.5,
            max_tokens=1000
        )
        self.config_manager._fallback_model_configs = {
            "keyword_filter": mock_fallback_config
        }
        self.config_manager._config_loaded = True

        config = self.config_manager.get_fallback_model_config("keyword_filter")

        assert config == mock_fallback_config

    def test_get_fallback_model_config_not_found(self):
        """测试获取不存在的备用模型配置"""
        self.config_manager._fallback_model_configs = {}
        self.config_manager._config_loaded = True

        config = self.config_manager.get_fallback_model_config("nonexistent")

        assert config is None

    def test_get_provider_config(self):
        """测试获取提供商配置"""
        # 模拟配置
        mock_provider_config = ProviderConfig(
            api_key_env_var="OPENAI_API_KEY",
            base_url_env_var="OPENAI_BASE_URL",
            default_base_url="https://api.openai.com/v1",
            timeout=30,
            max_retries=3
        )
        self.config_manager._provider_configs = {
            "openai": mock_provider_config
        }
        self.config_manager._config_loaded = True

        config = self.config_manager.get_provider_config("openai")

        assert config == mock_provider_config

    def test_get_provider_config_not_found(self):
        """测试获取不存在的提供商配置"""
        self.config_manager._provider_configs = {}
        self.config_manager._config_loaded = True

        with pytest.raises(ValueError) as exc_info:
            self.config_manager.get_provider_config("nonexistent")

        assert "未找到提供商 'nonexistent' 的配置" in str(exc_info.value)

    def test_get_prompt_template(self):
        """测试获取Prompt模板"""
        # 模拟配置
        mock_prompt_template = {
            "system": "系统提示",
            "user": "用户提示 {keywords}",
            "parameters": {"temperature": 0.3}
        }
        self.config_manager._prompts_config = {
            "PROMPT_VERSIONS": {
                "keyword_filter": {
                    "1.0": mock_prompt_template
                }
            },
            "CURRENT_VERSIONS": {
                "keyword_filter": "1.0"
            }
        }
        self.config_manager._config_loaded = True

        template = self.config_manager.get_prompt_template("keyword_filter", "1.0")

        assert template == mock_prompt_template

    def test_get_prompt_template_not_found(self):
        """测试获取不存在的Prompt模板"""
        self.config_manager._prompts_config = {
            "PROMPT_VERSIONS": {}
        }
        self.config_manager._config_loaded = True

        with pytest.raises(ValueError) as exc_info:
            self.config_manager.get_prompt_template("nonexistent", "1.0")

        assert "未找到Prompt 'nonexistent'" in str(exc_info.value)

    def test_get_prompt_template_version_not_found(self):
        """测试获取不存在的Prompt版本"""
        self.config_manager._prompts_config = {
            "PROMPT_VERSIONS": {
                "keyword_filter": {
                    "1.0": {"system": "系统提示"}
                }
            }
        }
        self.config_manager._config_loaded = True

        with pytest.raises(ValueError) as exc_info:
            self.config_manager.get_prompt_template("keyword_filter", "2.0")

        assert "未找到Prompt 'keyword_filter' 的版本 '2.0'" in str(exc_info.value)

    def test_get_current_prompt_version(self):
        """测试获取当前Prompt版本"""
        self.config_manager._prompts_config = {
            "CURRENT_VERSIONS": {
                "keyword_filter": "1.1",
                "content_generator": "2.0"
            }
        }
        self.config_manager._config_loaded = True

        version = self.config_manager.get_current_prompt_version("keyword_filter")

        assert version == "1.1"

    def test_get_current_prompt_version_default(self):
        """测试获取默认Prompt版本"""
        self.config_manager._prompts_config = {
            "CURRENT_VERSIONS": {}
        }
        self.config_manager._config_loaded = True

        version = self.config_manager.get_current_prompt_version("nonexistent")

        assert version == "1.0"  # 默认值

    def test_check_api_keys(self):
        """测试检查API密钥"""
        # 模拟项目配置（有OpenAI密钥，无Anthropic密钥）
        mock_project_config = Mock(spec=ProjectConfig)
        mock_project_config.openai_api_key = "test-openai-key"
        mock_project_config.anthropic_api_key = ""
        mock_project_config.azure_openai_api_key = ""

        # 模拟WordPress配置（完整）
        mock_wp_config = Mock(spec=WordPressConfig)
        mock_wp_config.url = "https://example.com"
        mock_wp_config.username = "admin"
        mock_wp_config.password = "password"
        mock_wp_config.application_password = ""

        self.config_manager._project_config = mock_project_config
        self.config_manager._wordpress_config = mock_wp_config
        self.config_manager._config_loaded = True

        api_status = self.config_manager.check_api_keys()

        assert api_status["openai"] == True
        assert api_status["anthropic"] == False
        assert api_status["wordpress"] == True  # 有password，满足条件

    def test_check_api_keys_no_config(self):
        """测试检查API密钥（无配置）"""
        self.config_manager._project_config = None
        self.config_manager._wordpress_config = None
        self.config_manager._config_loaded = True

        api_status = self.config_manager.check_api_keys()

        assert api_status == {}

    def test_aimodelconfig_from_dict(self):
        """测试AIModelConfig从字典创建"""
        data = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "cost_per_1k_tokens": 0.03,
            "cost_per_image": 0.04,
            "size": "1024x1024",
            "quality": "standard"
        }

        config = AIModelConfig.from_dict(data)

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.cost_per_1k_tokens == 0.03
        assert config.cost_per_image == 0.04
        assert config.size == "1024x1024"
        assert config.quality == "standard"

    def test_aimodelconfig_from_dict_defaults(self):
        """测试AIModelConfig从字典创建（使用默认值）"""
        data = {
            "provider": "openai",
            "model": "gpt-4",
        }

        config = AIModelConfig.from_dict(data)

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7  # 默认值
        assert config.max_tokens == 1000  # 默认值
        assert config.cost_per_1k_tokens is None
        assert config.cost_per_image is None
        assert config.size is None
        assert config.quality is None

    def test_providerconfig_from_dict(self):
        """测试ProviderConfig从字典创建"""
        data = {
            "api_key_env_var": "OPENAI_API_KEY",
            "base_url_env_var": "OPENAI_BASE_URL",
            "default_base_url": "https://api.openai.com/v1",
            "timeout": 60,
            "max_retries": 5
        }

        config = ProviderConfig.from_dict(data)

        assert config.api_key_env_var == "OPENAI_API_KEY"
        assert config.base_url_env_var == "OPENAI_BASE_URL"
        assert config.default_base_url == "https://api.openai.com/v1"
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_providerconfig_from_dict_defaults(self):
        """测试ProviderConfig从字典创建（使用默认值）"""
        data = {
            "api_key_env_var": "OPENAI_API_KEY",
            "base_url_env_var": "OPENAI_BASE_URL",
            "default_base_url": "https://api.openai.com/v1",
        }

        config = ProviderConfig.from_dict(data)

        assert config.api_key_env_var == "OPENAI_API_KEY"
        assert config.base_url_env_var == "OPENAI_BASE_URL"
        assert config.default_base_url == "https://api.openai.com/v1"
        assert config.timeout == 30  # 默认值
        assert config.max_retries == 3  # 默认值

    def test_wordpressconfig_from_dict(self):
        """测试WordPressConfig从字典创建"""
        data = {
            "WORDPRESS_URL": "https://example.com",
            "WORDPRESS_USERNAME": "admin",
            "WORDPRESS_PASSWORD": "password",
            "WORDPRESS_APPLICATION_PASSWORD": "app_password",
            "WORDPRESS_API_URL": "https://example.com/wp-json",
            "WORDPRESS_XMLRPC_URL": "https://example.com/xmlrpc.php",
            "DEFAULT_POST_STATUS": "publish",
            "DEFAULT_POST_TYPE": "post",
            "DEFAULT_CATEGORY_ID": 2,
            "DEFAULT_TAG_IDS": [1, 2, 3],
            "MEDIA_UPLOAD_PATH": "uploads/ai",
            "ALLOWED_IMAGE_EXTENSIONS": [".jpg", ".png"],
            "MAX_IMAGE_SIZE_MB": 10,
            "SCHEDULE_POSTS": True,
            "DEFAULT_SCHEDULE_HOURS": 48,
            "TIMEZONE": "Asia/Shanghai",
            "VERIFY_SSL": False,
            "TIMEOUT": 60,
            "MAX_RETRIES": 5
        }

        config = WordPressConfig.from_dict(data)

        assert config.url == "https://example.com"
        assert config.username == "admin"
        assert config.password == "password"
        assert config.application_password == "app_password"
        assert config.api_url == "https://example.com/wp-json"
        assert config.xmlrpc_url == "https://example.com/xmlrpc.php"
        assert config.default_post_status == "publish"
        assert config.default_post_type == "post"
        assert config.default_category_id == 2
        assert config.default_tag_ids == [1, 2, 3]
        assert config.media_upload_path == "uploads/ai"
        assert config.allowed_image_extensions == [".jpg", ".png"]
        assert config.max_image_size_mb == 10
        assert config.schedule_posts == True
        assert config.default_schedule_hours == 48
        assert config.timezone == "Asia/Shanghai"
        assert config.verify_ssl == False
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_wordpressconfig_from_dict_defaults(self):
        """测试WordPressConfig从字典创建（使用默认值）"""
        data = {
            "WORDPRESS_URL": "https://example.com",
            "WORDPRESS_USERNAME": "admin",
            "WORDPRESS_PASSWORD": "password",
        }

        config = WordPressConfig.from_dict(data)

        assert config.url == "https://example.com"
        assert config.username == "admin"
        assert config.password == "password"
        assert config.application_password == ""
        assert config.api_url == ""
        assert config.xmlrpc_url == ""
        assert config.default_post_status == "draft"  # 默认值
        assert config.default_post_type == "post"  # 默认值
        assert config.default_category_id == 1  # 默认值
        assert config.default_tag_ids == []  # 默认值
        assert config.media_upload_path == "ai-generated"  # 默认值
        assert config.allowed_image_extensions == [".jpg", ".jpeg", ".png", ".gif", ".webp"]  # 默认值
        assert config.max_image_size_mb == 5  # 默认值
        assert config.schedule_posts == False  # 默认值
        assert config.default_schedule_hours == 24  # 默认值
        assert config.timezone == "UTC"  # 默认值
        assert config.verify_ssl == True  # 默认值
        assert config.timeout == 30  # 默认值
        assert config.max_retries == 3  # 默认值

    def test_projectconfig_from_dict(self):
        """测试ProjectConfig从字典创建"""
        data = {
            "BASE_DIR": "/test/path",
            "DATA_DIR": "/test/path/data",
            "INPUT_DIR": "/test/path/input",
            "OUTPUT_DIR": "/test/path/output",
            "CACHE_DIR": "/test/path/cache",
            "LOGS_DIR": "/test/path/logs",
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-azure-key",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-5.4",
            "AZURE_OPENAI_API_VERSION": "2024-12-01-preview",
            "DEFAULT_AI_MODEL": "gpt-4",
            "MAX_KEYWORDS_PER_BATCH": 200,
            "MAX_FILE_SIZE_MB": 20,
            "ARTICLE_WORD_COUNT": 2000,
            "TITLES_PER_KEYWORD": 5,
            "REQUEST_TIMEOUT": 60,
            "MAX_RETRIES": 5,
            "RETRY_DELAY": 10,
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "%(asctime)s - %(message)s",
            "LOG_FILE": "logs/test.log",
            "DEBUG": True
        }

        config = ProjectConfig.from_dict(data)

        assert config.base_dir == Path("/test/path")
        assert config.data_dir == Path("/test/path/data")
        assert config.input_dir == Path("/test/path/input")
        assert config.output_dir == Path("/test/path/output")
        assert config.cache_dir == Path("/test/path/cache")
        assert config.logs_dir == Path("/test/path/logs")
        assert config.openai_api_key == "test-openai-key"
        assert config.anthropic_api_key == "test-anthropic-key"
        assert config.openai_base_url == "https://api.openai.com/v1"
        assert config.anthropic_base_url == "https://api.anthropic.com"
        assert config.azure_openai_endpoint == "https://test.openai.azure.com/"
        assert config.azure_openai_api_key == "test-azure-key"
        assert config.azure_openai_deployment == "gpt-5.4"
        assert config.azure_openai_api_version == "2024-12-01-preview"
        assert config.default_ai_model == "gpt-4"
        assert config.max_keywords_per_batch == 200
        assert config.max_file_size_mb == 20
        assert config.article_word_count == 2000
        assert config.titles_per_keyword == 5
        assert config.request_timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 10
        assert config.log_level == "DEBUG"
        assert config.log_format == "%(asctime)s - %(message)s"
        assert config.log_file == Path("logs/test.log")
        assert config.debug == True

    def test_projectconfig_from_dict_defaults(self):
        """测试ProjectConfig从字典创建（使用默认值）"""
        data = {
            "BASE_DIR": "/test/path",
            "OPENAI_API_KEY": "test-openai-key",
        }

        config = ProjectConfig.from_dict(data)

        assert config.base_dir == Path("/test/path")
        assert config.data_dir == Path("")  # 默认值
        assert config.openai_api_key == "test-openai-key"
        assert config.anthropic_api_key == ""  # 默认值
        assert config.openai_base_url == "https://api.openai.com/v1"  # 默认值
        assert config.anthropic_base_url == "https://api.anthropic.com"  # 默认值
        assert config.azure_openai_endpoint == ""  # 默认值
        assert config.azure_openai_api_key == ""  # 默认值
        assert config.azure_openai_deployment == ""  # 默认值
        assert config.azure_openai_api_version == "2024-12-01-preview"  # 默认值
        assert config.default_ai_model == "gpt-4"  # 默认值
        assert config.max_keywords_per_batch == 100  # 默认值
        assert config.max_file_size_mb == 10  # 默认值
        assert config.article_word_count == 1500  # 默认值
        assert config.titles_per_keyword == 3  # 默认值
        assert config.request_timeout == 30  # 默认值
        assert config.max_retries == 3  # 默认值
        assert config.retry_delay == 5  # 默认值
        assert config.log_level == "INFO"  # 默认值
        assert config.log_format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # 默认值
        assert config.log_file == Path("logs/workflow.log")  # 默认值
        assert config.debug == False  # 默认值

    def test_global_config_manager(self):
        """测试全局配置管理器实例"""
        # 测试全局实例存在
        assert config_manager is not None
        assert isinstance(config_manager, ConfigManager)

        # 测试获取函数
        manager = get_config()
        assert manager is config_manager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])