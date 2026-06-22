from pydantic import BaseModel


class ParseResponse(BaseModel):
    filename: str
    content_type: str
    parser_used: str
    text: str
    metadata: dict[str, str] = {}


class ProgressEvent(BaseModel):
    step: str
    message: str


class ErrorEvent(BaseModel):
    detail: str
