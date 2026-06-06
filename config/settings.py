"""
全局配置文件
包含API密钥、路径配置等敏感信息，请不要提交到版本控制系统
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录路径
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"

# 创建必要的目录
for directory in [INPUT_DIR, OUTPUT_DIR, CACHE_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# AI模型配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

# Azure OpenAI 配置（优先于标准 OpenAI）
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# 默认AI模型选择
DEFAULT_AI_MODEL = "gpt-4o"  # 可选: gpt-4o-mini, gpt-4o, claude-3-5-sonnet 等

# 工作流配置
MAX_KEYWORDS_PER_BATCH = 100
MAX_FILE_SIZE_MB = 10
ARTICLE_WORD_COUNT = 1500
TITLES_PER_KEYWORD = 3

# 性能配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_log_file_override = os.getenv("SEO_LOG_FILE")
if _log_file_override is not None:
    LOG_FILE = Path(_log_file_override) if _log_file_override else None
else:
    LOG_FILE = LOGS_DIR / "workflow.log"

# 开发模式
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
