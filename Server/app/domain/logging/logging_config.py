import sys
import logging
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logger():
    logger.remove()

    # Intercept stdlib logs (uvicorn, asyncio, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

    # Optional: Silence noisy libs (you can add/remove as needed)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").disabled = True

    # Error logs to file (persistent storage)
    logger.add(
        "logs/error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="1 week",
        retention="1 month",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # STDOUT log for Docker – plain, clean, non-color
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} - {message}",
        colorize=False,
        enqueue=True,
        backtrace=False,
    )