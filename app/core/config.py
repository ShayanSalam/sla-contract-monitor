from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GOOGLE_API_KEY: str = ""

    # Comma-separated list of allowed frontend origins for CORS, e.g.
    # "https://your-app.streamlit.app,http://localhost:8501"
    CORS_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"

    # Optional SMTP settings for real email alerts - if left blank, the
    # alerting service simulates emails by logging instead of sending them
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM: str = ""

    @property
    def CORS_ALLOWED_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
