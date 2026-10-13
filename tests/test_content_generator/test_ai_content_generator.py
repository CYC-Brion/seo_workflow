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

    def test_every_declared_target_has_matchable_phrases(self):
        """每个工作簿能写的目标名，都必须解析出非空短语表。

        回归背景：Contact 在 target_map 里有 URL，但规则表里没有对应条目。
        resolve_internal_link_targets() 拿到空 phrases，
        _replace_first_internal_link() 见空列表直接返回，于是「工作簿里填了 Contact、
        文章里一个 Contact 链接都没有」，而且不报错、不告警。
        """
        from config.internal_links_config import (
            get_internal_link_target_map,
            resolve_internal_link_targets,
        )

        for normalized_name in get_internal_link_target_map():
            rules = resolve_internal_link_targets(normalized_name)
            assert rules, f"{normalized_name} 无法解析出规则"
            assert rules[0]["phrases"], f"{normalized_name} 解析出的短语表为空"

    def test_apply_internal_links_links_the_literal_service_word(self):
        """结语常写 "review our Services"，短语表里必须有 services 本身。"""
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>Before placing an order, review our Services against your "
            "required processes.</p></article>"
        )

        linked = generator._apply_internal_links(
            content, internal_link_targets="Home; About Us; Services; Contact"
        )

        assert 'href="https://yushengco.com/services/"' in linked

    def test_apply_internal_links_makes_contact_reachable(self):
        generator = AIContentGenerator("test-content-gen")
        content = "<article><p>Contact us before finalizing drawings.</p></article>"

        linked = generator._apply_internal_links(
            content, internal_link_targets="Home; About Us; Services; Contact"
        )

        assert 'href="https://yushengco.com/contact-us/"' in linked

    def test_home_rule_does_not_steal_generic_anchors(self):
        """裸词 supplier / manufacturer 不该被首页规则吃掉。"""
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>Comparing suppliers and manufacturers is the first step "
            "in a sourcing program.</p></article>"
        )

        linked = generator._apply_internal_links(
            content, internal_link_targets="Home; Services"
        )

        assert "suppliers</a>" not in linked
        assert "manufacturers</a>" not in linked

    def test_service_life_is_not_linked_to_the_services_page(self):
        """service life / service temperature 是技术参数，不是服务介绍。"""
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>The gasket is rated for a 50,000 hour service life at "
            "rated service temperature.</p></article>"
        )

        linked = generator._apply_internal_links(
            content, internal_link_targets="Home; Services"
        )

        assert "service life</a>" not in linked
        assert "service temperature</a>" not in linked

    def test_link_cta_targets_handles_a_natural_sentence(self):
        """结语不照抄模板句式时也要能挂上 CTA 目标链接。"""
        generator = AIContentGenerator("test-content-gen")
        content = (
            "<article><p>Body paragraph.</p>"
            "<p>Before placing an order, review our Services against your required "
            "processes.</p></article>"
        )

        result = generator._link_cta_targets(
            content, lane="pillar", internal_link_targets="Home; Services; Contact"
        )

        assert 'href="https://yushengco.com/services/"' in result
        assert ">Services</a>" in result

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
