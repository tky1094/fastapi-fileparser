import io

import pypdfium2 as pdfium
import pytest

from app.parsers.pdf import PdfParser
from tests.conftest import MockLLMService


def create_text_pdf(text: str) -> bytes:
    """Create a minimal PDF with text using pypdfium2."""
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(200, 100)

    # We can't easily add text with pypdfium2 alone,
    # so we create a PDF manually with reportlab-like approach.
    # Instead, use a raw PDF string.
    page.close()
    pdf.close()

    # Build a minimal PDF with text manually
    pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET")} >>
stream
BT /F1 12 Tf 100 700 Td ({text}) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF"""
    return pdf_content.encode("latin-1")


def create_blank_pdf() -> bytes:
    """Create a PDF with no text (simulates scanned PDF)."""
    # Create a PDF with an image page but no text
    pdf = pdfium.PdfDocument.new()
    page = pdf.new_page(200, 100)
    page.close()

    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


@pytest.fixture
def mock_llm() -> MockLLMService:
    return MockLLMService()


@pytest.fixture
def parser(mock_llm: MockLLMService) -> PdfParser:
    return PdfParser(mock_llm)


async def test_parse_text_pdf(parser: PdfParser, mock_llm: MockLLMService) -> None:
    pdf_bytes = create_text_pdf("Hello World this is a test of text extraction from PDF documents")
    result = await parser.parse(pdf_bytes, "application/pdf", "test.pdf")

    assert result.parser_used == "pdf"
    assert result.metadata["extraction_method"] == "text"
    assert "Hello World" in result.text
    mock_llm._mock_describe_image.assert_not_called()


async def test_parse_scanned_pdf(parser: PdfParser, mock_llm: MockLLMService) -> None:
    pdf_bytes = create_blank_pdf()
    mock_llm._mock_describe_image.return_value = "OCR result from scanned page"

    result = await parser.parse(pdf_bytes, "application/pdf", "scanned.pdf")

    assert result.parser_used == "pdf"
    assert result.metadata["extraction_method"] == "image_fallback"
    mock_llm._mock_describe_image.assert_called()


async def test_supported_mimetypes(parser: PdfParser) -> None:
    assert "application/pdf" in parser.supported_mimetypes()
