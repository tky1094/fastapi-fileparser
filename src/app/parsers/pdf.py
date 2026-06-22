import asyncio
import io

import pypdfium2 as pdfium
from PIL import Image

from app.parsers.base import BaseParser, ParseResult, ProgressCallback
from app.services.llm import BaseLLMService

SCANNED_PDF_TEXT_THRESHOLD = 50
DEFAULT_MAX_CONCURRENCY = 3


class PdfParser(BaseParser):
    def __init__(
        self, llm_service: BaseLLMService, max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    ) -> None:
        self._llm = llm_service
        self._max_concurrency = max_concurrency

    def supported_mimetypes(self) -> set[str]:
        return {"application/pdf"}

    async def parse(
        self,
        content: bytes,
        mime_type: str,
        filename: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ParseResult:
        await self._notify(progress_callback, "parsing", "PDFを解析中...")

        pdf = pdfium.PdfDocument(content)
        page_count = len(pdf)

        # First attempt: text extraction
        texts: list[str] = []
        for i in range(page_count):
            await self._notify(
                progress_callback,
                "parsing_page",
                f"テキスト抽出中: ページ {i + 1}/{page_count}",
            )
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            texts.append(text)
            textpage.close()
            page.close()

        full_text = "\n".join(texts)
        pdf.close()

        # Check if scanned PDF (insufficient text)
        stripped = full_text.replace(" ", "").replace("\n", "").replace("\r", "")
        if len(stripped) >= SCANNED_PDF_TEXT_THRESHOLD:
            return ParseResult(
                text=full_text,
                content_type=mime_type,
                parser_used="pdf",
                metadata={
                    "page_count": str(page_count),
                    "extraction_method": "text",
                },
            )

        # Scanned PDF: render pages as images and use LLM (parallel)
        await self._notify(
            progress_callback,
            "parsing",
            f"テキストが少ないため、画像としてLLM解析に切り替えます（並列数: {self._max_concurrency}）...",
        )

        pdf = pdfium.PdfDocument(content)

        # Pre-render all pages to PNG bytes (CPU-bound, done sequentially)
        page_images: list[bytes] = []
        for i in range(page_count):
            page = pdf[i]
            bitmap = page.render(scale=2)
            pil_image: Image.Image = bitmap.to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            page_images.append(buf.getvalue())
            page.close()
        pdf.close()

        # LLM calls in parallel with semaphore
        semaphore = asyncio.Semaphore(self._max_concurrency)
        completed_count = 0

        async def process_page(page_index: int, image_bytes: bytes) -> str:
            nonlocal completed_count
            async with semaphore:
                result = await self._llm.describe_image(image_bytes, "image/png")
                completed_count += 1
                await self._notify(
                    progress_callback,
                    "parsing_page",
                    f"LLM画像解析完了: ページ {page_index + 1}/{page_count}"
                    f"（{completed_count}/{page_count} 完了）",
                )
                return result

        tasks = [process_page(i, img) for i, img in enumerate(page_images)]
        ocr_texts = await asyncio.gather(*tasks)

        return ParseResult(
            text="\n\n--- Page Break ---\n\n".join(ocr_texts),
            content_type=mime_type,
            parser_used="pdf",
            metadata={
                "page_count": str(page_count),
                "extraction_method": "image_fallback",
            },
        )
