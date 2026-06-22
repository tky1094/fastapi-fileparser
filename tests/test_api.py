import io
import json

from docx import Document
from httpx import AsyncClient


async def test_parse_text_file(client: AsyncClient) -> None:
    content = "Hello, world!".encode("utf-8")
    response = await client.post(
        "/parse",
        files={"file": ("test.txt", content, "text/plain")},
    )
    assert response.status_code == 200

    # Parse SSE events
    events = parse_sse_events(response.text)
    assert any(e["event"] == "progress" for e in events)

    complete_event = next(e for e in events if e["event"] == "complete")
    data = json.loads(complete_event["data"])
    assert data["parser_used"] == "text"
    assert "Hello, world!" in data["text"]


async def test_parse_docx_file(client: AsyncClient) -> None:
    doc = Document()
    doc.add_paragraph("Test paragraph")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    response = await client.post(
        "/parse",
        files={
            "file": (
                "test.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200

    events = parse_sse_events(response.text)
    complete_event = next(e for e in events if e["event"] == "complete")
    data = json.loads(complete_event["data"])
    assert data["parser_used"] == "docx"
    assert "Test paragraph" in data["text"]


async def test_parse_unsupported_file(client: AsyncClient) -> None:
    response = await client.post(
        "/parse",
        files={"file": ("test.zip", b"PK\x03\x04fake", "application/zip")},
    )
    assert response.status_code == 200  # SSE always returns 200

    events = parse_sse_events(response.text)
    error_event = next((e for e in events if e["event"] == "error"), None)
    assert error_event is not None
    data = json.loads(error_event["data"])
    assert "Unsupported" in data["detail"]


def parse_sse_events(text: str) -> list[dict]:
    """Parse raw SSE text into a list of event dicts."""
    events = []
    current: dict = {}
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events
