import pytest

from app.parsers.text import TextParser


@pytest.fixture
def parser() -> TextParser:
    return TextParser()


async def test_parse_utf8(parser: TextParser) -> None:
    content = "Hello, world! こんにちは".encode("utf-8")
    result = await parser.parse(content, "text/plain", "test.txt")
    assert result.text == "Hello, world! こんにちは"
    assert result.parser_used == "text"
    # charset-normalizer returns "utf_8" (underscore) or "ascii"
    enc = result.metadata["detected_encoding"].lower().replace("_", "-").replace("ascii", "utf-8")
    assert enc in ("utf-8", "ascii")


async def test_parse_shift_jis(parser: TextParser) -> None:
    # Use longer text for more reliable detection
    text = "これは日本語のテスト文字列です。文字コード検出のテストを行っています。"
    content = text.encode("shift_jis")
    result = await parser.parse(content, "text/plain", "test.txt")
    assert text in result.text
    assert result.parser_used == "text"
    # charset-normalizer may detect as cp932 (superset of shift_jis)
    enc = result.metadata["detected_encoding"].lower()
    assert enc in ("shift_jis", "cp932", "shift-jis")


async def test_parse_euc_jp(parser: TextParser) -> None:
    # Use longer text for more reliable detection
    text = "これは日本語のテスト文字列です。文字コード検出のテストを行っています。正しく検出されるべきです。"
    content = text.encode("euc_jp")
    result = await parser.parse(content, "text/plain", "test.txt")
    assert text in result.text


async def test_parse_empty(parser: TextParser) -> None:
    result = await parser.parse(b"", "text/plain", "empty.txt")
    assert result.text == ""


async def test_supported_mimetypes(parser: TextParser) -> None:
    mimes = parser.supported_mimetypes()
    assert "text/plain" in mimes
    assert "text/csv" in mimes
    assert "application/json" in mimes
