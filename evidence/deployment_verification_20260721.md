# Deployment Verification - 2026-07-21

## Verified

- `docker compose config` completed successfully and rendered the full stack:
  PostgreSQL with pgvector, FastAPI, Prometheus, and Grafana.
- `docker compose build api --progress plain` completed successfully.
- `docker compose up -d` completed successfully after moving the host API
  port to `8001`.
- `docker compose ps` showed all services running:
  `recipe_postgres`, `recipe_api`, `recipe_prometheus`, and
  `recipe_grafana`.
- `http://localhost:8001/health` returned `status=ok`.
- `http://localhost:8001/ready` returned `status=ready` with both database
  checks passing.
- `http://localhost:8001/metrics` returned the required Prometheus metrics,
  including `records_ingested_total`, `ingredient_resolution_rate`,
  `validation_acceptance_rate`, and `dead_letter_rate`.
- `http://localhost:9090/-/healthy` returned `Prometheus Server is Healthy.`
- `http://localhost:3001/api/health` returned Grafana `database=ok`.
- `python -m scripts.backup_catalogue_v3 --dry-run` completed and produced
  the expected `pg_dump` command.
- `python -m scripts.run_catalogue_v3_scheduled_job --source-id swasthi_recipes_index_web --allow-disabled --skip-scrape --skip-nutrition --dry-run --no-track-runs --max-items 1 --validation-limit 100000`
  completed and wrote `evidence/scheduled_catalogue_v3_run_latest.json`.
- `python -m pytest` completed with `143 passed`.
- Windows Task Scheduler task `ShopConnect Catalogue V3 Pipeline` was
  registered and triggered once.
- The scheduled proof run completed with `LastTaskResult = 0` and wrote
  `evidence/scheduled_catalogue_v3_run_latest.json` at
  `2026-07-21 10:36:07`.

## Issues Found And Fixed

- Docker Desktop was initially not running. It was started and `docker info`
  then succeeded.
- Docker build initially failed because `.pytest_cache` was unreadable in the
  Docker build context. Added `.dockerignore`.
- Docker API startup initially failed because host port `8000` was already
  allocated. Compose now publishes the API on `8001` by default.
- Docker DB bootstrap exposed idempotency issues:
  - duplicate `recipe_embeddings.recipe_id` rows could block unique-index
    creation
  - older `recipe_steps.step_id` columns did not match the newer
    `recipe_step_id` view contract
- Both migration issues are now fixed in `db/schemas/05_embeddings.sql` and
  `db/schemas/06_recipe_steps.sql`.

## Current Runtime Commands

The working runtime proof commands are:

```bash
docker compose build api --progress plain
docker compose up -d
curl http://localhost:8001/health
curl http://localhost:8001/ready
curl http://localhost:8001/metrics
curl http://localhost:9090/-/healthy
curl http://localhost:3001/api/health
docker compose ps
```
