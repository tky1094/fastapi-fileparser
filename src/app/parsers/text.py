from charset_normalizer import from_bytes

from app.parsers.base import BaseParser, ParseResult, ProgressCallback


class TextParser(BaseParser):
    def supported_mimetypes(self) -> set[str]:
        return {
            "text/plain",
            "text/csv",
            "text/html",
            "text/markdown",
            "text/xml",
            "text/css",
            "text/javascript",
            "application/json",
            "application/xml",
        }

    async def parse(
        self,
        content: bytes,
        mime_type: str,
        filename: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ParseResult:
        await self._notify(progress_callback, "parsing", "文字コード検出中...")

        result = from_bytes(content).best()

        if result is None:
            return ParseResult(
                text=content.decode("utf-8", errors="replace"),
                content_type=mime_type,
                parser_used="text",
                metadata={"detected_encoding": "unknown", "confidence": "0"},
            )

        detected_encoding = result.encoding
        confidence = f"{result.coherence:.2f}"
        text = str(result)

        await self._notify(
            progress_callback,
            "parsing",
            f"文字コード検出完了: {detected_encoding} (confidence: {confidence})",
        )

        return ParseResult(
            text=text,
            content_type=mime_type,
            parser_used="text",
            metadata={
                "detected_encoding": detected_encoding,
                "confidence": confidence,
            },
        )
