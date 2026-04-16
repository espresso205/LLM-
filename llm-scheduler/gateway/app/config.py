import logging
from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {
    "SECRET_KEY": "changeme-use-a-real-secret-in-production",
    "INTERNAL_TOKEN": "internal-secret-change-me",
    "ADMIN_PASSWORD": "admin123",
}


class Settings(BaseSettings):
    SCHEDULER_URL: str = "http://localhost:8001"
    MONITORING_URL: str = "http://localhost:8002"
    DATABASE_URL: str = "gateway.db"
    SECRET_KEY: str = "changeme-use-a-real-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    INTERNAL_TOKEN: str = "internal-secret-change-me"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    PORT: int = 8080

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
