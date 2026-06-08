from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_models: str = "gemini-2.5-flash-lite,gemini-2.0-flash-lite"
    groq_api_key: str | None = None
    groq_text_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_transcribe_model: str = "whisper-large-v3"
    openai_api_key: str | None = None
    openai_text_model: str = "gpt-5.2"
    openai_transcribe_model: str = "gpt-4o-mini-transcribe"
    openai_image_model: str = "gpt-image-1.5"
    database_path: Path = Path("work/smm_bot.sqlite3")
    temp_dir: Path = Path("work/tmp")
    openai_enable_image_generation: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def ensure_dirs(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
