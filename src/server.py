"""Servidor MCP principal com as ferramentas de IA."""
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from smithery.decorators import smithery
from enhanced_mcp_server.tools import fetch_content, search_web, ValidationError
from enhanced_mcp_server.logging import get_logger

logger = get_logger(__name__)

# @smithery.server()
def create_server():
    mcp = FastMCP(name="enhanced-mcp-server")

    @mcp.tool(name="fetch", description="Fetches the content of a web page.")
    async def fetch(url: str = Field(description="The URL of the webpage to fetch.")) -> str:
        try:
            return await fetch_content(url)
        except ValidationError as e:
            logger.warning("Fetch validation error", url=url, error=str(e))
            return f"Error: {str(e)}"

    @mcp.tool(name="search", description="Searches the web for a given query.")
    async def search(query: str = Field(description="The search query.")) -> str:
        try:
            return await search_web(query)
        except ValidationError as e:
            logger.warning("Search validation error", query=query, error=str(e))
            return f"Error: {str(e)}"

    return mcp