import logging
from typing import List

from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {
    "INTERNAL_TOKEN": "internal-secret-change-me",
}


class Settings(BaseSettings):
    DATABASE_URL: str = "monitoring.db"
    GATEWAY_URL: str = "http://localhost:8080"
    SCHEDULER_URL: str = "http://localhost:8001"
    NODE_URLS: str = ""          # comma-separated, e.g. "http://localhost:8003"
    SCRAPE_INTERVAL_S: int = 15
    INTERNAL_TOKEN: str = "internal-secret-change-me"
    PORT: int = 8002

    def node_url_list(self) -> List[str]:
        if not self.NODE_URLS:
            return []
        return [u.strip() for u in self.NODE_URLS.split(",") if u.strip()]

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
