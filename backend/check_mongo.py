from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient

from pymongo import MongoClient

from config import Settings


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