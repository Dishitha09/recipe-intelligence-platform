import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")


def backup_catalogue_v3(output_dir=Path("backups"), dry_run=False):
    database_url = _pg_dump_url(os.getenv("CATALOGUE_V3_DATABASE_URL"))

    if not database_url:
        raise RuntimeError("CATALOGUE_V3_DATABASE_URL is not configured")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"recipe_catalogue_v3_{timestamp}.dump"
    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(backup_path),
        database_url,
    ]

    if dry_run:
        return {
            "status": "dry_run",
            "backup_path": str(backup_path),
            "command": command,
        }

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "pg_dump failed")

    manifest_path = backup_path.with_suffix(".json")
    manifest = {
        "status": "completed",
        "database": "recipe_catalogue_v3",
        "backup_path": str(backup_path),
        "created_at": timestamp,
        "bytes": backup_path.stat().st_size,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def _pg_dump_url(database_url):
    if not database_url:
        return database_url

    return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)


def main():
    parser = argparse.ArgumentParser(
        description="Create a pg_dump backup for recipe_catalogue_v3."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        json.dumps(
            backup_catalogue_v3(
                output_dir=args.output_dir,
                dry_run=args.dry_run,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
