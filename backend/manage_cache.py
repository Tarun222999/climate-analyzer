"""Operator CLI. Invalidation previews by default; stop the API before --apply."""
import argparse
import json

from pydantic import ValidationError
from pymongo.errors import PyMongoError

from config import Settings
from database import create_mongo_client
from maintenance import invalidate_cache, storage_report
from models import Location


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("storage", help="Read configured database storage usage")
    invalidate = commands.add_parser("invalidate", help="Preview scoped cache invalidation")
    invalidate.add_argument("--kind", choices=("analyses", "baseline", "weather"), required=True)
    invalidate.add_argument("--latitude", type=float, required=True)
    invalidate.add_argument("--longitude", type=float, required=True)
    invalidate.add_argument("--timezone", required=True)
    invalidate.add_argument("--year", type=int)
    invalidate.add_argument("--apply", action="store_true", help="Delete matching caches; stop API first")
    args = parser.parse_args()
    try:
        # Validate the scope before opening a database connection.
        location = None
        if args.command == "invalidate":
            location = Location(name="Cache maintenance", latitude=args.latitude,
                                longitude=args.longitude, timezone=args.timezone)
            from maintenance import invalidation_plan
            invalidation_plan(location, args.kind, args.year)
        settings = Settings()
        with create_mongo_client(settings) as mongo:
            db = mongo[settings.mongodb_db_name]
            report = (storage_report(db, settings.storage_budget_bytes) if args.command == "storage"
                      else invalidate_cache(db, location, args.kind, args.year, args.apply))
            print(json.dumps(report, indent=2))
        return 0
    except (PyMongoError, ValidationError, ValueError) as exc:
        print(f"Cache maintenance failed: {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
