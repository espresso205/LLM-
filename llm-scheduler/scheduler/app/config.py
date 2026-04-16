import logging
from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {
    "INTERNAL_TOKEN": "internal-secret-change-me",
}


class Settings(BaseSettings):
    DATABASE_URL: str = "scheduler.db"
    HEARTBEAT_TIMEOUT_S: int = 30
    DEFAULT_STRATEGY: str = "round_robin"
    INTERNAL_TOKEN: str = "internal-secret-change-me"
    PORT: int = 8001

    model_config = {"env_file": ".env", "extra": "ignore"}

    def warn_insecure(self) -> None:
        for key, default in _INSECURE_DEFAULTS.items():
            if getattr(self, key, None) == default:
                logging.getLogger(__name__).warning(
                    f"SECURITY WARNING: {key} is using the insecure default value. "
                    f"Change it via environment variable or .env file."
                )


settings = Settings()
settings.warn_insecure()
