"""Testes básicos para o Enhanced MCP Server."""
import pytest
from enhanced_mcp_server.settings import Settings
from unittest.mock import patch, AsyncMock
from enhanced_mcp_server.tools import fetch_content, search_web, ValidationError

def test_settings():
    """Testa se as configurações são carregadas corretamente."""
    settings = Settings()
    assert settings.cache_ttl == 3600
    assert settings.log_level == "INFO"
    assert settings.request_timeout == 30

@pytest.mark.asyncio
async def test_fetch_content_valid_url():
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.text = "Fetched content"
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        result = await fetch_content("https://example.com")
        assert result == "Fetched content"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_content_invalid_url():
    with pytest.raises(ValidationError):
        await fetch_content("invalid-url")

@pytest.mark.asyncio
async def test_search_web_valid_query():
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.text = "Search results"
        mock_response.raise_for_status = AsyncMock()
        mock_get.return_value = mock_response

        result = await search_web("test query")
        assert result == "Search results"
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_search_web_empty_query():
    with pytest.raises(ValidationError):
        await search_web("")