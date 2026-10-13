"""
WordPress API客户端
提供WordPress REST API和XML-RPC的集成
"""

import json
import time
import base64
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import mimetypes

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError

from src.utils import (
    get_logger,
    config_manager,
    exception_handler,
    APIError,
    RateLimitError,
)

# 尝试导入WordPress库
try:
    from wordpress_xmlrpc import Client, WordPressPost
    from wordpress_xmlrpc.methods.posts import GetPosts, NewPost
    from wordpress_xmlrpc.methods.media import UploadFile
    from wordpress_xmlrpc.methods.taxonomies import GetTaxonomies, GetTerms
    WORDPRESS_XMLRPC_AVAILABLE = True
except ImportError:
    WORDPRESS_XMLRPC_AVAILABLE = False
    Client = None
    WordPressPost = None


class WordPressPublishStatus(Enum):
    """WordPress发布状态"""
    DRAFT = "draft"
    PUBLISH = "publish"
    PENDING = "pending"
    PRIVATE = "private"
    FUTURE = "future"  # 定时发布


@dataclass
class WordPressPostData:
    """WordPress文章数据"""
    title: str
    content: str
    excerpt: Optional[str] = None
    status: str = "draft"
    categories: List[int] = field(default_factory=list)
    tags: List[int] = field(default_factory=list)
    featured_media: Optional[int] = None
    author: Optional[int] = None
    format: str = "standard"  # standard, aside, image, video, etc.
    comment_status: str = "open"  # open, closed
    ping_status: str = "open"  # open, closed
    sticky: bool = False
    template: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    slug: Optional[str] = None
    date: Optional[str] = None  # ISO格式: 2024-01-01T12:00:00


@dataclass
class WordPressMediaData:
    """WordPress媒体数据"""
    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    description: Optional[str] = None


@dataclass
class WordPressCategory:
    """WordPress分类"""
    id: int
    name: str
    slug: str
    description: str
    count: int
    parent: int


@dataclass
class WordPressTag:
    """WordPress标签"""
    id: int
    name: str
    slug: str
    description: str
    count: int


class WordPressAPIError(Exception):
    """WordPress API错误"""
    pass


class WordPressAuthenticationError(WordPressAPIError):
    """WordPress认证错误"""
    pass


class WordPressRateLimitError(WordPressAPIError):
    """WordPress速率限制错误"""
    pass


class WordPressClient:
    """WordPress客户端基类"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        use_application_password: bool = True,
        verify_ssl: bool = True,
        timeout: int = 30
    ):
        """
        初始化WordPress客户端

        Args:
            base_url: WordPress站点URL
            username: 用户名
            password: 密码或应用密码
            use_application_password: 是否使用应用密码
            verify_ssl: 是否验证SSL证书
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.use_application_password = use_application_password
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self.logger = get_logger("wordpress_client")
        self.rest_api_url = f"{self.base_url}/wp-json/wp/v2"
        self.xmlrpc_url = f"{self.base_url}/xmlrpc.php"

        # 认证
        if self.use_application_password:
            self.auth = HTTPBasicAuth(self.username, self.password)
        else:
            # 对于普通密码，可能需要不同的认证方式
            self.auth = HTTPBasicAuth(self.username, self.password)

        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            "User-Agent": "SEO Content Automation Workflow/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        self.logger.info(
            f"WordPress客户端初始化",
            base_url=self.base_url,
            username=self.username,
            use_application_password=use_application_password
        )

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.session.get(
                f"{self.rest_api_url}/posts",
                params={"per_page": 1},
                timeout=self.timeout
            )
            response.raise_for_status()

            # 检查是否是有效的WordPress REST API响应
            if response.headers.get('Content-Type', '').startswith('application/json'):
                self.logger.info("WordPress连接测试成功")
                return True
            else:
                self.logger.warning("WordPress连接测试失败：无效的响应格式")
                return False

        except Exception as e:
            self.logger.error(f"WordPress连接测试失败: {e}")
            return False

    def create_post(self, post_data: WordPressPostData) -> Dict[str, Any]:
        """创建文章（子类必须实现）"""
        raise NotImplementedError

    def upload_media(self, media_data: WordPressMediaData) -> Dict[str, Any]:
        """上传媒体（子类必须实现）"""
        raise NotImplementedError

    def get_categories(self, **kwargs) -> List[WordPressCategory]:
        """获取分类列表（子类必须实现）"""
        raise NotImplementedError

    def get_tags(self, **kwargs) -> List[WordPressTag]:
        """获取标签列表（子类必须实现）"""
        raise NotImplementedError

    def _handle_api_error(self, response: requests.Response) -> None:
        """处理API错误"""
        if response.status_code == 401:
            raise WordPressAuthenticationError(f"认证失败: {response.text}")
        elif response.status_code == 429:
            raise WordPressRateLimitError(f"速率限制: {response.text}")
        elif 400 <= response.status_code < 500:
            raise WordPressAPIError(f"客户端错误 ({response.status_code}): {response.text}")
        elif 500 <= response.status_code < 600:
            raise WordPressAPIError(f"服务器错误 ({response.status_code}): {response.text}")
        else:
            response.raise_for_status()


