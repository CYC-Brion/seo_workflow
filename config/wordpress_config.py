"""
WordPress配置
包含WordPress站点连接信息
"""

import os

# WordPress站点配置
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://your-wordpress-site.com")
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "admin")
WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD", "")
WORDPRESS_APPLICATION_PASSWORD = os.getenv("WORDPRESS_APPLICATION_PASSWORD", "")

# API端点
WORDPRESS_API_URL = f"{WORDPRESS_URL}/wp-json/wp/v2"
WORDPRESS_XMLRPC_URL = f"{WORDPRESS_URL}/xmlrpc.php"

# 文章发布设置
DEFAULT_POST_STATUS = "draft"  # draft, publish, pending, private
DEFAULT_POST_TYPE = "post"     # post, page
DEFAULT_CATEGORY_ID = 1        # 默认分类ID
DEFAULT_TAG_IDS = []           # 默认标签ID列表

# 媒体设置
MEDIA_UPLOAD_PATH = "ai-generated"  # 媒体上传子目录
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
MAX_IMAGE_SIZE_MB = 5

# 发布计划
SCHEDULE_POSTS = False
DEFAULT_SCHEDULE_HOURS = 24  # 默认在24小时后发布
TIMEZONE = "UTC"  # 时区设置

# 验证配置
VERIFY_SSL = True
TIMEOUT = 30
MAX_RETRIES = 3
