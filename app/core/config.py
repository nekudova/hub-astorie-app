from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HUB"
    database_url: str
    secret_key: str
    brand_primary: str = "#003D4C"
    brand_secondary: str = "#FC4C02"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
