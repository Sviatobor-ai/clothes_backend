# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # App
    app_env: str = Field("local", alias="APP_ENV")
    tz: str = Field("Europe/Warsaw", alias="TZ")

    # APIs
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")

    # Telegram (Telethon user session)
    tg_api_id: int = Field(..., alias="TELEGRAM_API_ID")
    tg_api_hash: str = Field(..., alias="TELEGRAM_API_HASH")
    tg_phone: str = Field(..., alias="TELEGRAM_PHONE")
    tg_target_chat_id: int = Field(..., alias="TELEGRAM_TARGET_CHAT_ID")

    # Generation controls
    daily_jobs: int = Field(17, alias="DAILY_JOBS")
    run_window_start: str = Field("10:00", alias="RUN_WINDOW_START")
    run_window_end: str = Field("11:00", alias="RUN_WINDOW_END")
    images_per_job: int = Field(2, alias="IMAGES_PER_JOB")
    image_aspect: str = Field("VERTICAL", alias="IMAGE_ASPECT")
    image_format: str = Field("png", alias="IMAGE_FORMAT")
    retry_backoff_minutes: int = Field(5, alias="RETRY_BACKOFF_MINUTES")
    max_prompt_regens: int = Field(1, alias="MAX_PROMPT_REGENS")
    max_total_failure_cycles: int = Field(2, alias="MAX_TOTAL_FAILURE_CYCLES")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()