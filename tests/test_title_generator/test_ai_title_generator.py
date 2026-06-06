from unittest.mock import Mock, patch

import pytest

from src.modules.title_generator.ai_title_generator import AITitleGenerator


class TestAITitleGenerator:
    def test_validate_and_prepare_input_supports_strings(self):
        generator = AITitleGenerator("test-title-gen")

        result = generator._validate_and_prepare_input(
            "hardware, lamp holder, lighting accessories"
        )

        assert len(result) == 3
        assert result[0]["keyword"] == "hardware"
        assert result[1]["keyword"] == "lamp holder"
        assert result[2]["keyword"] == "lighting accessories"

    def test_validate_and_prepare_input_preserves_metadata(self):
        generator = AITitleGenerator("test-title-gen")

        result = generator._validate_and_prepare_input(
            [
                {
                    "keyword": "lighting hardware manufacturer",
                    "direction": "supplier comparison",
                    "lane": "pillar",
                    "priority": "A",
                    "cluster": "core",
                }
            ]
        )

        assert result[0]["direction"] == "supplier comparison"
        assert result[0]["lane"] == "pillar"
        assert result[0]["priority"] == "A"
        assert result[0]["cluster"] == "core"

    def test_create_batches(self):
        generator = AITitleGenerator("test-title-gen", {"batch_size": 3})
        keywords = [{"keyword": f"kw{i}"} for i in range(5)]

        batches = generator._create_batches(keywords)

        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    def test_generate_default_title(self):
        generator = AITitleGenerator("test-title-gen")

        assert (
            generator._generate_default_title("hardware")
            == "Practical Guide to hardware"
        )
        assert (
            generator._generate_default_title(
                "hardware",
                "supplier comparison",
                lane="pillar",
                priority="A",
            )
            == "How to Evaluate hardware: supplier comparison"
        )

    def test_parse_ai_response(self):
        generator = AITitleGenerator("test-title-gen")

        result = generator._parse_ai_response(
            '```json\n["Complete Guide to Hardware", "Hardware Solutions Guide"]\n```'
        )

        assert result == ["Complete Guide to Hardware", "Hardware Solutions Guide"]

    @patch("src.modules.title_generator.ai_title_generator.get_ai_client")
    def test_generate_titles_for_keyword(self, mock_get_ai_client):
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = '["Complete Guide to Hardware", "Hardware Solutions"]'
        mock_response.usage = {"total_tokens": 50}
        mock_response.cost = 0.005
        mock_client.chat_completion.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        generator = AITitleGenerator("test-title-gen")
        generator.prompt_template = {
            "system": "Test system prompt",
            "user": "Test user prompt",
            "parameters": {"temperature": 0.7, "max_tokens": 500},
        }

        titles = generator._generate_titles_for_keyword(
            "hardware",
            direction="supplier comparison",
            lane="pillar",
            priority="A",
            cluster="core",
        )

        assert titles == ["Complete Guide to Hardware"]
        assert generator.stats["ai_calls"] == 1
        assert generator.stats["total_tokens"] == 50
        assert generator.stats["total_cost"] == 0.005

    def test_validate_input_and_output(self):
        generator = AITitleGenerator("test-title-gen")

        assert generator.validate_input(["hardware", "lamp holder"]) is True
        assert generator.validate_input([]) is False
        assert generator.validate_output(["Title 1", "Title 2"]) is True
        assert generator.validate_output(["Title 1", ""]) is False

    def test_invalid_input_raises(self):
        generator = AITitleGenerator("test-title-gen")

        with pytest.raises(ValueError):
            generator._validate_and_prepare_input(123)
