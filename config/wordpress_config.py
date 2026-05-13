"""
WordPress configuration.

This module intentionally reads sensitive credentials from environment
variables only. Do not hardcode production credentials in source control.
"""

import os


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None and value != "" else default


# WordPress site configuration
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "")
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "")
WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD", "")
WORDPRESS_APPLICATION_PASSWORD = os.getenv("WORDPRESS_APPLICATION_PASSWORD", "")

# API endpoints
WORDPRESS_API_URL = f"{WORDPRESS_URL.rstrip('/')}/wp-json/wp/v2" if WORDPRESS_URL else ""
WORDPRESS_XMLRPC_URL = f"{WORDPRESS_URL.rstrip('/')}/xmlrpc.php" if WORDPRESS_URL else ""

# Article publishing defaults
DEFAULT_POST_STATUS = "draft"  # draft, publish, pending, private
DEFAULT_POST_TYPE = "post"  # post, page
DEFAULT_CATEGORY_ID = 1022  # Technical Guides
DEFAULT_TAG_IDS = []

# Category mapping used by the AI workflow
CATEGORY_MAPPING = {
    "Technical Guides": 1022,
    "Industry Insights": 1021,
}
DEFAULT_AI_CATEGORY = "Technical Guides"

# Media settings
MEDIA_UPLOAD_PATH = "ai-generated"
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
MAX_IMAGE_SIZE_MB = 5

# Scheduling settings
SCHEDULE_POSTS = _get_bool_env("SCHEDULE_POSTS", True)
DEFAULT_SCHEDULE_HOURS = _get_int_env("DEFAULT_SCHEDULE_HOURS", 1)
DEFAULT_SCHEDULE_INTERVAL_HOURS = _get_int_env("DEFAULT_SCHEDULE_INTERVAL_HOURS", 1)
TIMEZONE = os.getenv("WORDPRESS_TIMEZONE", "UTC")

# Request settings
VERIFY_SSL = _get_bool_env("WORDPRESS_VERIFY_SSL", True)
TIMEOUT = _get_int_env("WORDPRESS_TIMEOUT", 30)
MAX_RETRIES = _get_int_env("WORDPRESS_MAX_RETRIES", 3)
