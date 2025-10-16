"""Configuração centralizada do Enhanced MCP Server."""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configurações da aplicação."""
    # API Keys
    jina_api_key: Optional[str] = None
    deepl_api_key: Optional[str] = None

    # Cache
    redis_url: Optional[str] = None
    cache_ttl: int = 3600

    # Logging
    log_level: str = "INFO"

    # Timeouts
    request_timeout: int = 30
    translation_timeout: int = 60

    # Server
    port: int = 8002

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()