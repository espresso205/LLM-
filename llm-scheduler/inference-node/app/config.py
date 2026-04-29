import logging
from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {
    "INTERNAL_TOKEN": "internal-secret-change-me",
}


class Settings(BaseSettings):
    NODE_ID: str = "node-1"
    NODE_HOST: str = "localhost"
    NODE_PORT: int = 8003
    VLLM_URL: str = "http://localhost:8000"
    SCHEDULER_URL: str = "http://localhost:8001"
    MONITORING_URL: str = "http://localhost:8002"
    DATABASE_URL: str = "node.db"
    HEARTBEAT_INTERVAL_S: int = 3
    INTERNAL_TOKEN: str = "internal-secret-change-me"

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
