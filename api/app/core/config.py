"""Application configuration."""
import os
import logging
from typing import Literal
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger(__name__)


def _load_env_layered():
    """Load env variables with predictable precedence.

    Order (first loaded has lowest precedence; later calls override earlier):
    1) repo-root/.env
    2) repo-root/.env.local
    3) api/.env
    4) api/.env.local
    """
    # 1/2: repo root
    repo_root_env = find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=True)
    if repo_root_env:
        load_dotenv(repo_root_env, override=False)
    repo_root_env_local = find_dotenv(filename=".env.local", raise_error_if_not_found=False, usecwd=True)
    if repo_root_env_local:
        load_dotenv(repo_root_env_local, override=True)

    # 3/4: api
    api_env = find_dotenv(filename="api/.env", raise_error_if_not_found=False, usecwd=True)
    if api_env:
        load_dotenv(api_env, override=True)
    api_env_local = find_dotenv(filename="api/.env.local", raise_error_if_not_found=False, usecwd=True)
    if api_env_local:
        load_dotenv(api_env_local, override=True)


# Load envs before reading settings
_load_env_layered()


class Settings:
    """Runtime configuration loaded from environment variables."""
    def __init__(self):
        self.provider_api_key: str | None = os.getenv("PROVIDER_API_KEY") or os.getenv("COHERE_API_KEY")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.default_model: str = os.getenv("DEFAULT_MODEL", "command-r-plus")
        self.log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = os.getenv("LOG_LEVEL", "INFO")

        # Configure logging level after initialization
        logging.getLogger().setLevel(getattr(logging, self.log_level))
        logger.info("settings.loaded", extra={
            "port": self.port,
            "default_model": self.default_model,
            "log_level": self.log_level,
            "has_api_key": bool(self.provider_api_key)
        })
        if not self.provider_api_key:
            logger.warning("settings.missing_api_key", extra={"message": "PROVIDER_API_KEY is not set; provider calls will fail."})


settings = Settings()
