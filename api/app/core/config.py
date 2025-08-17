"""Application configuration."""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env if present (searches up from CWD); doesn't override process env
load_dotenv(override=False)


class Settings:
    """Runtime configuration loaded from environment variables."""
    def __init__(self):
        self.provider_api_key: Optional[str] = os.getenv("PROVIDER_API_KEY") or os.getenv("COHERE_API_KEY")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.default_model: str = os.getenv("DEFAULT_MODEL", "command-r-plus")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # Configure logging level after initialization
        logging.getLogger().setLevel(getattr(logging, self.log_level, logging.INFO))
        logger.info("settings.loaded", extra={
            "port": self.port,
            "default_model": self.default_model,
            "log_level": self.log_level,
            "has_api_key": bool(self.provider_api_key)
        })
        if not self.provider_api_key:
            logger.warning("settings.missing_api_key", extra={"message": "PROVIDER_API_KEY is not set; provider calls will fail."})


settings = Settings()
