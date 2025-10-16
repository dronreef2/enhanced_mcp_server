"""Testes básicos para o Enhanced MCP Server."""
import pytest
from enhanced_mcp_server.settings import Settings

def test_settings():
    """Testa se as configurações são carregadas corretamente."""
    settings = Settings()
    assert settings.cache_ttl == 3600
    assert settings.log_level == "INFO"
    assert settings.request_timeout == 30