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
        # 配置管理器暴露的是 wordpress_config 属性（lowercase 字段）。
        # 以前这里 mock 的是 get_wordpress_config() 和大写字段，
        # 但实现里根本没有那个方法 —— 断言一个永远不成立的调用。
        mock_wp_config = Mock()
        mock_wp_config.url = "https://test.com"
        mock_wp_config.username = "admin"
        mock_wp_config.application_password = "app_password"
        mock_wp_config.password = "password"
        mock_wp_config.verify_ssl = True
        mock_wp_config.timeout = 30
        mock_config_manager.wordpress_config = mock_wp_config

        # 模拟客户端创建
        with patch('src.modules.wordpress_integration.wp_api_client.WordPressRESTClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            client = get_wordpress_client(api_type="rest", use_config=True)

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

    # --- 媒体库读取（只读，供 linker 使用）---

    def _media_response(self, items, total_pages=1, total=None):
        response = Mock()
        response.status_code = 200
        response.json.return_value = items
        response.headers = {
            "X-WP-Total": str(total if total is not None else len(items)),
            "X-WP-TotalPages": str(total_pages),
        }
        return response

    def test_list_media_paginates_until_the_last_page(self):
        """分页必须靠 X-WP-TotalPages 走完，否则大库只拿到第一页。"""
        self.client.session.get.side_effect = [
            self._media_response([{"id": 1}, {"id": 2}], total_pages=2, total=3),
            self._media_response([{"id": 3}], total_pages=2, total=3),
        ]

        items = self.client.list_media(per_page=2)

        assert [item["id"] for item in items] == [1, 2, 3]
        assert self.client.session.get.call_count == 2
        # 只读：全程 GET，并且显式限定只取图片
        assert self.client.session.get.call_args.kwargs["params"]["media_type"] == "image"

    def test_list_media_stops_on_out_of_range_page(self):
        """WP 在页码越界时返回 400 rest_post_invalid_page_number，不是错误。"""
        overflow = Mock()
        overflow.status_code = 400
        overflow.json.return_value = {"code": "rest_post_invalid_page_number"}
        self.client.session.get.side_effect = [
            self._media_response([{"id": 1}], total_pages=99, total=1),
            overflow,
        ]

        items = self.client.list_media(per_page=1)

        assert [item["id"] for item in items] == [1]

    def test_list_media_raises_on_a_real_api_error(self):
        failure = Mock()
        failure.status_code = 403
        failure.json.return_value = {"code": "rest_forbidden", "message": "nope"}
        self.client.session.get.return_value = failure

        with pytest.raises(WordPressAPIError):
            self.client.list_media()

    def test_count_media_reads_the_total_header_without_downloading_items(self):
        self.client.session.get.return_value = self._media_response([], total=1391)

        assert self.client.count_media() == 1391
        assert self.client.session.get.call_args.kwargs["params"]["per_page"] == 1

    def test_get_media_by_id(self):
        self.client.session.get.return_value = self._media_response(
            {"id": 15621, "source_url": "https://test.com/factory-08.webp"}
        )

        media = self.client.get_media(15621)

        assert media["id"] == 15621
        assert self.client.session.get.call_args.args[0].endswith("/media/15621")

    def test_base_client_media_methods_are_not_silently_unimplemented(self):
        """XML-RPC 没有读媒体的接口，必须显式报错而不是返回空列表。"""
        client = WordPressClient("https://test.com", "admin", "password")

        with pytest.raises(NotImplementedError):
            client.list_media()
        with pytest.raises(NotImplementedError):
            client.get_media(1)
        with pytest.raises(NotImplementedError):
            client.count_media()


if __name__ == "__main__":
    pytest.main([__file__])