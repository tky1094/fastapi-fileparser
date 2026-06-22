import base64

import openai

from app.services.llm import BaseLLMService

IMAGE_PROMPT = (
    "この画像を分析してください。"
    "画像内にテキストが含まれている場合は、すべてのテキストを正確に抽出してください。"
    "テキストが含まれていない場合は、画像の情景や内容を簡潔に説明してください。"
)


class OpenAILLMService(BaseLLMService):
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def describe_image(self, image_bytes: bytes, media_type: str) -> str:
        b64_data = base64.b64encode(image_bytes).decode()
        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64_data}",
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
        return response.choices[0].message.content or ""
