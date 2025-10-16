# Enhanced MCP Server – Copilot Instructions

## Big Picture
- README.md is the source of truth; the code skeleton described there may not exist yet, so generate files exactly as specified before extending.
- Target architecture is a Python package `enhanced_mcp_server` with modules in `src/` for `settings`, `logging`, `cache`, `tools`, `server`, and `main`.
- The server is built around `smithery.server` + `FastMCP`, exposing async MCP tools for web fetching and search.
- HTTP interactions rely on `httpx.AsyncClient` with bearer auth against Jina AI endpoints.
- Caching wraps tool functions via a `cached` decorator that prefers Redis but falls back to an in-memory dict guarded by a threading lock.

## Configuration & Environment
- Centralize configuration in `src/settings.py` using `pydantic_settings.BaseSettings`; load `.env` and expose a module-level `settings` instance.
- Expected env vars: `JINA_API_KEY`, `DEEPL_API_KEY`, `REDIS_URL`, `CACHE_TTL`, `LOG_LEVEL`, `REQUEST_TIMEOUT`, `TRANSLATION_TIMEOUT`, `PORT`.
- When adding new settings, expose them through the `Settings` class so all modules import from one place.
- Logging must flow through `src/logging.py`, calling `setup_logging()` once and retrieving loggers with `get_logger(name)`.

## Core Components
- `src/server.py` should define `create_server()` returning the `FastMCP` app and register tools via `@mcp.tool`; catch `ValidationError` and log structured warnings.
- Tool implementations live in `src/tools.py`; keep them async, raise `ValidationError` for user-facing issues, and rely on `settings` for timeouts and keys.
- Any new tool that hits slow IO should use the `@cached` decorator with an explicit TTL to avoid stale data.
- `src/cache.py` manages Redis lazily; always protect shared structures with the provided lock and respect TTL semantics.
- `src/main.py` is the CLI entry point: call `setup_logging()`, read `PORT`, build the server via `create_server()`, and run `uvicorn`.

## Workflows
- Use Python 3.11 and install dependencies with `pip install -e ".[dev]"` at the repo root.
- Run the server locally with `python -m enhanced_mcp_server.main`; the `smithery` CLI entry should stay configured in `pyproject.toml`.
- Execute tests with `pytest`; add `pytest-asyncio` markers for coroutine-based tests.
- Deployment to Smithery expects the default command `python -m smithery.server` and relies on the env var contract in `smithery.yaml`.

## Conventions
- Keep modules importable without side effects; defer heavy setup to functions like `create_server()` or `setup_logging()`.
- Prefer structured logging via `structlog` and pass contextual keywords (e.g., `logger.warning("Fetch validation error", url=url, error=str(e))`).
- Always validate external inputs and translate HTTP errors into `ValidationError` messages surfaced to the MCP client.
- When extending caching, ensure keys are JSON-serializable and keep TTL configurable through settings or decorator arguments.
- Update README.md when altering architecture or required environment variables so future agents stay aligned.

## Deployment Plan
Aqui está um plano estruturado para criar um projeto pessoal de servidor MCP (Model Context Protocol) em Python, visando o deploy no smithery.ai. O plano é baseado na arquitetura já implementada no workspace atual (enhanced_mcp_server), que serve como referência, mas pode ser adaptado para um novo projeto. Ele segue as melhores práticas para MCP servers usando FastMCP e Smithery.

O plano inclui 13 tarefas principais, organizadas em ordem lógica de execução. Cada tarefa tem uma descrição detalhada para guiar a implementação.

### Visão Geral do Plano
- **Objetivo**: Criar um servidor MCP assíncrono que expõe ferramentas para busca e extração de conteúdo web via Jina AI, com cache (Redis/in-memory) e deploy no Smithery.
- **Tecnologias**: Python 3.11+, FastMCP, httpx, pydantic-settings, structlog, Redis, pytest.
- **Estrutura**: Pacote flat em `src/`, com módulos para settings, logging, cache, tools, server, main.
- **Deploy**: Via Smithery, usando `smithery.yaml` para configuração de ambiente e comando de inicialização.

### Próximos Passos Recomendados
1. Execute `uvx smithery init` em um novo diretório para gerar a estrutura base.
2. Siga as tarefas sequencialmente, marcando-as como concluídas à medida que avança.
3. Teste incrementalmente (ex.: rode `pytest` após implementar testes) para validar cada etapa.
4. Para deploy, certifique-se de que `smithery.yaml` esteja configurado corretamente com as variáveis de ambiente necessárias.

### Tarefas
1. **Inicializar projeto Smithery**: Execute `uvx smithery init` para configurar a estrutura básica e arquivos de configuração.
2. **Configurar estrutura do pacote Python**: Configure o diretório `src/`, `pyproject.toml` e módulos necessários (settings, logging, cache, tools, server, main).
3. **Implementar ferramentas MCP**: Adicione funções assíncronas em `src/tools.py` para busca e extração web usando FastMCP, httpx e Jina AI.
4. **Configurar ambiente e variáveis**: Configure `src/settings.py` com pydantic-settings e `.env.example` para variáveis como `JINA_API_KEY`, `REDIS_URL`, etc.
5. **Adicionar mecanismo de cache**: Implemente `src/cache.py` com conexão lazy ao Redis, fallback para dict in-memory e decorator `@cached` para funções assíncronas.
6. **Configurar logging**: Configure `src/logging.py` com structlog para logging estruturado, integrado ao server e main.
7. **Construir servidor MCP**: Crie `src/server.py` com `create_server()` para registrar ferramentas no app FastMCP, capturando `ValidationError`.
8. **Configurar ponto de entrada main**: Escreva `src/main.py` como CLI para executar uvicorn com o server.
9. **Configurar deploy no Smithery**: Configure `smithery.yaml` com comando de inicialização HTTP e variáveis de ambiente.
10. **Criar Dockerfile**: Adicione Dockerfile com imagem Python slim e CMD para `smithery.server`.
11. **Adicionar testes**: Escreva testes em `tests/` usando pytest e pytest-asyncio para validar ferramentas e configurações.
12. **Testar localmente**: Execute `python -m enhanced_mcp_server.main` e garanta que as ferramentas funcionem corretamente.
13. **Deploy no Smithery**: Use o `smithery.yaml` configurado para fazer deploy e verificar no smithery.ai.
