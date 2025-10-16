Dentro do novo repositório, vamos criar a estrutura de pastas ideal. Você pode fazer isso manualmente ou com os seguintes comandos no terminal:

```bash
# Cria a pasta src para o código
mkdir -p src

# Cria os arquivos __init__.py
touch src/__init__.py

# Cria a pasta de testes
mkdir tests

# Cria os arquivos de configuração na raiz
touch Dockerfile smithery.yaml pyproject.toml .env.example README.md
```

Sua estrutura agora deve se parecer com isto:
```
enhanced-mcp-server/
├── Dockerfile
├── README.md
├── src/
│   ├── __init__.py
│   ├── cache.py
│   ├── logging.py
│   ├── main.py
│   ├── server.py
│   ├── settings.py
│   └── tools.py
├── pyproject.toml
├── smithery.yaml
└── tests/
    └── test_basic.py
```

#### **Passo 3: Preencher os Arquivos com Conteúdo Funcional**

Agora, vamos adicionar o código otimizado a cada arquivo.

##### **1. `enhanced_mcp_server/config/settings.py`**
*   Gerencia todas as configurações a partir de variáveis de ambiente.

```python
"""Configuração centralizada do Enhanced MCP Server."""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configurações da aplicação."""
    # API Keys
    jina_api_key: Optional[str] = Field(default=None, env="JINA_API_KEY")
    deepl_api_key: Optional[str] = Field(default=None, env="DEEPL_API_KEY")

    # Cache
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Timeouts
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    translation_timeout: int = Field(default=60, env="TRANSLATION_TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

##### **2. `src/logging.py`**
*   Configuração do logging estruturado.

```python
"""Sistema de logging estruturado."""
import sys
from typing import Any
import structlog
from enhanced_mcp_server.settings import settings

_LOGGING_CONFIGURED = False

