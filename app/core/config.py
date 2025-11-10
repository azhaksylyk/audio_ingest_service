from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@db:5432/app"
    storage_dir: str = "/data/storage"
    tmp_dir: str = "/data/tmp"


    model_config = SettingsConfigDict(
        env_prefix="",      
        env_file=".env",    
    )


settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
Path(settings.tmp_dir).mkdir(parents=True, exist_ok=True)