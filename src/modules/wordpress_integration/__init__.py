"""
WordPress集成模块
将生成的文章发布到WordPress网站
"""

from .wp_api_client import (
    WordPressClient,
    WordPressRESTClient,
    WordPressXMLRPCClient,
    WordPressPostData,
    WordPressMediaData,
    WordPressCategory,
    WordPressTag,
    WordPressAPIError,
    WordPressAuthenticationError,
    WordPressRateLimitError,
    create_wordpress_client,
    get_wordpress_client,
)

from .wordpress_publisher import WordPressPublisher

__all__ = [
    # 客户端类
    "WordPressClient",
    "WordPressRESTClient",
    "WordPressXMLRPCClient",

    # 数据类
    "WordPressPostData",
    "WordPressMediaData",
    "WordPressCategory",
    "WordPressTag",

    # 错误类
    "WordPressAPIError",
    "WordPressAuthenticationError",
    "WordPressRateLimitError",

    # 工厂函数
    "create_wordpress_client",
    "get_wordpress_client",

    # 发布器节点
    "WordPressPublisher",
]