from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # FIRMS / Map
    MAP_KEY: Optional[str] = Field(default=None, alias="MAP_KEY")
    SOURCE: str = Field(default="VIIRS_SNPP_NRT", alias="SOURCE")
    IZMIR_BBOX: str = Field(default="26.0,37.5,28.5,39.5", alias="IZMIR_BBOX")

    # Weather
    OPEN_METEO_BASE: str = Field(default="https://api.open-meteo.com/v1/forecast", alias="OPEN_METEO_BASE")
    TZ: str = Field(default="Europe/Istanbul", alias="TZ")

    # JWT
    SECRET_KEY: str = Field(default="koru-super-secret-key-please-change", alias="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")


settings = Settings()
