"""
WordPress API客户端测试
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from src.modules.wordpress_integration.wp_api_client import (
    WordPressClient,
    WordPressRESTClient,
    WordPressXMLRPCClient,
    WordPressPostData,
    WordPressMediaData,
    create_wordpress_client,
    get_wordpress_client,
    WordPressAPIError,
)


class TestWordPressClient:
    """WordPress客户端测试类"""

    def test_wordpress_post_data_creation(self):
        """测试WordPressPostData创建"""
        post_data = WordPressPostData(
            title="Test Post",
            content="This is test content",
            excerpt="Test excerpt",
            status="draft",
            categories=[1, 2],
            tags=[3, 4],
            featured_media=5,
            author=1
        )

        assert post_data.title == "Test Post"
        assert post_data.content == "This is test content"
        assert post_data.excerpt == "Test excerpt"
        assert post_data.status == "draft"
        assert post_data.categories == [1, 2]
        assert post_data.tags == [3, 4]
        assert post_data.featured_media == 5
        assert post_data.author == 1

    def test_wordpress_media_data_creation(self):
        """测试WordPressMediaData创建"""
        media_data = WordPressMediaData(
            file_path="/path/to/image.jpg",
            file_name="image.jpg",
            mime_type="image/jpeg",
            caption="Test caption",
            alt_text="Test alt text",
            description="Test description"
        )

        assert media_data.file_path == "/path/to/image.jpg"
        assert media_data.file_name == "image.jpg"
        assert media_data.mime_type == "image/jpeg"
        assert media_data.caption == "Test caption"
        assert media_data.alt_text == "Test alt text"
        assert media_data.description == "Test description"

    @patch('src.modules.wordpress_integration.wp_api_client.config_manager')
    def test_get_wordpress_client_with_config(self, mock_config_manager):
        """测试通过配置获取WordPress客户端"""
        # 模拟配置
        mock_wp_config = Mock()
        mock_wp_config.WORDPRESS_URL = "https://test.com"
        mock_wp_config.WORDPRESS_USERNAME = "admin"
        mock_wp_config.WORDPRESS_APPLICATION_PASSWORD = "app_password"
        mock_wp_config.WORDPRESS_PASSWORD = "password"
        mock_wp_config.VERIFY_SSL = True
        mock_wp_config.TIMEOUT = 30
        mock_config_manager.get_wordpress_config.return_value = mock_wp_config

        # 模拟客户端创建
        with patch('src.modules.wordpress_integration.wp_api_client.WordPressRESTClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = get_wordpress_client(api_type="rest", use_config=True)

            # 验证配置管理器被调用
            mock_config_manager.get_wordpress_config.assert_called_once()

            # 验证客户端使用正确的参数创建
            mock_client_class.assert_called_once_with(
                base_url="https://test.com",
                username="admin",
                password="app_password",
                use_application_password=True,
                verify_ssl=True,
                timeout=30
            )

            assert client == mock_client

    def test_create_wordpress_client_rest(self):
        """测试创建REST客户端"""
        with patch('src.modules.wordpress_integration.wp_api_client.WordPressRESTClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = create_wordpress_client(
                api_type="rest",
                base_url="https://test.com",
                username="admin",
                password="password"
            )

            mock_client_class.assert_called_once_with(
                base_url="https://test.com",
                username="admin",
                password="password",
                use_application_password=True,
                verify_ssl=True,
                timeout=30
            )
            assert client == mock_client

    def test_create_wordpress_client_invalid_type(self):
        """测试创建无效类型的客户端"""
        with pytest.raises(ValueError, match="不支持的API类型"):
            create_wordpress_client(api_type="invalid")


class TestWordPressRESTClient:
    """WordPress REST客户端测试类"""

    def setup_method(self):
        """测试设置"""
        self.client = WordPressRESTClient(
            base_url="https://test.com",
            username="admin",
            password="password"
        )

        # 模拟session
        self.client.session = Mock()
        self.client.logger = Mock()

    def test_test_connection_success(self):
        """测试连接成功"""
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.raise_for_status.return_value = None
        self.client.session.get.return_value = mock_response

        result = self.client.test_connection()

        assert result is True
        self.client.session.get.assert_called_once()
        self.client.logger.info.assert_called()

    def test_test_connection_failure(self):
        """测试连接失败"""
        self.client.session.get.side_effect = Exception("Connection failed")

        result = self.client.test_connection()

        assert result is False
        self.client.logger.error.assert_called()

    def test_create_post_success(self):
        """测试创建文章成功"""
        # 准备测试数据
        post_data = WordPressPostData(
            title="Test Post",
            content="Test content",
            status="draft",
            categories=[1],
            tags=[2]
        )

        # 模拟响应
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 123,
            "title": {"rendered": "Test Post"},
            "link": "https://test.com/test-post"
        }
        self.client.session.post.return_value = mock_response

        result = self.client.create_post(post_data)

        # 验证调用
        self.client.session.post.assert_called_once()
        call_args = self.client.session.post.call_args
        assert call_args[0][0] == "https://test.com/wp-json/wp/v2/posts"

        # 验证结果
        assert result["id"] == 123
        assert result["title"]["rendered"] == "Test Post"
        self.client.logger.info.assert_called()

    def test_create_post_api_error(self):
        """测试创建文章API错误"""
        post_data = WordPressPostData(
            title="Test Post",
            content="Test content"
        )

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        self.client.session.post.return_value = mock_response

        with pytest.raises(WordPressAPIError, match="认证失败"):
            self.client.create_post(post_data)

    def test_get_categories_success(self):
        """测试获取分类成功"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": 1,
                "name": "Category 1",
                "slug": "category-1",
                "description": "Test category 1",
                "count": 5,
                "parent": 0
            },
            {
                "id": 2,
                "name": "Category 2",
                "slug": "category-2",
                "description": "Test category 2",
                "count": 3,
                "parent": 1
            }
        ]
        mock_response.raise_for_status.return_value = None
        self.client.session.get.return_value = mock_response

        categories = self.client.get_categories()

        assert len(categories) == 2
        assert categories[0].id == 1
        assert categories[0].name == "Category 1"
        assert categories[1].id == 2
        assert categories[1].name == "Category 2"

    def test_create_category_success(self):
        """测试创建分类成功"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 10,
            "name": "New Category",
            "slug": "new-category",
            "description": "New category description",
            "count": 0,
            "parent": 0
        }
        mock_response.raise_for_status.return_value = None
        self.client.session.post.return_value = mock_response

        category = self.client.create_category("New Category", description="New category description")

        assert category.id == 10
        assert category.name == "New Category"
        assert category.slug == "new-category"
        self.client.logger.info.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])