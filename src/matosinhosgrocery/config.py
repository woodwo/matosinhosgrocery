from typing import List, Optional, Union, Any

from pydantic import (
    field_validator,
    AnyHttpUrl,
    PostgresDsn,
    RedisDsn,
    Field,
    model_validator,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # populate_by_name=True # Not strictly needed here as we use validation_alias
    )

    # Core application settings
    APP_NAME: str = "Matosinhos Grocery Bot"
    DEBUG: bool = False

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str

    # This field captures the TELEGRAM_ALLOWED_USER_IDS env var as a raw string.
    # `validation_alias` maps the environment variable name to this field.
    # Pydantic will load the value of "TELEGRAM_ALLOWED_USER_IDS" from .env into this field.
    ENV_TELEGRAM_ALLOWED_USER_IDS: Optional[str] = Field(
        default=None, validation_alias="TELEGRAM_ALLOWED_USER_IDS"
    )

    # Database Configuration
    # Example for SQLite: "sqlite+aiosqlite:///./matosinhosgrocery.db"
    # Example for PostgreSQL: "postgresql+asyncpg://user:pass@host:port/db"
    DATABASE_URL: str = "sqlite+aiosqlite:///./matosinhosgrocery.db"

    # OpenAI API Configuration
    OPENAI_API_KEY: Optional[str] = None

    # Google Drive API Configuration
    GOOGLE_DRIVE_CREDENTIALS_PATH: Optional[
        str
    ] = None  # Path to the JSON credentials file
    GOOGLE_DRIVE_FOLDER_ID: Optional[
        str
    ] = None  # Optional: Specific folder ID to store receipts

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    @computed_field  # type: ignore[misc] # Decorator for property_name can't be inferred by some linters
    @property
    def TELEGRAM_ALLOWED_USER_IDS(self) -> List[int]:
        """Parses the comma-separated string from env into a list of integers."""
        raw_str = self.ENV_TELEGRAM_ALLOWED_USER_IDS  # Access the string field
        if raw_str and raw_str.strip():
            try:
                return [int(id_val.strip()) for id_val in raw_str.split(",")]
            except ValueError as e:
                # It's good practice to log this error as well
                # import logging; logging.getLogger(__name__).error(...)
                raise ValueError(
                    f"Invalid format for TELEGRAM_ALLOWED_USER_IDS environment variable: '{raw_str}'. "
                    f"Must be a comma-separated list of integers."
                ) from e
        return []  # Default to an empty list if the env var is not set or is empty

    # Removed the validator for DATABASE_URL as its type is now just str with a default.
    # If Union[PostgresDsn, str] is still desired, the validator would need to be adjusted
    # or pydantic-extra-types used for more robust DSN parsing if not from env.


settings = Settings()
