from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    APP_ENV: str = Field(default="development", alias="APP_ENV")
    HOST: str = Field(default="0.0.0.0", alias="HOST")
    PORT: int = Field(default=8000, alias="PORT")
    BACKEND_CORS_ORIGINS: str = Field(default="*", alias="BACKEND_CORS_ORIGINS")

    # Database
    DATABASE_URL: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # PostgreSQL container info
    POSTGRES_USER: str = Field(default="koru", alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="koru123", alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="koru_db", alias="POSTGRES_DB")
    POSTGRES_HOST: str = Field(default="db", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, alias="POSTGRES_PORT")

    # FIRMS / Map
    MAP_KEY: Optional[str] = Field(default=None, alias="MAP_KEY")
    SOURCE: str = Field(default="VIIRS_SNPP_NRT", alias="SOURCE")
    IZMIR_BBOX: str = Field(default="26.0,37.5,28.5,39.5", alias="IZMIR_BBOX")

    # Weather
    OPEN_METEO_BASE: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        alias="OPEN_METEO_BASE"
    )
    TZ: str = Field(default="Europe/Istanbul", alias="TZ")

    # JWT
    SECRET_KEY: str = Field(
        default="please-change-me",
        alias="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        raw_value = (self.BACKEND_CORS_ORIGINS or "*").strip()
        if raw_value == "*":
            return ["*"]
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


settings = Settings()