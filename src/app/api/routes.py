import asyncio
import json
import mimetypes
from collections.abc import AsyncGenerator

import filetype
from fastapi import APIRouter, Request, UploadFile
from sse_starlette.sse import EventSourceResponse

from app.schemas import ErrorEvent, ParseResponse, ProgressEvent
from app.services.parser_registry import UnsupportedFileTypeError

router = APIRouter()


def detect_mime_type(content: bytes, filename: str | None) -> str:
    # Try binary detection first (images, PDFs, etc.)
    kind = filetype.guess(content)
    if kind is not None:
        mime = kind.mime
        # filetype identifies .docx as application/zip; fall back to extension
        if mime in ("application/zip",) and filename:
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                return guessed
        return mime

    # Fall back to extension-based detection (text files, etc.)
    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed

    return "application/octet-stream"


@router.post("/parse")
async def parse_file(file: UploadFile, request: Request) -> EventSourceResponse:
    settings = request.app.state.settings
    registry = request.app.state.parser_registry

    content = await file.read()

    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            # Size check
            if len(content) > settings.max_upload_size_bytes:
                yield {
                    "event": "error",
                    "data": ErrorEvent(
                        detail=f"File too large. Max size: {settings.max_upload_size_mb}MB"
                    ).model_dump_json(),
                }
                return

            yield {
                "event": "progress",
                "data": ProgressEvent(
                    step="file_received",
                    message=f"ファイルを受信しました: {file.filename}",
                ).model_dump_json(),
            }

            # MIME detection
            mime_type = detect_mime_type(content, file.filename)
            yield {
                "event": "progress",
                "data": ProgressEvent(
                    step="mime_detected",
                    message=f"MIME判定完了: {mime_type}",
                ).model_dump_json(),
            }

            # Get parser
            try:
                parser = registry.get_parser(mime_type)
            except UnsupportedFileTypeError:
                yield {
                    "event": "error",
                    "data": ErrorEvent(
                        detail=f"Unsupported file type: {mime_type}"
                    ).model_dump_json(),
                }
                return

            # Progress callback for parser internals
            queue: asyncio.Queue[dict] = asyncio.Queue()

            async def progress_callback(step: str, message: str) -> None:
                await queue.put({
                    "event": "progress",
                    "data": ProgressEvent(step=step, message=message).model_dump_json(),
                })

            # Run parser in background task, collect progress events
            async def run_parser() -> None:
                result = await parser.parse(
                    content, mime_type, file.filename or "unknown", progress_callback
                )
                await queue.put(("result", result))

            task = asyncio.create_task(run_parser())

            # Yield progress events as they arrive
            while True:
                item = await queue.get()
                if isinstance(item, tuple) and item[0] == "result":
                    parse_result = item[1]
                    break
                yield item

            await task  # ensure any exception propagates

            response = ParseResponse(
                filename=file.filename or "unknown",
                content_type=parse_result.content_type,
                parser_used=parse_result.parser_used,
                text=parse_result.text,
                metadata=parse_result.metadata,
            )
            yield {
                "event": "complete",
                "data": response.model_dump_json(),
            }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)}),
            }

    return EventSourceResponse(event_stream())
