from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient

from app.core.config import Settings


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
