"""Ferramentas MCP para busca e tradução."""
import httpx
from enhanced_mcp_server.settings import settings
from enhanced_mcp_server.cache import cached
from enhanced_mcp_server.logging import get_logger

logger = get_logger(__name__)

class ValidationError(Exception):
    pass

@cached(ttl=1800)
async def fetch_content(url: str) -> str:
    if not settings.jina_api_key:
        raise ValidationError("JINA_API_KEY is not configured.")
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                f"https://r.jina.ai/{url}",
                headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            )
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        raise ValidationError(f"HTTP error {e.response.status_code}")
    except Exception as e:
        logger.error("Error during fetch", url=url, error=str(e))
        raise ValidationError(f"Failed to fetch content: {str(e)}")

@cached(ttl=900)
async def search_web(query: str) -> str:
    if not settings.jina_api_key:
        raise ValidationError("JINA_API_KEY is not configured.")
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                f"https://s.jina.ai/?q={query}",
                headers={"Authorization": f"Bearer {settings.jina_api_key}"},
            )
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error("Error during search", query=query, error=str(e))
        raise ValidationError(f"Failed to search: {str(e)}")