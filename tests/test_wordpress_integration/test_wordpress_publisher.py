"""
WordPress发布器测试
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from src.modules.wordpress_integration.wordpress_publisher import (
    WordPressPublisher,
    WordPressPublishInput,
    WordPressPublishResult,
)


class TestWordPressPublisher:
    """WordPress发布器测试类"""

    def setup_method(self):
        """测试设置"""
        self.config = {
            "batch_size": 2,
            "api_type": "rest",
            "default_status": "draft",
            "default_category_id": 1,
            "auto_create_categories": False,
            "auto_create_tags": False,
            "enable_media_upload": False,
        }

        self.publisher = WordPressPublisher("test-publisher", self.config)
        self.publisher.logger = Mock()

    def test_initialization(self):
        """测试初始化"""
        assert self.publisher.node_id == "test-publisher"
        assert self.publisher.node_type == "wordpress_publisher"
        assert self.publisher.batch_size == 2
        assert self.publisher.api_type == "rest"
        assert self.publisher.default_status == "draft"
        assert self.publisher.default_category_id == 1
        assert self.publisher.auto_create_categories is False
        assert self.publisher.auto_create_tags is False

    def test_wordpress_publish_input_creation(self):
        """测试WordPressPublishInput创建"""
        publish_input = WordPressPublishInput(
            title="Test Post",
            content="Test content",
            keyword="test",
            excerpt="Test excerpt",
            categories=["Category 1", "Category 2"],
            tags=["Tag 1", "Tag 2"],
            featured_image_url="https://example.com/image.jpg",
            publish_status="draft",
            author_id=1
        )

        assert publish_input.title == "Test Post"
        assert publish_input.content == "Test content"
        assert publish_input.keyword == "test"
        assert publish_input.excerpt == "Test excerpt"
        assert publish_input.categories == ["Category 1", "Category 2"]
        assert publish_input.tags == ["Tag 1", "Tag 2"]
        assert publish_input.featured_image_url == "https://example.com/image.jpg"
        assert publish_input.publish_status == "draft"
        assert publish_input.author_id == 1

    def test_uploads_local_editorial_images_and_sets_featured_media(self, tmp_path):
        image_path = tmp_path / "floor-lamp.webp"
        image_path.write_bytes(b"webp")
        self.publisher.enable_media_upload = True
        self.publisher.wp_client = Mock()
        self.publisher.wp_client.upload_media.side_effect = [
            {"id": 501, "source_url": "https://example.com/floor-lamp.webp"},
            {"id": 502, "source_url": "https://example.com/qc.webp"},
        ]
        self.publisher.wp_client.create_post.return_value = {
            "id": 100, "link": "https://example.com/post", "date": "2026-01-01"
        }
        marker = "<!-- editorial-image:factory/qc.webp -->"
        post = WordPressPublishInput(
            title="Floor Lamp Guide",
            content=f"<article><h2>Quality Control</h2>{marker}</article>",
            featured_image_path=str(image_path),
            editorial_images=[
                {
                    "file": "factory/qc.webp",
                    "path": str(image_path),
                    "marker": marker,
                    "alt_text": "Factory quality inspection",
                    "width": 900,
                    "height": 700,
                }
            ],
        )

        result = self.publisher._process_single_post(post)

        wp_post = self.publisher.wp_client.create_post.call_args.args[0]
        assert result.metadata["featured_media"] == 502
        assert result.metadata["editorial_media"] == [{"id": 501, "file": "factory/qc.webp"}]
        assert wp_post.featured_media == 502
        assert marker not in wp_post.content
        assert 'loading="lazy"' in wp_post.content
        assert 'width="900" height="700"' in wp_post.content

    def test_wordpress_publish_result_creation(self):
        """测试WordPressPublishResult创建"""
        result = WordPressPublishResult(
            post_id=123,
            title="Test Post",
            status="published",
            url="https://test.com/test-post",
            published_at="2024-01-01T12:00:00",
            metadata={"wordpress_id": 123}
        )

        assert result.post_id == 123
        assert result.title == "Test Post"
        assert result.status == "published"
        assert result.url == "https://test.com/test-post"
        assert result.published_at == "2024-01-01T12:00:00"
        assert result.metadata == {"wordpress_id": 123}

    def test_validate_and_prepare_input_with_dict_list(self):
        """测试验证和准备字典列表输入"""
        input_data = [
            {
                "title": "Post 1",
                "content": "Content 1",
                "keyword": "kw1",
                "categories": ["Cat1", "Cat2"],
                "tags": ["Tag1", "Tag2"]
            },
            {
                "title": "Post 2",
                "content": "Content 2",
                "keyword": "kw2",
                "categories": "Cat3,Cat4",
                "tags": "Tag3,Tag4"
            }
        ]

        inputs = self.publisher._validate_and_prepare_input(input_data)

        assert len(inputs) == 2
        assert isinstance(inputs[0], WordPressPublishInput)
        assert inputs[0].title == "Post 1"
        assert inputs[0].content == "Content 1"
        assert inputs[0].keyword == "kw1"
        assert inputs[0].categories == ["Cat1", "Cat2"]
        assert inputs[0].tags == ["Tag1", "Tag2"]

        # 测试字符串转换为列表
        assert inputs[1].categories == ["Cat3", "Cat4"]
        assert inputs[1].tags == ["Tag3", "Tag4"]

    def test_validate_and_prepare_input_with_single_dict(self):
        """测试验证和准备单个字典输入"""
        input_data = {
            "title": "Single Post",
            "content": "Single content",
            "keyword": "single"
        }

        inputs = self.publisher._validate_and_prepare_input(input_data)

        assert len(inputs) == 1
        assert inputs[0].title == "Single Post"
        assert inputs[0].content == "Single content"
        assert inputs[0].keyword == "single"

    def test_validate_and_prepare_input_invalid_data(self):
        """测试无效输入数据"""
        # 缺少title或content
        input_data = [
            {"title": "No content"},
            {"content": "No title"}
        ]

        with pytest.raises(ValueError, match="没有有效的文章数据"):
            self.publisher._validate_and_prepare_input(input_data)

    def test_create_batches(self):
        """测试创建批次"""
        items = [1, 2, 3, 4, 5]
        self.publisher.batch_size = 2

        batches = self.publisher._create_batches(items)

        assert len(batches) == 3
        assert batches[0] == [1, 2]
        assert batches[1] == [3, 4]
        assert batches[2] == [5]

    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_initialize_client(self, mock_get_client):
        """测试初始化客户端"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        self.publisher._initialize_client()

        mock_get_client.assert_called_once_with(api_type="rest")
        assert self.publisher.wp_client == mock_client
        self.publisher.logger.debug.assert_called_with("WordPress客户端初始化成功")

    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_pre_execute_success(self, mock_get_client):
        """测试执行前处理成功"""
        # 模拟客户端
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_get_client.return_value = mock_client

        input_data = [
            {
                "title": "Test Post",
                "content": "Test content",
                "keyword": "test"
            }
        ]

        result = self.publisher.pre_execute(input_data)

        # 验证客户端初始化
        mock_get_client.assert_called_once()
        mock_client.test_connection.assert_called_once()

        # 验证结果
        assert len(result) == 1
        assert result[0].title == "Test Post"
        assert result[0].content == "Test content"

        # 验证统计信息重置
        assert self.publisher.stats["total_posts"] == 1

    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_pre_execute_connection_failed(self, mock_get_client):
        """测试执行前处理连接失败"""
        mock_client = Mock()
        mock_client.test_connection.return_value = False
        mock_get_client.return_value = mock_client

        input_data = [{"title": "Test", "content": "Content"}]

        with pytest.raises(ConnectionError, match="无法连接到WordPress站点"):
            self.publisher.pre_execute(input_data)

    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_process_single_post_success(self, mock_get_client):
        """测试处理单篇文章成功"""
        # 模拟客户端
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # 模拟分类获取
        mock_client.get_categories.return_value = []
        mock_client.get_tags.return_value = []

        # 模拟文章创建
        mock_client.create_post.return_value = {
            "id": 123,
            "link": "https://test.com/test-post",
            "date": "2024-01-01T12:00:00"
        }

        self.publisher.wp_client = mock_client

        publish_input = WordPressPublishInput(
            title="Test Post",
            content="Test content",
            categories=["Category 1"],
            tags=["Tag 1"]
        )

        result = self.publisher._process_single_post(publish_input)

        # 验证结果
        assert result.post_id == 123
        assert result.title == "Test Post"
        assert result.status == "draft"  # 使用默认状态
        assert result.url == "https://test.com/test-post"
        assert result.error is None

        # 验证统计信息更新
        assert self.publisher.stats["posts_published"] == 1

    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_process_single_post_failure(self, mock_get_client):
        """测试处理单篇文章失败"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # 模拟API错误
        from src.modules.wordpress_integration.wp_api_client import WordPressAPIError
        mock_client.create_post.side_effect = WordPressAPIError("API Error")

        self.publisher.wp_client = mock_client

        publish_input = WordPressPublishInput(
            title="Test Post",
            content="Test content"
        )

        result = self.publisher._process_single_post(publish_input)

        # 验证失败结果
        assert result.post_id == 0
        assert result.status == "failed"
        assert result.error == "API Error"
        assert self.publisher.stats["posts_failed"] == 1
        assert self.publisher.stats["api_errors"] == 1


    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_process_single_post_future_schedule(self, mock_get_client):
        """Scheduled posts should be created as future posts with a publish date."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_categories.return_value = []
        mock_client.get_tags.return_value = []
        mock_client.create_post.return_value = {
            "id": 456,
            "link": "https://test.com/scheduled-post",
            "date": "2026-05-11T17:00:00"
        }

        self.publisher.wp_client = mock_client

        publish_input = WordPressPublishInput(
            title="Scheduled Post",
            content="Scheduled content",
            publish_status="future",
            schedule_date="2026-05-11T17:00:00+00:00"
        )

        result = self.publisher._process_single_post(publish_input)

        assert result.post_id == 456
        assert result.status == "future"

        create_post_input = mock_client.create_post.call_args[0][0]
        assert create_post_input.status == "future"
        assert create_post_input.date == "2026-05-11T17:00:00+00:00"

    def test_validate_input_success(self):
        """测试输入验证成功"""
        input_data = [
            {"title": "Post 1", "content": "Content 1"},
            {"title": "Post 2", "content": "Content 2"}
        ]

        result = self.publisher.validate_input(input_data)

        assert result is True

    def test_validate_input_failure(self):
        """测试输入验证失败"""
        # 无效输入
        input_data = []

        result = self.publisher.validate_input(input_data)

        assert result is False
        self.publisher.logger.error.assert_called()

    def test_validate_output_success(self):
        """测试输出验证成功"""
        output_data = [
            WordPressPublishResult(
                post_id=1,
                title="Post 1",
                status="published",
                url="https://test.com/post-1"
            ),
            WordPressPublishResult(
                post_id=2,
                title="Post 2",
                status="draft",
                url="https://test.com/post-2"
            )
        ]

        result = self.publisher.validate_output(output_data)

        assert result is True

    def test_validate_output_failure(self):
        """测试输出验证失败"""
        # 无效输出（不是列表）
        output_data = "not a list"

        result = self.publisher.validate_output(output_data)

        assert result is False
        self.publisher.logger.warning.assert_called()

    def test_get_statistics(self):
        """测试获取统计信息"""
        # 设置一些统计值
        self.publisher.stats["posts_published"] = 5
        self.publisher.stats["posts_failed"] = 2

        stats = self.publisher.get_statistics()

        assert stats["posts_published"] == 5
        assert stats["posts_failed"] == 2
        assert "total_posts" in stats
        assert "total_time" in stats

    @patch('src.modules.wordpress_integration.wordpress_publisher.WordPressPublisher._process_single_post')
    @patch('src.modules.wordpress_integration.wordpress_publisher.get_wordpress_client')
    def test_execute_impl_success(self, mock_get_client, mock_process_single_post):
        """测试执行实现成功"""
        # 模拟客户端
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_get_client.return_value = mock_client

        # 模拟输入数据
        input_data = [
            WordPressPublishInput(title="Post 1", content="Content 1"),
            WordPressPublishInput(title="Post 2", content="Content 2"),
            WordPressPublishInput(title="Post 3", content="Content 3")
        ]

        # 设置批量大小为2
        self.publisher.batch_size = 2

        # 模拟处理结果
        mock_process_single_post.side_effect = [
            WordPressPublishResult(post_id=1, title="Post 1", status="published", url=""),
            WordPressPublishResult(post_id=2, title="Post 2", status="published", url=""),
            WordPressPublishResult(post_id=3, title="Post 3", status="published", url="")
        ]

        # 调用执行方法
        results = self.publisher.execute_impl(input_data)

        # 验证结果
        assert len(results) == 3
        assert results[0].post_id == 1
        assert results[1].post_id == 2
        assert results[2].post_id == 3

        # 验证批次处理
        assert self.publisher.stats["batches_processed"] == 2  # 3个文章，批量大小2 = 2个批次

        # 验证_process_single_post被调用3次
        assert mock_process_single_post.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__])
