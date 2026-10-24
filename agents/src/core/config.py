from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    agents_database_url: str
    # 1C lives on the same connection as the rest of the app - no separate
    # ONEC_DATABASE_URL/TATWIR_DATABASE_URL var needed or read anymore.
    onec_database_url: str = Field(validation_alias="database_url")
    allowed_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
