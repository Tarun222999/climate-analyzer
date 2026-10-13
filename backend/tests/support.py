"""Test imports and non-secret defaults; no test connects to this URI."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "climate_analyzer_tests")

from copy import deepcopy
from threading import Lock


class MemoryDatabase:
    """Thread-safe document adapter for offline service integration tests."""
    def __init__(self):
        self.client = object()
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MemoryCollection(self, name)
        return self.collections[name]


class MemoryCollection:
    def __init__(self, database, name):
        self.database = database
        self.full_name = f"test.{name}"
        self.documents = []
        self.lock = Lock()

    @staticmethod
    def matches(document, query):
        for key, expected in query.items():
            value = document
            for part in key.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            if value != expected:
                return False
        return True

    def find_one(self, query, projection=None):
        with self.lock:
            return next((deepcopy(doc) for doc in self.documents if self.matches(doc, query)), None)

    def count_documents(self, query):
        with self.lock:
            return sum(self.matches(doc, query) for doc in self.documents)

    def replace_one(self, query, document, upsert=False):
        with self.lock:
            for i, doc in enumerate(self.documents):
                if self.matches(doc, query):
                    self.documents[i] = deepcopy(document)
                    return
            if upsert:
                self.documents.append(deepcopy(document))

    def update_one(self, query, update, upsert=False):
        with self.lock:
            if not any(self.matches(doc, query) for doc in self.documents) and upsert:
                self.documents.append(deepcopy(update["$setOnInsert"]))