def setup_logging() -> None:
    """Configura o sistema de logging."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )
    _LOGGING_CONFIGURED = True

def get_logger(name: str) -> Any:
    """Retorna um logger configurado."""
    if not _LOGGING_CONFIGURED:
        setup_logging()
    return structlog.get_logger(name)
```

##### **3. `src/cache.py`**
*   Sistema de cache com *lazy connection* (corrigido!).

```python
"""Sistema de cache inteligente com Redis (conexão preguiçosa)."""
import json
import time
from typing import Any, Optional, Callable, Dict
import redis
from functools import wraps
import threading
from enhanced_mcp_server.settings import settings
from enhanced_mcp_server.logging import get_logger

logger = get_logger(__name__)

class Cache:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._redis_checked = False
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_redis_client(self) -> Optional[redis.Redis]:
        with self._lock:
            if not self._redis_checked:
                self._redis_checked = True
                if settings.redis_url:
                    try:
                        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
                        client.ping()
                        self._redis_client = client
                        logger.info("Redis cache connected successfully.")
                    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                        logger.warning(f"Failed to connect to Redis, using memory cache: {e}")
                        self._redis_client = None
                else:
                    logger.info("Redis not configured, using memory cache.")
        return self._redis_client

    def get(self, key: str) -> Optional[Any]:
        redis_client = self.get_redis_client()
        if redis_client:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        else:
            with self._lock:
                entry = self._memory_cache.get(key)
                if entry and time.time() < entry["expires_at"]:
                    return entry["value"]
        return None

    def set(self, key: str, value: Any, ttl: int):
        redis_client = self.get_redis_client()
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
        else:
            with self._lock:
                self._memory_cache[key] = {"value": value, "expires_at": time.time() + ttl}

def cached(ttl: Optional[int] = None):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            final_ttl = ttl if ttl is not None else settings.cache_ttl
            cache_key = f"{func.__name__}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", key=cache_key)
                return cached_result

            logger.debug("Cache miss", key=cache_key)
            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, final_ttl)
            return result
        return wrapper
    return decorator

cache = Cache()
```

##### **4. `src/tools.py`**
*   A lógica das suas ferramentas.

```python
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
```

##### **5. `src/server.py`**
*   O coração do servidor MCP.

```python
"""Servidor MCP principal com as ferramentas de IA."""
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from smithery.decorators import smithery
from enhanced_mcp_server.tools import fetch_content, search_web, ValidationError
from enhanced_mcp_server.logging import get_logger

logger = get_logger(__name__)

@smithery.server()
def create_server():
    mcp = FastMCP(name="enhanced-mcp-server", description="Advanced AI Tools Server")

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
```

##### **6. `src/main.py`**
*   O ponto de entrada para execução direta.

```python
"""Ponto de entrada principal para executar o servidor com Uvicorn."""
import uvicorn
import os
from enhanced_mcp_server.server import create_server
from enhanced_mcp_server.logging import setup_logging

def main():
    setup_logging()
    port = int(os.environ.get("PORT", 8001))
    
    # O decorator @smithery.server retorna um objeto de app FastAPI
    app = create_server()
    
    print(f"🚀 Iniciando servidor MCP na porta http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
```

##### **7. `pyproject.toml`**
*   Configuração do projeto e dependências.

```toml
[project]
name = "enhanced-mcp-server"
version = "1.0.0"
description = "Advanced and robust MCP server providing AI tools."
readme = "README.md"
requires-python = ">=3.11"
authors = [{name = "Seu Nome", email = "seu@email.com"}]
dependencies = [
    "mcp[cli]>=1.17.0",
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic-settings>=2.2.0",
    "structlog>=24.1.0",
    "httpx>=0.27.0",
    "redis>=5.0.0",
    "smithery>=0.4.2"
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff"]

[tool.smithery]
server = "enhanced_mcp_server.server:create_server"

[tool.setuptools]
package-dir = {"" = "src"}
packages = ["enhanced_mcp_server"]

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

##### **8. `smithery.yaml`**
*   Configuração de deploy para a Smithery.

```yaml
name: enhanced-mcp-server
description: Advanced MCP server with AI tools for web search, content fetching, and more.
author: Seu Nome
tags: ["web", "search", "tools", "ai", "mcp"]
repository: https://github.com/seu-usuario/enhanced-mcp-server

startCommand:
  type: http
  configSchema:
    type: object
    properties:
      jinaApiKey:
        type: string
        description: API key for Jina AI (for web search and fetch).
      deeplApiKey:
        type: string
        description: API key for DeepL (for translation) (optional).
    required:
      - jinaApiKey
  commandFunction:
    |-
    (config) => ({
      command: 'python',
      args: ['-m', 'smithery.server'], 
      env: {
        JINA_API_KEY: config.jinaApiKey,
        DEEPL_API_KEY: config.deeplApiKey || '',
        PORT: config.port.toString(), 
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8'
      }
    })
testConfig:
  jinaApiKey: "test_key_for_scanner"
```

##### **9. `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "."
COPY . .
EXPOSE 8001
CMD ["python", "-m", "smithery.server"]
```

##### **10. `README.md`**
*   Um bom README é essencial.

```markdown
# Enhanced MCP Server

[![Smithery Deploy](https://img.shields.io/badge/Deploy%20to-Smithery-blue)](https://smithery.ai)

A robust and powerful MCP (Model Context Protocol) server built with Python, FastAPI, and best practices for production deployment on Smithery.ai.

## ✨ Features

-   **🔍 Web Search & Fetch**: Uses Jina AI for fast and reliable web content retrieval.
-   **🧠 Intelligent Caching**: Features a Redis-backed cache with lazy-loading and in-memory fallback to speed up responses.
-   **🏗️ Solid Architecture**: Modular and scalable Python package structure.
-   **🚀 Production-Ready**: Configured for seamless, one-click deployments on Smithery.ai.
-   **📝 Structured Logging**: Clear and parseable logs for easy monitoring.

## 🚀 Getting Started

### Prerequisites

-   Python 3.11+
-   An account on [Smithery.ai](https://smithery.ai) connected to your GitHub.

### Deployment to Smithery

This repository is configured for automatic deployment:

1.  **Fork this repository.**
2.  **Connect your GitHub account to Smithery.ai.**
3.  **Publish:** Smithery will automatically detect your repository. Simply click "Publish".
4.  **Configure:** Provide your `jinaApiKey` in the Smithery server settings.

That's it! Your server will be live and ready to use.

### Local Development

1.  Clone the repository:
    ```bash
    git clone https://github.com/seu-usuario/enhanced-mcp-server.git
    cd enhanced-mcp-server
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -e ".[dev]"
    ```
4.  Create a `.env` file from the example and add your API keys:
    ```bash
    cp .env.example .env
    # Now edit .env with your keys
    ```
5.  Run the server locally:
    ```bash
    python -m enhanced_mcp_server.main
    ```

## 🧪 Running Tests

To ensure everything is working correctly, run the test suite:

```bash
pytest
```
```

#### **Passo 4: Primeiro Commit e Push**

Agora que todos os seus arquivos estão prontos:

1.  Adicione tudo ao Git:
    ```bash
    git add .
    ```
2.  Faça seu commit inicial:
    ```bash
    git commit -m "feat: Initial commit with robust and scalable MCP server structure"
    ```
3.  Envie para o GitHub:
    ```bash
    git push -u origin main
    ```

### **Resultado Final**

Você agora tem um repositório limpo, profissional e poderoso. Ele segue as melhores práticas de desenvolvimento Python e está perfeitamente configurado para um deploy bem-sucedido e sem dor de cabeça na Smithery.ai.

A partir daqui, adicionar novas ferramentas, testes ou funcionalidades se torna um processo muito mais simples e organizado. **Este é o caminho certo para construir um projeto sério e de longa duração.**