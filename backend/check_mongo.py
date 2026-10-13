from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient


class Settings(BaseSettings):
    mongodb_uri: SecretStr
    mongodb_db_name: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        extra="ignore",
    )


if __name__ == "__main__":
    try:
        settings = Settings()
        with MongoClient(
            settings.mongodb_uri.get_secret_value(),
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        ) as client:
            client.admin.command("ping")
        print("MongoDB connection verified")
    except Exception as error:
        print(f"Connection failed: {type(error).__name__}")
        raise SystemExit(1)