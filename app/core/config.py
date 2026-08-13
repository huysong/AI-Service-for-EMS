# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # DB
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    # LLM
    LLM_API_URL: str = "http://localhost:1234/v1/chat/completions"
    LLM_MODEL: str = "local-model"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1000

    # Whisper
    WHISPER_MODEL: str = "medium"


    # AI
    CONFIDENCE_THRESHOLD: float = 60.0
    PROMPT_FILE_PATH: str = "app/prompts/triage_system_prompt.txt"

    AI_API_KEY: str
    SPRING_BOOT_CALLBACK_KEY: str

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()