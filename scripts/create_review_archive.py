from __future__ import annotations

import argparse
import fnmatch
import os
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_EXCLUDES = (
    ".git/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".venv/**",
    "venv/**",
    "env/**",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    ".env",
    "*.zip",
    "output/**",
    "backups/**",
    "data/datasets/catalogue_v3/*.partial.csv",
    "data/datasets/catalogue_v3/automated_runs/*.partial.csv",
    "data/datasets/catalogue_v3/automated_runs/*.log",
)


def _as_posix(path: Path) -> str:
    return path.as_posix()


def _is_excluded(relative_path: Path, patterns: tuple[str, ...]) -> bool:
    rel = _as_posix(relative_path)

    return any(
        fnmatch.fnmatch(rel, pattern)
        or fnmatch.fnmatch(relative_path.name, pattern)
        for pattern in patterns
    )


def create_archive(project_root: Path, output_path: Path) -> Path:
    excludes = DEFAULT_EXCLUDES
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(project_root.rglob("*")):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(project_root)

            if _is_excluded(relative_path, excludes):
                continue

            archive.write(file_path, arcname=_as_posix(relative_path))

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a reviewer-safe project archive.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output zip path. Defaults to ./output/review_archives/...",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = args.output or (
        project_root
        / "output"
        / "review_archives"
        / f"recipe-intelligence-platform-review-{timestamp}.zip"
    )

    archive_path = create_archive(project_root, output_path)
    print(archive_path)
    print(f"bytes={os.path.getsize(archive_path)}")


if __name__ == "__main__":
    main()
