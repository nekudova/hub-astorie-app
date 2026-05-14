from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HUB"
    database_url: str
    secret_key: str
    brand_primary: str = "#003D4C"
    brand_secondary: str = "#FC4C02"
    support_email: str = "nekudova@astorieas.cz"
    support_phone: str = "737 233 888"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
