import os
import sys
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import logger


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    DATABASE_URL: str
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev_secret_key_placeholder_change_in_production_min_32_chars"
    UPLOAD_DIR: str = "uploads"
    SEED_DEFAULT_PASSWORD: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ALGORITHM: str = "HS256"


    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        cleaned = v.strip() if v else ""
        if not cleaned:
            raise ValueError(
                "DATABASE_URL cannot be empty. Please configure a valid PostgreSQL connection string."
            )
        return cleaned

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        origins = [item.strip() for item in v.split(",") if item.strip()]
        if "*" in origins:
            raise ValueError(
                "Wildcard '*' is not permitted in CORS_ORIGINS for security reasons. "
                "Specify explicit origin domains (e.g., http://localhost:5173)."
            )
        return v

    @model_validator(mode="after")
    def validate_secret_key_security(self) -> "Settings":
        """Enforce strict cryptographic secret standards in production while permitting dev overrides."""
        placeholders = [
            "dev_secret_key_placeholder",
            "change_in_production",
            "secret",
            "changeme",
        ]
        is_placeholder = any(p in self.SECRET_KEY.lower() for p in placeholders)
        too_short = len(self.SECRET_KEY.strip()) < 32

        if self.is_production:
            if is_placeholder or too_short:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production environment (APP_ENV=production), "
                    "SECRET_KEY must be a cryptographically secure random string of at least 32 characters, "
                    "and cannot be a default/placeholder value."
                )
        else:
            if is_placeholder or too_short:
                logger.warning(
                    "[SECURITY WARNING] Using a placeholder or short SECRET_KEY in development environment. "
                    "Ensure a strong, unique >=32 character SECRET_KEY is configured before deploying to production."
                )
        return self


    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS_ORIGINS string into a list of cleaned origin strings."""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.APP_ENV.strip().lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings with fast-fail on missing required configurations."""
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:
        sys.stderr.write(
            "\n" + "=" * 80 + "\n"
            "[CRITICAL CONFIGURATION ERROR] Application failed to start due to invalid or missing configuration.\n"
            f"Details: {exc}\n"
            "Please ensure backend/.env exists and contains DATABASE_URL.\n"
            "Example: DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sparehub_dev\n"
            + "=" * 80 + "\n\n"
        )
        sys.stderr.flush()
        raise SystemExit(1) from exc