class WordPressRESTClient(WordPressClient):
    """WordPress REST API客户端"""

    def create_post(self, post_data: WordPressPostData) -> Dict[str, Any]:
        """创建文章"""
        url = f"{self.rest_api_url}/posts"

        # 准备请求数据
        request_data = {
            "title": post_data.title,
            "content": post_data.content,
            "status": post_data.status,
            "categories": post_data.categories,
            "tags": post_data.tags,
        }

        # 可选字段
        if post_data.excerpt:
            request_data["excerpt"] = post_data.excerpt
        if post_data.featured_media:
            request_data["featured_media"] = post_data.featured_media
        if post_data.author:
            request_data["author"] = post_data.author
        if post_data.format:
            request_data["format"] = post_data.format
        if post_data.comment_status:
            request_data["comment_status"] = post_data.comment_status
        if post_data.ping_status:
            request_data["ping_status"] = post_data.ping_status
        if post_data.sticky:
            request_data["sticky"] = post_data.sticky
        if post_data.template:
            request_data["template"] = post_data.template
        if post_data.meta:
            request_data["meta"] = post_data.meta
        if post_data.slug:
            request_data["slug"] = post_data.slug
        if post_data.date:
            request_data["date"] = post_data.date

        try:
            self.logger.debug(f"创建WordPress文章: {post_data.title}")
            response = self.session.post(
                url,
                json=request_data,
                timeout=self.timeout
            )

            if response.status_code != 201:
                self._handle_api_error(response)

            result = response.json()
            self.logger.info(f"文章创建成功: {result.get('id')} - {post_data.title}")
            return result

        except RequestException as e:
            self.logger.error(f"创建文章失败: {e}")
            raise WordPressAPIError(f"创建文章失败: {e}")

    def upload_media(self, media_data: WordPressMediaData) -> Dict[str, Any]:
        """上传媒体文件"""
        url = f"{self.rest_api_url}/media"

        # 确定文件内容和MIME类型
        if media_data.file_path:
            with open(media_data.file_path, 'rb') as f:
                file_content = f.read()
            file_name = media_data.file_name or media_data.file_path.split('/')[-1]
            mime_type = media_data.mime_type or mimetypes.guess_type(media_data.file_path)[0] or 'application/octet-stream'
        elif media_data.file_content:
            file_content = media_data.file_content
            file_name = media_data.file_name or 'upload.jpg'
            mime_type = media_data.mime_type or 'application/octet-stream'
        else:
            raise ValueError("必须提供file_path或file_content")

        # 准备文件上传
        files = {
            'file': (file_name, file_content, mime_type)
        }

        # 准备其他字段
        data = {}
        if media_data.caption:
            data['caption'] = media_data.caption
        if media_data.alt_text:
            data['alt_text'] = media_data.alt_text
        if media_data.description:
            data['description'] = media_data.description

        # Override session-level Content-Type so requests auto-sets multipart/form-data
        # Deleting from a copy is not enough — the session default still bleeds through.
        headers = {"Content-Type": None}

        try:
            self.logger.debug(f"上传媒体文件: {file_name}")
            response = self.session.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=self.timeout * 2  # 媒体上传需要更长时间
            )

            if response.status_code != 201:
                self._handle_api_error(response)

            result = response.json()
            self.logger.info(f"媒体上传成功: {result.get('id')} - {file_name}")
            return result

        except RequestException as e:
            self.logger.error(f"上传媒体失败: {e}")
            raise WordPressAPIError(f"上传媒体失败: {e}")

    def get_posts(self, status: str = "draft", per_page: int = 100, **kwargs) -> List[Dict[str, Any]]:
        """获取文章列表"""
        url = f"{self.rest_api_url}/posts"
        params = {"status": status, "per_page": per_page, **kwargs}
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            posts = response.json()
            self.logger.debug(f"获取文章列表: status={status}, count={len(posts)}")
            return posts
        except RequestException as e:
            self.logger.error(f"获取文章列表失败: {e}")
            raise WordPressAPIError(f"获取文章列表失败: {e}")

    def update_post(self, post_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新文章"""
        url = f"{self.rest_api_url}/posts/{post_id}"
        try:
            response = self.session.post(url, json=data, timeout=self.timeout)
            if response.status_code < 200 or response.status_code >= 300:
                self._handle_api_error(response)
            result = response.json()
            self.logger.info(f"文章更新成功: {post_id}, status={data.get('status', '?')}")
            return result
        except RequestException as e:
            self.logger.error(f"更新文章失败: {e}")
            raise WordPressAPIError(f"更新文章失败: {e}")

    def get_categories(self, **kwargs) -> List[WordPressCategory]:
        """获取分类列表"""
        url = f"{self.rest_api_url}/categories"

        try:
            response = self.session.get(url, params=kwargs, timeout=self.timeout)
            response.raise_for_status()

            categories_data = response.json()
            categories = []

            for cat_data in categories_data:
                category = WordPressCategory(
                    id=cat_data.get('id'),
                    name=cat_data.get('name', ''),
                    slug=cat_data.get('slug', ''),
                    description=cat_data.get('description', ''),
                    count=cat_data.get('count', 0),
                    parent=cat_data.get('parent', 0)
                )
                categories.append(category)

            return categories

        except RequestException as e:
            self.logger.error(f"获取分类失败: {e}")
            raise WordPressAPIError(f"获取分类失败: {e}")

    def get_tags(self, **kwargs) -> List[WordPressTag]:
        """获取标签列表"""
        url = f"{self.rest_api_url}/tags"

        try:
            response = self.session.get(url, params=kwargs, timeout=self.timeout)
            response.raise_for_status()

            tags_data = response.json()
            tags = []

            for tag_data in tags_data:
                tag = WordPressTag(
                    id=tag_data.get('id'),
                    name=tag_data.get('name', ''),
                    slug=tag_data.get('slug', ''),
                    description=tag_data.get('description', ''),
                    count=tag_data.get('count', 0)
                )
                tags.append(tag)

            return tags

        except RequestException as e:
            self.logger.error(f"获取标签失败: {e}")
            raise WordPressAPIError(f"获取标签失败: {e}")

    def create_category(self, name: str, **kwargs) -> WordPressCategory:
        """创建分类"""
        url = f"{self.rest_api_url}/categories"

        request_data = {"name": name}
        request_data.update(kwargs)

        try:
            response = self.session.post(url, json=request_data, timeout=self.timeout)
            response.raise_for_status()

            cat_data = response.json()
            category = WordPressCategory(
                id=cat_data.get('id'),
                name=cat_data.get('name', ''),
                slug=cat_data.get('slug', ''),
                description=cat_data.get('description', ''),
                count=cat_data.get('count', 0),
                parent=cat_data.get('parent', 0)
            )

            self.logger.info(f"分类创建成功: {category.id} - {category.name}")
            return category

        except RequestException as e:
            self.logger.error(f"创建分类失败: {e}")
            raise WordPressAPIError(f"创建分类失败: {e}")

    def create_tag(self, name: str, **kwargs) -> WordPressTag:
        """创建标签"""
        url = f"{self.rest_api_url}/tags"

        request_data = {"name": name}
        request_data.update(kwargs)

        try:
            response = self.session.post(url, json=request_data, timeout=self.timeout)
            response.raise_for_status()

            tag_data = response.json()
            tag = WordPressTag(
                id=tag_data.get('id'),
                name=tag_data.get('name', ''),
                slug=tag_data.get('slug', ''),
                description=tag_data.get('description', ''),
                count=tag_data.get('count', 0)
            )

            self.logger.info(f"标签创建成功: {tag.id} - {tag.name}")
            return tag

        except RequestException as e:
            self.logger.error(f"创建标签失败: {e}")
            raise WordPressAPIError(f"创建标签失败: {e}")


class WordPressXMLRPCClient(WordPressClient):
    """WordPress XML-RPC客户端"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not WORDPRESS_XMLRPC_AVAILABLE:
            raise ImportError("python-wordpress-xmlrpc库未安装")

        # XML-RPC客户端
        self.xmlrpc_client = Client(
            self.xmlrpc_url,
            self.username,
            self.password
        )

    def create_post(self, post_data: WordPressPostData) -> Dict[str, Any]:
        """创建文章（XML-RPC）"""
        try:
            wp_post = WordPressPost()
            wp_post.title = post_data.title
            wp_post.content = post_data.content

            if post_data.excerpt:
                wp_post.excerpt = post_data.excerpt

            # XML-RPC使用字符串状态
            wp_post.post_status = post_data.status

            # 分类和标签
            if post_data.categories:
                wp_post.terms_names = {
                    'category': [str(cat_id) for cat_id in post_data.categories]
                }

            # 其他字段
            if post_data.slug:
                wp_post.slug = post_data.slug

            self.logger.debug(f"通过XML-RPC创建WordPress文章: {post_data.title}")
            post_id = self.xmlrpc_client.call(NewPost(wp_post))

            self.logger.info(f"文章创建成功 (XML-RPC): {post_id} - {post_data.title}")
            return {"id": post_id, "title": post_data.title}

        except Exception as e:
            self.logger.error(f"通过XML-RPC创建文章失败: {e}")
            raise WordPressAPIError(f"通过XML-RPC创建文章失败: {e}")

    def upload_media(self, media_data: WordPressMediaData) -> Dict[str, Any]:
        """上传媒体文件（XML-RPC）"""
        # XML-RPC媒体上传需要不同的实现
        # 这里简化处理
        self.logger.warning("XML-RPC媒体上传功能待实现")
        return {"id": 0, "url": "", "message": "XML-RPC媒体上传功能待实现"}

    def get_categories(self, **kwargs) -> List[WordPressCategory]:
        """获取分类列表（XML-RPC）"""
        try:
            # XML-RPC获取分类的方式不同
            # 这里简化处理
            self.logger.warning("XML-RPC获取分类功能待实现")
            return []

        except Exception as e:
            self.logger.error(f"通过XML-RPC获取分类失败: {e}")
            raise WordPressAPIError(f"通过XML-RPC获取分类失败: {e}")

    def get_tags(self, **kwargs) -> List[WordPressTag]:
        """获取标签列表（XML-RPC）"""
        try:
            # XML-RPC获取标签的方式不同
            # 这里简化处理
            self.logger.warning("XML-RPC获取标签功能待实现")
            return []

        except Exception as e:
            self.logger.error(f"通过XML-RPC获取标签失败: {e}")
            raise WordPressAPIError(f"通过XML-RPC获取标签失败: {e}")


# 工厂函数
def create_wordpress_client(
    api_type: str = "rest",
    **kwargs
) -> WordPressClient:
    """
    创建WordPress客户端工厂函数

    Args:
        api_type: API类型，'rest' 或 'xmlrpc'
        **kwargs: 传递给客户端构造函数的参数

    Returns:
        WordPressClient实例
    """
    # 设置默认值
    default_kwargs = {
        "use_application_password": True,
        "verify_ssl": True,
        "timeout": 30,
    }

    # 用提供的参数覆盖默认值
    default_kwargs.update(kwargs)

    if api_type.lower() == "rest":
        return WordPressRESTClient(**default_kwargs)
    elif api_type.lower() == "xmlrpc":
        return WordPressXMLRPCClient(**default_kwargs)
    else:
        raise ValueError(f"不支持的API类型: {api_type}")


# 便捷函数：从配置创建客户端
def get_wordpress_client(
    api_type: str = "rest",
    use_config: bool = True,
    **kwargs
) -> WordPressClient:
    """
    获取WordPress客户端

    Args:
        api_type: API类型
        use_config: 是否使用配置文件中的设置
        **kwargs: 覆盖配置的参数

    Returns:
        WordPressClient实例
    """
    if use_config:
        # 从配置管理器获取配置
        wp_config = config_manager.wordpress_config

        client_kwargs = {
            "base_url": wp_config.url,
            "username": wp_config.username,
            "password": wp_config.application_password or wp_config.password,
            "use_application_password": bool(wp_config.application_password),
            "verify_ssl": wp_config.verify_ssl,
            "timeout": wp_config.timeout
        }

        # 用提供的参数覆盖配置
        client_kwargs.update(kwargs)
    else:
        client_kwargs = kwargs

    return create_wordpress_client(api_type=api_type, **client_kwargs)