from abc import ABC, abstractmethod


class BaseLLMService(ABC):
    @abstractmethod
    async def describe_image(self, image_bytes: bytes, media_type: str) -> str:
        """Analyze an image: extract text if present, otherwise describe the scene."""
        ...
