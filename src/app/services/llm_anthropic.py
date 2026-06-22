import base64

import anthropic

from app.services.llm import BaseLLMService

IMAGE_PROMPT = (
    "この画像を分析してください。"
    "画像内にテキストが含まれている場合は、すべてのテキストを正確に抽出してください。"
    "テキストが含まれていない場合は、画像の情景や内容を簡潔に説明してください。"
)


class AnthropicLLMService(BaseLLMService):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def describe_image(self, image_bytes: bytes, media_type: str) -> str:
        b64_data = base64.b64encode(image_bytes).decode()
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": IMAGE_PROMPT,
                        },
                    ],
                }
            ],
        )
        return response.content[0].text
