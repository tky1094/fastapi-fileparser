from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.parsers.docx import DocxParser
from app.parsers.image import ImageParser
from app.parsers.pdf import PdfParser
from app.parsers.text import TextParser
from app.services.llm import BaseLLMService
from app.services.parser_registry import ParserRegistry


class MockLLMService(BaseLLMService):
    def __init__(self) -> None:
        self._mock_describe_image = AsyncMock(return_value="Mock LLM response: extracted text")

    async def describe_image(self, image_bytes: bytes, media_type: str) -> str:
        return await self._mock_describe_image(image_bytes, media_type)


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    return MockLLMService()


@pytest.fixture
def app(mock_llm_service: MockLLMService):
    application = create_app()

    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        anthropic_model="test-model",
    )

    registry = ParserRegistry()
    registry.register(TextParser())
    registry.register(ImageParser(mock_llm_service))
    registry.register(PdfParser(mock_llm_service))
    registry.register(DocxParser())

    application.state.settings = settings
    application.state.parser_registry = registry

    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
