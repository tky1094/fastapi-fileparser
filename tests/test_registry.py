import pytest

from app.parsers.text import TextParser
from app.services.parser_registry import ParserRegistry, UnsupportedFileTypeError


def test_register_and_get_parser() -> None:
    registry = ParserRegistry()
    parser = TextParser()
    registry.register(parser)

    result = registry.get_parser("text/plain")
    assert result is parser


def test_unsupported_file_type() -> None:
    registry = ParserRegistry()
    registry.register(TextParser())

    with pytest.raises(UnsupportedFileTypeError):
        registry.get_parser("application/zip")
