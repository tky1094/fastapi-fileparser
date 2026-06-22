from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


ProgressCallback = Callable[[str, str], Awaitable[None]]


@dataclass
class ParseResult:
    text: str
    content_type: str
    parser_used: str
    metadata: dict[str, str] = field(default_factory=dict)


class BaseParser(ABC):
    @abstractmethod
    def supported_mimetypes(self) -> set[str]:
        ...

    @abstractmethod
    async def parse(
        self,
        content: bytes,
        mime_type: str,
        filename: str,
        progress_callback: ProgressCallback | None = None,
    ) -> ParseResult:
        ...

    async def _notify(
        self,
        callback: ProgressCallback | None,
        step: str,
        message: str,
    ) -> None:
        if callback:
            await callback(step, message)
