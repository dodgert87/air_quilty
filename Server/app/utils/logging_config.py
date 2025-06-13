import logging
import sys
from loguru import logger

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Map standard logging levels to loguru levels
        level = logger.level(record.levelname).name if record.levelname in logger._core.levels else record.levelno # type: ignore
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    logger.remove()  # Remove default log handler

    #  Intercept standard logging to loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.WARNING, force=True)

    # Silencing specific modules (you had this already, keeping it)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("pydantic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    #  Pretty console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level="INFO",
        enqueue=True,
        backtrace=False,
        colorize=True,
    )
"""
    #  Optional: JSON file logging
    logger.add(
        "logs/structured.json",
        level="INFO",
        serialize=True,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
"""