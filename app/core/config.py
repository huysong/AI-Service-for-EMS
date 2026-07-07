# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    LMSTUDIO_API_URL: str = "http://localhost:1234/v1/chat/completions"
    LMSTUDIO_MODEL: str = "local-model"
    LMSTUDIO_TEMPERATURE: float = 0.1
    LMSTUDIO_MAX_TOKENS: int = 1000
    CONFIDENCE_THRESHOLD: float = 60.0
    PROMPT_FILE_PATH: str = "app/prompts/triage_system_prompt.txt"
    AI_API_KEY: str = "ems-cad-ai-secret-key-123456"
    SPRING_BOOT_CALLBACK_KEY: str = "ems-cad-callback-secret-key-789012"


    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()