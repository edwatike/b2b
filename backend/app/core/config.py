from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/b2b"
    REDIS_BROKER: str = "redis://redis:6379"

    class Config:
        env_file = ".env"

settings = Settings()
