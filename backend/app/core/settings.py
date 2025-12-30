from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Banco local (arquivo). Para distribuir a ferramenta, isso é o ideal.
    database_url: str = "sqlite:///./calculadora_reforma.db"

    backend_cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
