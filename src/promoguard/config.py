"""Application configuration. Keep secrets outside the repository."""

from pydantic import BaseModel


class Settings(BaseModel):
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()

