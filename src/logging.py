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