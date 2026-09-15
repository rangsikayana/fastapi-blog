from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # Defines app settings
    model_config = SettingsConfigDict(  # Auto loads .env
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Field names map .env variable names, case-insensitive
    secret_key: SecretStr  # Masks value in logs, errors, prints
    algorithm: str = "HS256"  # Default algorithm, standard for JWT
    access_token_expire_minutes: int = 30


settings = Settings()  # Loads .env when settings is imported
