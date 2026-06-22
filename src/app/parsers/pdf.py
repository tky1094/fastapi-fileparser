import io

import pypdfium2 as pdfium
from PIL import Image

from app.parsers.base import BaseParser, ParseResult, ProgressCallback
from app.services.llm import BaseLLMService

SCANNED_PDF_TEXT_THRESHOLD = 50


class PdfParser(BaseParser):
    def __init__(self, llm_service: BaseLLMService) -> None:
        self._llm = llm_service

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

        # Check if scanned PDF (insufficient text)
        stripped = full_text.replace(" ", "").replace("\n", "").replace("\r", "")
        if len(stripped) >= SCANNED_PDF_TEXT_THRESHOLD:
            pdf.close()
            return ParseResult(
                text=full_text,
                content_type=mime_type,
                parser_used="pdf",
                metadata={
                    "page_count": str(page_count),
                    "extraction_method": "text",
                },
            )

        # Scanned PDF: render pages as images and use LLM
        await self._notify(
            progress_callback,
            "parsing",
            "テキストが少ないため、画像としてLLM解析に切り替えます...",
        )

        pdf = pdfium.PdfDocument(content)
        ocr_texts: list[str] = []
        for i in range(page_count):
            await self._notify(
                progress_callback,
                "parsing_page",
                f"LLMで画像解析中: ページ {i + 1}/{page_count}",
            )
            page = pdf[i]
            bitmap = page.render(scale=2)
            pil_image: Image.Image = bitmap.to_pil()

            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

            text = await self._llm.describe_image(image_bytes, "image/png")
            ocr_texts.append(text)

            page.close()

        pdf.close()

        return ParseResult(
            text="\n\n--- Page Break ---\n\n".join(ocr_texts),
            content_type=mime_type,
            parser_used="pdf",
            metadata={
                "page_count": str(page_count),
                "extraction_method": "image_fallback",
            },
        )
