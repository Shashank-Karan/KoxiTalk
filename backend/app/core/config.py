"""
Configuration settings for the chat application
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from decouple import config


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = config("DATABASE_URL", default="sqlite:///./chatapp.db")
    redis_url: str = config("REDIS_URL", default="redis://localhost:6379")
    
    # Security
    secret_key: str = config("SECRET_KEY", default="your-super-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_path: str = "uploads"
    allowed_file_extensions: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp",  # Images
        ".mp4", ".avi", ".mov", ".webm",  # Videos
        ".mp3", ".wav", ".ogg", ".aac",  # Audio
        ".pdf", ".doc", ".docx", ".txt",  # Documents
    ]
    
    # Real-time
    websocket_ping_interval: int = 25
    websocket_ping_timeout: int = 60
    
    # Rate Limiting
    rate_limit_messages_per_minute: int = 100
    rate_limit_files_per_hour: int = 50
    
    # Email (for notifications)
    smtp_host: str = config("SMTP_HOST", default="")
    smtp_port: int = config("SMTP_PORT", default=587)
    smtp_user: str = config("SMTP_USER", default="")
    smtp_password: str = config("SMTP_PASSWORD", default="")
    
    # Environment
    environment: str = config("ENVIRONMENT", default="development")
    debug: bool = config("DEBUG", default=True, cast=bool)
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
