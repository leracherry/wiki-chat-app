"""Application configuration."""
import os
import logging
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Runtime configuration loaded from environment variables."""
    provider_api_key: str | None = os.getenv("PROVIDER_API_KEY") or os.getenv("COHERE_API_KEY")
    port: int = int(os.getenv("PORT", 8000))
    default_model: str = os.getenv("DEFAULT_MODEL", "command-r-plus")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self):
        """Configure logging level after initialization."""
        logging.getLogger().setLevel(getattr(logging, self.log_level))
        logger.info("settings.loaded", extra={
            "port": self.port,
            "default_model": self.default_model,
            "log_level": self.log_level,
            "has_api_key": bool(self.provider_api_key)
        })


settings = Settings()

if not settings.provider_api_key:
    error_msg = "PROVIDER_API_KEY environment variable is required (legacy COHERE_API_KEY also supported)"
    logger.error("settings.validation_error", extra={"error": error_msg})
    raise ValueError(error_msg)
