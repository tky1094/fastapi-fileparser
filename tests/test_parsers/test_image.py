import pytest

from app.parsers.image import ImageParser
from tests.conftest import MockLLMService


@pytest.fixture
def mock_llm() -> MockLLMService:
    return MockLLMService()


@pytest.fixture
def parser(mock_llm: MockLLMService) -> ImageParser:
    return ImageParser(mock_llm)


async def test_parse_image(parser: ImageParser, mock_llm: MockLLMService) -> None:
    mock_llm._mock_describe_image.return_value = "テスト画像のテキスト"
    content = b"\x89PNG\r\n\x1a\n fake image data"

    result = await parser.parse(content, "image/png", "test.png")

    assert result.text == "テスト画像のテキスト"
    assert result.parser_used == "image"
    mock_llm._mock_describe_image.assert_called_once_with(content, "image/png")


async def test_supported_mimetypes(parser: ImageParser) -> None:
    mimes = parser.supported_mimetypes()
    assert "image/png" in mimes
    assert "image/jpeg" in mimes
    assert "image/webp" in mimes
