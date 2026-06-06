from unittest.mock import Mock, patch

import pytest

from src.modules.content_generator.ai_content_generator import AIContentGenerator


class TestAIContentGenerator:
    def test_validate_and_prepare_input_preserves_workflow_metadata(self):
        generator = AIContentGenerator("test-content-gen")

        result = generator._validate_and_prepare_input(
            [
                {
                    "keyword": "lighting hardware manufacturer",
                    "title": "Guide",
                    "lane": "pillar",
                    "priority": "A",
                    "cluster": "core",
                    "direction": "supplier comparison",
                    "internal_link_targets": "Home; Services",
                }
            ]
        )

        assert result[0]["lane"] == "pillar"
        assert result[0]["priority"] == "A"
        assert result[0]["cluster"] == "core"
        assert result[0]["direction"] == "supplier comparison"
        assert result[0]["internal_link_targets"] == "Home; Services"

    def test_generate_default_content_html(self):
        generator = AIContentGenerator("test-content-gen")
        content = generator._generate_default_content(
            "hardware",
            "Hardware Guide",
            lane="ordinary",
            priority="B",
            cluster="process",
        )

        assert "<article>" in content
        assert "<h1>Hardware Guide</h1>" in content
        assert "Priority: B" in content
        assert "Cluster: process" in content
        assert "What to Verify Before Ordering" in content
        assert "If your project involves finish, tolerance, or custom production questions" in content

    def test_get_cta_destination_prefers_service_targets_for_pillar(self):
        generator = AIContentGenerator("test-content-gen")

        destination = generator._get_cta_destination(
            "pillar", "Home; Services; Contact"
        )

        assert destination == "Services"

    def test_parse_ai_response_wraps_plain_text(self):
        generator = AIContentGenerator("test-content-gen")
        result = generator._parse_ai_response("Plain text content")

        assert "<article>" in result
        assert "Plain text content" in result

    def test_parse_ai_response_removes_ai_authored_internal_urls(self):
        generator = AIContentGenerator("test-content-gen")
        response = """
        {
          "title": "Test",
          "keyword": "hardware",
          "content": "<p>Read more on <a href=\\"https://yushengco.com/services/\\">our services</a> and visit /about-us for details.</p>",
          "slug": "test",
          "excerpt": "test excerpt"
        }
        """

        result = generator._parse_ai_response(
            response, internal_link_targets="Services; About Us"
        )

        assert 'href="https://yushengco.com/services/"' in result
        assert 'href="/about-us"' not in result
        assert "visit /about-us" not in result

    def test_parse_ai_response_links_existing_cta_target_names(self):
        generator = AIContentGenerator("test-content-gen")
        response = """
        {
          "title": "Test",
          "keyword": "hardware",
          "content": "<p>Body copy.</p><p>If you are comparing suppliers, the next practical step is to review Services, About Us, or Contact before placing an order.</p>",
          "slug": "test",
          "excerpt": "test excerpt"
        }
        """

        result = generator._parse_ai_response(
            response,
            internal_link_targets="Services; About Us; Contact",
            lane="pillar",
        )

        assert 'href="https://yushengco.com/services/"' in result
        assert 'href="https://yushengco.com/about-us/"' in result
        assert "review <a href=" in result

    def test_ensure_cta_section_appends_natural_cta(self):
        generator = AIContentGenerator("test-content-gen")
        content = "<article><p>Lane: pillar</p><p>Technical article body.</p></article>"

        result = generator._ensure_cta_section(
            content, internal_link_targets="Services; About Us; Contact"
        )

        assert "If you are comparing suppliers" in result
        assert 'href="https://yushengco.com/services/"' in result

    def test_apply_internal_links_uses_defaults(self):
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>Our factory provides floor lamp accessories, "
            "OEM customization, and a complete company profile.</p></article>"
        )

        linked = generator._apply_internal_links(content)

        assert 'href="https://yushengco.com/product-category/floor-lamp-sets/"' in linked
        assert 'href="https://yushengco.com/services/"' in linked
        assert 'href="https://yushengco.com/about-us/"' in linked
        assert 'href="https://yushengco.com/"' in linked

    def test_apply_internal_links_prefers_explicit_targets(self):
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>We support floor lamp accessories, OEM customization, "
            "and precision parts for project buyers.</p></article>"
        )

        linked = generator._apply_internal_links(
            content,
            internal_link_targets="Floor Lamp Sets; Services; Machined Parts",
        )

        assert 'href="https://yushengco.com/product-category/floor-lamp-sets/"' in linked
        assert 'href="https://yushengco.com/services/"' in linked
        assert 'href="https://yushengco.com/product-category/machined-parts/"' in linked

    @patch("src.modules.content_generator.ai_content_generator.get_ai_client")
    def test_generate_content_for_input(self, mock_get_ai_client):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = (
            "<article><h1>Test Article</h1><p>Test content about hardware.</p></article>"
        )
        mock_response.usage = {"total_tokens": 100}
        mock_response.cost = 0.01
        mock_client.chat_completion.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        generator = AIContentGenerator("test-content-gen")
        generator.prompt_template = {
            "system": "Test system prompt",
            "user": "Test user prompt",
            "parameters": {"temperature": 0.7, "max_tokens": 4000},
        }

        contents = generator._generate_content_for_input(
            "hardware",
            "Hardware Guide",
            lane="pillar",
            priority="A",
            cluster="core",
            direction="supplier comparison",
            internal_link_targets="Home; Services",
        )

        assert len(contents) == 1
        assert "<article>" in contents[0]
        assert generator.stats["ai_calls"] == 1
        assert generator.stats["total_tokens"] == 100
        assert generator.stats["total_cost"] == 0.01

    def test_validate_input_and_output(self):
        generator = AIContentGenerator("test-content-gen")

        assert generator.validate_input([{"keyword": "hardware", "title": "Guide"}]) is True
        assert generator.validate_input([]) is False
        assert generator.validate_output(["<article>Content</article>"]) is True
        assert generator.validate_output([""]) is False

    def test_invalid_input_raises(self):
        generator = AIContentGenerator("test-content-gen")

        with pytest.raises(ValueError):
            generator._validate_and_prepare_input(123)
