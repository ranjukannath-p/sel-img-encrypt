from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    APP_MASTER_KEY_HEX: str = "00"*32  # 32 bytes hex for AES-256
    STORAGE_DIR: str = "./data"
    ALLOW_ORIGINS: str = "*"

settings = Settings()
