# Production Deployment Evidence

This document is the reviewer checklist for the production closure work.

## Fresh Docker/Compose Setup

Build and start the production-like stack:

```bash
docker compose up --build -d
```

Services:

- PostgreSQL with pgvector: `localhost:5433`
- FastAPI: `http://localhost:8001` by default
- Prometheus: `http://localhost:9090`

Health checks:

```bash
curl http://localhost:8001/health
curl http://localhost:8001/ready
curl http://localhost:8001/metrics
docker compose ps
```

Bootstrap the databases after a fresh start:

```bash
python -m services.database.init_db
python -m scripts.init_catalogue_v3_db
python -m scripts.apply_catalogue_v3_operational_schema
python -m scripts.sync_catalogue_v3_master_ingredients
python -m scripts.backfill_catalogue_v3_ingredient_embeddings
```

## Prometheus Evidence

Prometheus scrape config:

```text
monitoring/prometheus/prometheus.yml
```

## PagerDuty/System Failure Alerting

Set one or both alert targets:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_ROUTING_KEY=...
```

The dispatcher triggers when at least 5 critical validation failures occur in
60 minutes. The threshold and window are configurable:

```bash
CRITICAL_FAILURE_ALERT_THRESHOLD=5
CRITICAL_FAILURE_WINDOW_MINUTES=60
```

## Scheduled Automated Pipeline Proof

Run the scheduled job proof:

```bash
python -m scripts.run_catalogue_v3_scheduled_job \
  --source-id swasthi_recipes_index_web \
  --allow-disabled \
  --max-items 1 \
  --max-pages 5 \
  --max-depth 1 \
  --source-timeout-seconds 60
```

For a no-network proof run:

```bash
python -m scripts.run_catalogue_v3_scheduled_job \
  --source-id swasthi_recipes_index_web \
  --allow-disabled \
  --skip-scrape \
  --skip-nutrition \
  --dry-run \
  --no-track-runs
```

The latest proof artifact is written to:

```text
evidence/scheduled_catalogue_v3_run_latest.json
```

Register the Windows scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_windows_catalogue_v3_schedule.ps1
```

The task runs `scripts.run_catalogue_v3_scheduled_job` daily and writes the
same evidence JSON file after each run.

## Backup/Export Process

Create a database backup:

```bash
python -m scripts.backup_catalogue_v3 --output-dir backups
```

Dry-run the backup command:

```bash
python -m scripts.backup_catalogue_v3 --dry-run
```

Reviewer CSV export:

```bash
python -m scripts.export_catalogue_v3_reviewer_format
```

## Curator Alias Workflow

When a reviewer corrects an unresolved ingredient, write it back:

```bash
python -m scripts.curator_alias_writeback \
  --canonical-name dry_mango_powder \
  --alias-name amchoor \
  --language hi \
  --corrected-by reviewer@example.com
```

Then rerun:

```bash
python -m scripts.resolve_catalogue_v3_ingredients
```

The same raw alias now resolves through:

```text
resolution_tier = exact_alias
resolution_method = database_alias
```

The DB-backed proof script applies several real curator corrections and writes
the proof artifact:

```bash
python -m scripts.run_catalogue_v3_curator_workflow_proof
```

Output:

```text
evidence/catalogue_v3_curator_workflow_latest.json
```

## Multi-Source Evidence

Generate source coverage evidence from the v3 catalogue:

```bash
python -m scripts.catalogue_v3_multisource_evidence_report
```

Output:

```text
evidence/catalogue_v3_multisource_evidence_latest.json
```
