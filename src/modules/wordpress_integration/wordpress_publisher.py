"""
WordPress发布器节点
将生成的文章发布到WordPress网站的工作流节点
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

from src.core import DataProcessingNode
from src.utils import (
    get_logger,
    config_manager,
    exception_handler,
)

from .wp_api_client import (
    WordPressPostData,
    WordPressMediaData,
    get_wordpress_client,
    WordPressAPIError,
)
from src.enhanced_features.image_integration.editorial_image_library import (
    build_inline_image_html,
)


@dataclass
class WordPressPublishResult:
    """WordPress发布结果"""
    post_id: int
    title: str
    status: str
    url: str
    published_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WordPressPublishInput:
    """WordPress发布输入数据"""
    title: str
    content: str
    keyword: Optional[str] = None
    excerpt: Optional[str] = None
    slug: Optional[str] = None
    categories: List[str] = field(default_factory=list)  # 分类名称列表
    tags: List[str] = field(default_factory=list)  # 标签名称列表
    featured_image_url: Optional[str] = None
    featured_image_path: Optional[str] = None
    editorial_images: List[Dict[str, Any]] = field(default_factory=list)
    publish_status: str = "draft"  # draft, publish, pending, private
    schedule_date: Optional[str] = None  # ISO格式: 2024-01-01T12:00:00
    author_id: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class WordPressPublisher(DataProcessingNode):
    """WordPress发布器节点"""

    def __init__(
        self,
        node_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化WordPress发布器

        Args:
            node_id: 节点ID
            config: 配置字典，包含以下键：
                - batch_size: 批量处理大小（默认: 5）
                - api_type: API类型，'rest' 或 'xmlrpc'（默认: 'rest'）
                - default_status: 默认发布状态（默认: 'draft'）
                - default_category_id: 默认分类ID
                - auto_create_categories: 是否自动创建分类（默认: False）
                - auto_create_tags: 是否自动创建标签（默认: False）
                - enable_media_upload: 是否启用媒体上传（默认: False）
                - max_retries: 最大重试次数（默认: 3）
                - retry_delay: 重试延迟（秒，默认: 5）
        """
        config = config or {}
        super().__init__(node_id, "wordpress_publisher", config)

        # 配置参数
        self.batch_size = config.get("batch_size", 5)
        self.api_type = config.get("api_type", "rest")
        self.default_status = config.get("default_status", "draft")
        self.default_category_id = config.get("default_category_id", 1)
        self.auto_create_categories = config.get("auto_create_categories", False)
        self.auto_create_tags = config.get("auto_create_tags", False)
        self.enable_media_upload = config.get("enable_media_upload", False)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 5)

        # WordPress客户端
        self.wp_client = None

        # 分类和标签缓存
        self.categories_cache: Dict[str, int] = {}  # 分类名称 -> ID
        self.tags_cache: Dict[str, int] = {}  # 标签名称 -> ID

        # 统计数据
        self.stats = {
            "total_posts": 0,
            "posts_published": 0,
            "posts_failed": 0,
            "categories_created": 0,
            "tags_created": 0,
            "media_uploads": 0,
            "batches_processed": 0,
            "api_errors": 0,
            "total_time": 0.0,
        }

        self.logger.info(
            f"WordPress发布器初始化: {node_id}",
            config={
                "batch_size": self.batch_size,
                "api_type": self.api_type,
                "default_status": self.default_status,
                "auto_create_categories": self.auto_create_categories,
                "auto_create_tags": self.auto_create_tags,
            }
        )

    def _initialize_client(self) -> None:
        """初始化WordPress客户端"""
        if self.wp_client is None:
            try:
                self.wp_client = get_wordpress_client(api_type=self.api_type)
                self.logger.debug("WordPress客户端初始化成功")
            except Exception as e:
                self.logger.error(f"初始化WordPress客户端失败: {e}")
                raise

    def _get_or_create_category(self, category_name: str) -> Optional[int]:
        """获取或创建分类"""
        if category_name in self.categories_cache:
            return self.categories_cache[category_name]

        try:
            categories = self.wp_client.get_categories(search=category_name)
            for category in categories:
                if category.name.lower() == category_name.lower():
                    self.categories_cache[category_name] = category.id
                    return category.id

            # 分类不存在，根据配置决定是否创建
            if self.auto_create_categories:
                try:
                    category = self.wp_client.create_category(name=category_name)
                    self.categories_cache[category_name] = category.id
                    self.stats["categories_created"] += 1
                    self.logger.info(f"创建分类: {category_name} (ID: {category.id})")
                    return category.id
                except Exception as e:
                    self.logger.warning(f"创建分类失败 '{category_name}': {e}")
                    return None
            else:
                self.logger.warning(f"分类不存在且未启用自动创建: {category_name}")
                return None

        except Exception as e:
            self.logger.error(f"获取分类失败: {e}")
            return None

    def _get_or_create_tag(self, tag_name: str) -> Optional[int]:
        """获取或创建标签"""
        if tag_name in self.tags_cache:
            return self.tags_cache[tag_name]

        try:
            tags = self.wp_client.get_tags(search=tag_name)
            for tag in tags:
                if tag.name.lower() == tag_name.lower():
                    self.tags_cache[tag_name] = tag.id
                    return tag.id

            # 标签不存在，根据配置决定是否创建
            if self.auto_create_tags:
                try:
                    tag = self.wp_client.create_tag(name=tag_name)
                    self.tags_cache[tag_name] = tag.id
                    self.stats["tags_created"] += 1
                    self.logger.info(f"创建标签: {tag_name} (ID: {tag.id})")
                    return tag.id
                except Exception as e:
                    self.logger.warning(f"创建标签失败 '{tag_name}': {e}")
                    return None
            else:
                self.logger.warning(f"标签不存在且未启用自动创建: {tag_name}")
                return None

        except Exception as e:
            self.logger.error(f"获取标签失败: {e}")
            return None

    def _process_single_post(self, post_input: WordPressPublishInput) -> WordPressPublishResult:
        """处理单个文章发布"""
        try:
            # 转换分类名称到ID
            category_ids = []
            for category_name in post_input.categories:
                category_id = self._get_or_create_category(category_name)
                if category_id:
                    category_ids.append(category_id)

            # 如果没有分类，使用默认分类
            if not category_ids and self.default_category_id:
                category_ids.append(self.default_category_id)

            # 转换标签名称到ID
            tag_ids = []
            for tag_name in post_input.tags:
                tag_id = self._get_or_create_tag(tag_name)
                if tag_id:
                    tag_ids.append(tag_id)

            # 处理定时发布
            post_date = None
            publish_status = post_input.publish_status or self.default_status
            if post_input.publish_status == "future" and post_input.schedule_date:
                post_date = post_input.schedule_date
            elif post_input.publish_status == "publish" and post_input.schedule_date:
                # 如果有定时日期，使用future状态
                post_date = post_input.schedule_date
                publish_status = "future"
            else:
                publish_status = post_input.publish_status or self.default_status

            content = post_input.content
            featured_media_id = None
            uploaded_editorial_media: List[Dict[str, Any]] = []

            if self.enable_media_upload:
                content, uploaded_editorial_media = self._upload_editorial_images(
                    content, post_input.editorial_images
                )
                featured_media_id = self._upload_featured_image(post_input)

            # 创建文章数据
            wp_post_data = WordPressPostData(
                title=post_input.title,
                content=content,
                excerpt=post_input.excerpt,
                slug=post_input.slug,
                status=publish_status,
                categories=category_ids,
                tags=tag_ids,
                author=post_input.author_id,
                meta=post_input.meta,
                date=post_date
            )

            # Retain legacy remote featured-image support for existing callers.
            if self.enable_media_upload and not featured_media_id and post_input.featured_image_url:
                try:
                    self.logger.info(f"下载特色图片: {post_input.featured_image_url}")
                    response = requests.get(
                        post_input.featured_image_url,
                        timeout=30,
                        headers={"User-Agent": "SEO-Workflow/1.0"},
                    )
                    response.raise_for_status()
                    image_bytes = response.content

                    # 从 URL 提取文件名和 MIME 类型
                    url_path = post_input.featured_image_url.split("?")[0]
                    file_name = url_path.split("/")[-1] or "featured_image.jpg"
                    content_type = response.headers.get("Content-Type", "")
                    if content_type.startswith("image/"):
                        ext_map = {
                            "image/jpeg": ".jpg", "image/png": ".png",
                            "image/gif": ".gif", "image/webp": ".webp",
                        }
                        ext = ext_map.get(content_type.split(";")[0], ".jpg")
                        if not file_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                            file_name = f"featured_image{ext}"

                    # 上传到 WordPress
                    media_data = WordPressMediaData(
                        file_content=image_bytes,
                        file_name=file_name,
                        mime_type=content_type or "image/jpeg",
                        alt_text=post_input.title,
                    )
                    media_result = self.wp_client.upload_media(media_data)
                    featured_media_id = media_result.get("id")
                    self.stats["media_uploads"] += 1
                    self.logger.info(f"特色图片上传成功, media_id={featured_media_id}")

                except requests.RequestException as req_err:
                    self.logger.warning(f"下载特色图片失败 (网络错误): {req_err}")
                except WordPressAPIError as api_err:
                    self.logger.warning(f"上传特色图片到WordPress失败: {api_err}")
                except Exception as e:
                    self.logger.warning(f"上传特色图片失败: {e}")

            if featured_media_id:
                wp_post_data.featured_media = featured_media_id

            # 发布文章
            self.logger.info(f"发布文章到WordPress: {post_input.title}")
            post_result = self.wp_client.create_post(wp_post_data)

            # 构建结果
            result = WordPressPublishResult(
                post_id=post_result.get("id", 0),
                title=post_input.title,
                status=publish_status,
                url=post_result.get("link", ""),
                published_at=post_result.get("date", None),
                metadata={
                    "wordpress_id": post_result.get("id"),
                    "categories": category_ids,
                    "tags": tag_ids,
                    "featured_media": featured_media_id,
                    "editorial_media": uploaded_editorial_media,
                }
            )

            self.stats["posts_published"] += 1
            self.logger.info(f"文章发布成功: {post_input.title} (ID: {result.post_id})")

            return result

        except WordPressAPIError as e:
            self.stats["posts_failed"] += 1
            self.stats["api_errors"] += 1
            self.logger.error(f"发布文章失败: {post_input.title} - {e}")

            return WordPressPublishResult(
                post_id=0,
                title=post_input.title,
                status="failed",
                url="",
                error=str(e),
                metadata={"error_details": str(e)}
            )

        except Exception as e:
            self.stats["posts_failed"] += 1
            self.logger.error(f"发布文章时发生意外错误: {post_input.title} - {e}")

            return WordPressPublishResult(
                post_id=0,
                title=post_input.title,
                status="failed",
                url="",
                error=str(e),
                metadata={"error_details": str(e)}
            )

    def _upload_featured_image(self, post_input: WordPressPublishInput) -> Optional[int]:
        """Upload the locally selected featured image and return its media ID."""
        if not post_input.featured_image_path:
            return None
        image = {
            "path": post_input.featured_image_path,
            "alt_text": post_input.title,
            "caption": post_input.title,
        }
        result = self._upload_local_image(image)
        return result.get("id") if result else None

    def _upload_editorial_images(
        self, content: str, editorial_images: List[Dict[str, Any]]
    ) -> tuple:
        """Upload local body images and replace their safe HTML placeholders."""
        uploaded: List[Dict[str, Any]] = []
        for image in editorial_images or []:
            marker = str(image.get("marker", ""))
            if not marker or marker not in content:
                continue
            result = self._upload_local_image(image)
            if not result:
                content = content.replace(marker, "")
                continue
            source_url = result.get("source_url") or result.get("guid", {}).get("rendered", "")
            if not source_url:
                content = content.replace(marker, "")
                continue
            content = content.replace(marker, build_inline_image_html(image, source_url))
            uploaded.append({"id": result.get("id"), "file": image.get("file")})
        return content, uploaded

    def _upload_local_image(self, image: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload a curated local WebP file without downloading it from the web."""
        file_path = Path(str(image.get("path", "")))
        if not file_path.is_file():
            self.logger.warning(f"Editorial image missing: {file_path}")
            return None
        try:
            result = self.wp_client.upload_media(
                WordPressMediaData(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    mime_type="image/webp",
                    caption=str(image.get("caption", image.get("alt_text", ""))),
                    alt_text=str(image.get("alt_text", "")),
                    description=str(image.get("alt_text", "")),
                )
            )
            self.stats["media_uploads"] += 1
            return result
        except (WordPressAPIError, OSError) as error:
            self.logger.warning(f"Editorial image upload failed for {file_path.name}: {error}")
            return None

    def _validate_and_prepare_input(self, input_data: Any) -> List[WordPressPublishInput]:
        """验证和准备输入数据"""
        inputs = []

        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    # 期望包含 title 和 content
                    title = item.get("title", "")
                    content = item.get("content", "")

                    if title and content:
                        # 处理分类和标签
                        categories = item.get("categories", [])
                        if isinstance(categories, str):
                            categories = [cat.strip() for cat in categories.split(",") if cat.strip()]
                        elif not isinstance(categories, list):
                            categories = []

                        tags = item.get("tags", [])
                        if isinstance(tags, str):
                            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
                        elif not isinstance(tags, list):
                            tags = []

                        post_input = WordPressPublishInput(
                            title=str(title).strip(),
                            content=str(content).strip(),
                            keyword=item.get("keyword"),
                            excerpt=item.get("excerpt"),
                            slug=item.get("slug"),
                            categories=categories,
                            tags=tags,
                            featured_image_url=item.get("featured_image_url"),
                            featured_image_path=item.get("featured_image_path"),
                            editorial_images=item.get("editorial_images", []),
                            publish_status=item.get("publish_status", self.default_status),
                            schedule_date=item.get("schedule_date"),
                            author_id=item.get("author_id"),
                            meta=item.get("meta", {})
                        )
                        inputs.append(post_input)
                    else:
                        self.logger.warning(f"跳过缺少title或content的项: {item}")
                elif isinstance(item, WordPressPublishInput):
                    inputs.append(item)
                else:
                    self.logger.warning(f"跳过不支持的类型: {type(item)}")

        elif isinstance(input_data, dict):
            # 单个文章
            title = input_data.get("title", "")
            content = input_data.get("content", "")

            if title and content:
                post_input = WordPressPublishInput(
                    title=str(title).strip(),
                    content=str(content).strip(),
                    keyword=input_data.get("keyword"),
                    excerpt=input_data.get("excerpt"),
                    slug=input_data.get("slug"),
                    categories=input_data.get("categories", []),
                    tags=input_data.get("tags", []),
                    featured_image_url=input_data.get("featured_image_url"),
                    featured_image_path=input_data.get("featured_image_path"),
                    editorial_images=input_data.get("editorial_images", []),
                    publish_status=input_data.get("publish_status", self.default_status),
                    schedule_date=input_data.get("schedule_date"),
                    author_id=input_data.get("author_id"),
                    meta=input_data.get("meta", {})
                )
                inputs.append(post_input)

        elif isinstance(input_data, WordPressPublishInput):
            inputs.append(input_data)

        else:
            raise ValueError(f"不支持的输入数据类型: {type(input_data)}")

        if not inputs:
            raise ValueError("没有有效的文章数据")

        return inputs

    def _create_batches(self, items: List[Any]) -> List[List[Any]]:
        """创建处理批次"""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batches.append(items[i:i + self.batch_size])
        return batches

    def pre_execute(self, input_data: Any) -> Any:
        """执行前处理"""
        self.logger.debug("WordPress发布器执行前处理")

        # 重置统计信息
        self.stats = {
            "total_posts": 0,
            "posts_published": 0,
            "posts_failed": 0,
            "categories_created": 0,
            "tags_created": 0,
            "media_uploads": 0,
            "batches_processed": 0,
            "api_errors": 0,
            "total_time": 0.0,
        }

        # 初始化WordPress客户端
        self._initialize_client()

        # 测试连接
        if not self.wp_client.test_connection():
            raise ConnectionError("无法连接到WordPress站点")

        # 验证和准备输入
        prepared_inputs = self._validate_and_prepare_input(input_data)
        self.stats["total_posts"] = len(prepared_inputs)

        return prepared_inputs

    def execute_impl(self, input_data: Any) -> Any:
        """执行文章发布"""
        self.logger.info(f"开始发布 {len(input_data)} 篇文章到WordPress")

        all_results = []
        start_time = time.time()

        # 分批处理
        batches = self._create_batches(input_data)
        self.stats["batches_processed"] = len(batches)

        for batch_idx, batch in enumerate(batches):
            self.logger.info(f"处理批次 {batch_idx + 1}/{len(batches)}，包含 {len(batch)} 篇文章")

            batch_results = []
            for post_input in batch:
                result = self._process_single_post(post_input)
                batch_results.append(result)

            all_results.extend(batch_results)

            # 批次间延迟，避免API限制
            if batch_idx < len(batches) - 1:
                time.sleep(1)

        # 计算总时间
        total_time = time.time() - start_time
        self.stats["total_time"] = total_time

        # 统计总结
        success_count = sum(1 for r in all_results if r.error is None)
        failed_count = len(all_results) - success_count

        self.logger.info(
            f"文章发布完成",
            total_posts=len(all_results),
            success=success_count,
            failed=failed_count,
            total_time=total_time,
            categories_created=self.stats["categories_created"],
            tags_created=self.stats["tags_created"]
        )

        return all_results

    def post_execute(self, output_data: Any) -> Any:
        """执行后处理"""
        self.logger.debug("WordPress发布器执行后处理")

        # 可以在这里添加清理或后处理逻辑
        return output_data

    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        try:
            inputs = self._validate_and_prepare_input(input_data)
            return len(inputs) > 0
        except Exception as e:
            self.logger.error(f"输入数据验证失败: {e}")
            return False

    def validate_output(self, output_data: Any) -> bool:
        """验证输出数据"""
        if not isinstance(output_data, list):
            self.logger.warning(f"输出数据不是列表: {type(output_data)}")
            return False

        # 检查每个结果是否包含必需字段
        for result in output_data:
            if not hasattr(result, 'title') or not hasattr(result, 'status'):
                self.logger.warning(f"输出结果缺少必需字段: {result}")
                return False

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()

    # 便捷方法
    def publish_single_post(
        self,
        title: str,
        content: str,
        **kwargs
    ) -> WordPressPublishResult:
        """发布单篇文章"""
        post_input = WordPressPublishInput(title=title, content=content, **kwargs)
        results = self.execute([post_input])

        if results and hasattr(results, 'output_data') and results.output_data:
            return results.output_data[0]
        else:
            return WordPressPublishResult(
                post_id=0,
                title=title,
                status="failed",
                url="",
                error="执行失败"
            )
