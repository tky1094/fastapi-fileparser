from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import router
from app.config import LLMProvider, Settings
from app.parsers.docx import DocxParser
from app.parsers.image import ImageParser
from app.parsers.pdf import PdfParser
from app.parsers.text import TextParser
from app.services.llm import BaseLLMService
from app.services.llm_anthropic import AnthropicLLMService
from app.services.llm_openai import OpenAILLMService
from app.services.parser_registry import ParserRegistry


def create_llm_service(settings: Settings) -> BaseLLMService:
    if settings.llm_provider == LLMProvider.ANTHROPIC:
        return AnthropicLLMService(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    elif settings.llm_provider == LLMProvider.OPENAI:
        return OpenAILLMService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    elif settings.llm_provider == LLMProvider.OLLAMA:
        return OpenAILLMService(
            api_key="ollama",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
    elif settings.llm_provider == LLMProvider.VLLM:
        return OpenAILLMService(
            api_key="vllm",
            model=settings.vllm_model,
            base_url=settings.vllm_base_url,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = Settings()
    llm_service = create_llm_service(settings)

    registry = ParserRegistry()
    registry.register(TextParser())
    registry.register(ImageParser(llm_service))
    registry.register(PdfParser(llm_service))
    registry.register(DocxParser())

    app.state.settings = settings
    app.state.parser_registry = registry

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="File Text Parser API",
        description="LLM-powered file text parser",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
