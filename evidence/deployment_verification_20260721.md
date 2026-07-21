# Deployment Verification - 2026-07-21

## Verified

- `docker compose config` completed successfully and rendered the full stack:
  PostgreSQL with pgvector, FastAPI, Prometheus, and Grafana.
- `python -m scripts.backup_catalogue_v3 --dry-run` completed and produced
  the expected `pg_dump` command.
- `python -m scripts.run_catalogue_v3_scheduled_job --source-id swasthi_recipes_index_web --allow-disabled --skip-scrape --skip-nutrition --dry-run --no-track-runs --max-items 1 --validation-limit 100000`
  completed and wrote `evidence/scheduled_catalogue_v3_run_latest.json`.
- `python -m pytest` completed with `143 passed`.

## Blocked External Verification

`docker compose up --build -d` was attempted, but Docker Desktop was not
running on the workstation:

```text
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Once Docker Desktop is running, rerun:

```bash
docker compose up --build -d
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/metrics
docker compose ps
```
