from app.parsers.base import BaseParser


class UnsupportedFileTypeError(Exception):
    def __init__(self, mime_type: str) -> None:
        self.mime_type = mime_type
        super().__init__(f"Unsupported file type: {mime_type}")


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser) -> None:
        self._parsers.append(parser)

    def get_parser(self, mime_type: str) -> BaseParser:
        for parser in self._parsers:
            if mime_type in parser.supported_mimetypes():
                return parser
        raise UnsupportedFileTypeError(mime_type)
