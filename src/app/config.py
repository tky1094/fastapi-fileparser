from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    llm_provider: LLMProvider = LLMProvider.ANTHROPIC

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    max_upload_size_mb: int = 20
    log_level: str = "INFO"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
