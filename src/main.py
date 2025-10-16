"""Ponto de entrada principal para executar o servidor com Uvicorn."""
import uvicorn
import os
from enhanced_mcp_server.server import create_server
from enhanced_mcp_server.logging import setup_logging
from enhanced_mcp_server.settings import settings

def main():
    setup_logging()
    server = create_server()
    uvicorn.run(server, host="0.0.0.0", port=settings.port)

if __name__ == "__main__":
    main()