"""
FreshCart FastAPI Backend - Logger Configuration

Structured logging using Loguru with file rotation and console output.
"""
import sys
from pathlib import Path

from loguru import logger

from app.config.settings import settings


def setup_logger() -> None:
    """
    Configure Loguru logger with console and file handlers.
    
    Should be called once during application startup.
    """
    # Remove default handler
    logger.remove()
    
    # Console handler (always enabled)
    logger.add(
        sys.stdout,
        format=settings.log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )
    
    # File handler (if log file path is configured)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            settings.log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.log_level,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="zip",
            backtrace=True,
            diagnose=False,  # Don't include sensitive info in file logs
        )
    
    # JSON log file for production (structured logs)
    if settings.app_env == "production":
        json_log_path = Path(settings.log_file).parent / "app.json.log" if settings.log_file else Path("logs/app.json.log")
        json_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            str(json_log_path),
            format="{message}",
            level="INFO",
            rotation="50 MB",
            retention="30 days",
            compression="zip",
            serialize=True,  # Output as JSON
        )


# Configure logger on module import
setup_logger()

# Export configured logger
__all__ = ["logger", "setup_logger"]
