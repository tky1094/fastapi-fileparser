from app.parsers.base import BaseParser, ParseResult, ProgressCallback
from app.services.llm import BaseLLMService


class ImageParser(BaseParser):
    def __init__(self, llm_service: BaseLLMService) -> None:
        self._llm = llm_service

    def supported_mimetypes(self) -> set[str]:
        return {
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "image/tiff",
        }

    async def parse(
        self,
        content: bytes,
        mime_type: str,
        filename: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ParseResult:
        await self._notify(progress_callback, "llm_processing", "LLMで画像解析中...")

        text = await self._llm.describe_image(content, mime_type)

        await self._notify(progress_callback, "llm_complete", "LLM画像解析完了")

        return ParseResult(
            text=text,
            content_type=mime_type,
            parser_used="image",
            metadata={"filename": filename},
        )
