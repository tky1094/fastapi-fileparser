from app.config import LLMProvider, Settings
from app.main import create_llm_service
from app.services.llm_anthropic import AnthropicLLMService
from app.services.llm_openai import OpenAILLMService


def test_create_anthropic_service() -> None:
    settings = Settings(
        llm_provider=LLMProvider.ANTHROPIC,
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-4-20250514",
    )
    service = create_llm_service(settings)
    assert isinstance(service, AnthropicLLMService)


def test_create_openai_service() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        openai_api_key="test-key",
        openai_model="gpt-4o",
    )
    service = create_llm_service(settings)
    assert isinstance(service, OpenAILLMService)


def test_create_ollama_service() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OLLAMA,
        ollama_base_url="http://localhost:11434/v1",
        ollama_model="llava",
    )
    service = create_llm_service(settings)
    assert isinstance(service, OpenAILLMService)
    assert str(service._client.base_url) == "http://localhost:11434/v1/"


def test_create_vllm_service() -> None:
    settings = Settings(
        llm_provider=LLMProvider.VLLM,
        vllm_base_url="http://localhost:8000/v1",
        vllm_model="llava-hf/llava-1.5-7b-hf",
    )
    service = create_llm_service(settings)
    assert isinstance(service, OpenAILLMService)
    assert str(service._client.base_url) == "http://localhost:8000/v1/"


def test_openai_service_default_base_url() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        openai_api_key="test-key",
        openai_model="gpt-4o",
    )
    service = create_llm_service(settings)
    assert isinstance(service, OpenAILLMService)
    # Default OpenAI base URL
    assert "api.openai.com" in str(service._client.base_url)
