"""
Configuration management using environment variables
"""

from pydantic import HttpUrl
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""

    app_url: HttpUrl

    # Database
    database_url: str

    # Security
    admin_token: str
    secret_key: str
    jwt_secret: str

    # Google Forms API
    google_credentials_path: str = "credentials.json"

    # Application
    app_name: str = "URL Redirect & A/B Testing"
    debug: bool = False

    # Session
    session_cookie_name: str = "admin_session"
    session_max_age: int = 86400  # 24 hours

    # A/B Testing
    click_id_max_age_seconds: int = 60  # 1 minute

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings(**{})
