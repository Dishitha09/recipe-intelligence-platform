import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy import text

from services.database.connection import engine
from services.ingestion.audio_adapter import AudioAdapter
from services.ingestion.csv_adapter import CSVAdapter
from services.ingestion.dataset_adapter import DatasetAdapter
from services.ingestion.image_adapter import ImageAdapter
from services.ingestion.pdf_adapter import PDFAdapter
from services.ingestion.text_adapter import TextAdapter
from services.ingestion.youtube_adapter import YouTubeAdapter
from services.preprocessing.schema_coercer import SchemaCoercer
from services.preprocessing.schema_registry import SchemaRegistry
from services.reports.acceptance_report import build_report
from services.reports.ingredient_resolution_report import build_report as build_ingredient_report


def generate(output_dir="evidence"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = {
        "01_adapter_test_report.json": adapter_test_report(),
        "02_schema_coercion_report.json": schema_coercion_report(),
        "03_ingredient_resolution_report.json": build_ingredient_report(),
        "04_uom_acceptance_report.json": uom_acceptance_report(),
        "05_validation_acceptance_report.json": validation_acceptance_report(),
        "06_pipeline_acceptance_report.json": build_report(),
    }

    for name, payload in reports.items():
        write_json(output_dir / name, payload)

    pytest_report = pytest_collect_report()
    (output_dir / "07_pytest_report.txt").write_text(
        pytest_report,
        encoding="utf-8",
    )
    (output_dir / "08_known_limitations.md").write_text(
        known_limitations(),
        encoding="utf-8",
    )

    return {
        "output_dir": str(output_dir),
        "files": sorted(path.name for path in output_dir.iterdir()),
    }


def adapter_test_report():
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        recipe_text = (
            "Title: Evidence Masala Rice\n"
            "Ingredients:\n"
            "rice\nsalt\n"
            "Instructions:\n"
            "Wash rice.\nCook until tender.\n"
        )

        csv_path = tmp_path / "recipes.csv"
        csv_path.write_text(
            "title,ingredients,instructions,source_url\n"
            '"Evidence Masala Rice","rice | salt","Wash rice. | Cook rice.","https://example.com/evidence"\n',
            encoding="utf-8",
        )
        text_path = tmp_path / "recipe.txt"
        text_path.write_text(recipe_text, encoding="utf-8")
        pdf_path = tmp_path / "recipe.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n% evidence placeholder\n")
        sidecar_path = tmp_path / "recipe.sidecar.txt"
        sidecar_path.write_text(recipe_text, encoding="utf-8")
        audio_path = tmp_path / "recipe.mp3"
        audio_path.write_bytes(b"ID3")
        image_path = tmp_path / "recipe.png"
        _write_png(image_path)

        adapter_specs = [
            ("csv", CSVAdapter(str(csv_path), source_id="csv.evidence")),
            (
                "dataset",
                DatasetAdapter(str(csv_path), source_id="dataset.evidence"),
            ),
            ("text", TextAdapter(str(text_path), source_id="text.evidence")),
            (
                "pdf",
                PDFAdapter(
                    str(pdf_path),
                    source_id="pdf.evidence",
                    config={"text_path": str(sidecar_path)},
                ),
            ),
            (
                "audio",
                AudioAdapter(
                    str(audio_path),
                    source_id="audio.evidence",
                    config={"transcript_path": str(sidecar_path)},
                ),
            ),
            (
                "image",
                ImageAdapter(
                    str(image_path),
                    source_id="image.evidence",
                    config={"ocr_text_path": str(sidecar_path)},
                ),
            ),
            (
                "youtube",
                YouTubeAdapter(
                    "evidence-video",
                    source_id="youtube.evidence",
                    config={"transcript_path": str(sidecar_path)},
                ),
            ),
        ]

        for source_type, adapter in adapter_specs:
            try:
                records = adapter.extract()
                results.append(
                    {
                        "source_type": source_type,
                        "status": "PASS",
                        "record_count": len(records),
                        "record_id_present": all(
                            bool(record.record_id) for record in records
                        ),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "source_type": source_type,
                        "status": "FAIL",
                        "error": str(exc),
                    }
                )

    return {
        "required_adapter_types": [
            "csv",
            "dataset",
            "text",
            "pdf",
            "audio",
            "image",
            "youtube",
        ],
        "results": results,
        "passed": all(result["status"] == "PASS" for result in results),
    }


def schema_coercion_report():
    coercer = SchemaCoercer.from_mapping_file("configs/source_field_mappings.json")
    registry = SchemaRegistry()
    adapter_result = adapter_test_report()
    accepted = 0
    dead_letter = 0
    schema_errors = []

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "recipe.csv"
        path.write_text(
            "title,ingredients,instructions,source_url\n"
            '"Evidence Sambar","dal | tamarind","Boil dal. | Simmer with tamarind.","https://example.com/sambar"\n',
            encoding="utf-8",
        )
        records = CSVAdapter(str(path), source_id="csv.evidence").extract()

        for record in records:
            result = coercer.coerce(record)

            if result.status == "accepted":
                accepted += 1
                schema_result = registry.validate(
                    result.recipe.model_dump(mode="json")
                )

                if not schema_result["valid"]:
                    schema_errors.extend(schema_result["errors"])
            else:
                dead_letter += 1

    return {
        "accepted": accepted,
        "dead_letter": dead_letter,
        "schema_version": "v1",
        "schema_errors": schema_errors,
        "adapter_report_passed": adapter_result["passed"],
        "passed": accepted > 0 and dead_letter == 0 and not schema_errors,
    }


def uom_acceptance_report():
    with engine.connect() as conn:
        invalid_units = scalar(
            conn,
            """
            SELECT count(*)
            FROM recipe_ingredients
            WHERE canonical_unit IS NOT NULL
              AND canonical_unit NOT IN ('g', 'ml', 'tsp', 'tbsp', 'cup', 'count')
            """,
        )
        density_rows = scalar(
            conn,
            """
            SELECT count(*)
            FROM master_ingredients
            WHERE density_g_per_ml IS NOT NULL
            """,
        )

    reference_path = Path("data/reference/top_200_ingredient_density.csv")
    reference_rows = 0

    if reference_path.exists():
        reference_rows = max(0, len(reference_path.read_text().splitlines()) - 1)

    return {
        "canonical_units": ["g", "ml", "tsp", "tbsp", "cup", "count"],
        "invalid_canonical_unit_rows": invalid_units,
        "db_density_rows": density_rows,
        "reference_density_rows": reference_rows,
        "top_200_density_reference_present": reference_rows >= 200,
        "passed": invalid_units == 0 and reference_rows >= 200,
    }


def validation_acceptance_report():
    with engine.connect() as conn:
        reports = scalar(conn, "SELECT count(*) FROM validation_reports")
        accepted = scalar(
            conn,
            "SELECT count(*) FROM validation_reports WHERE status = 'ACCEPTED'",
        )
        critical = scalar(
            conn,
            """
            SELECT count(*)
            FROM validation_reports
            WHERE recipe_id IS NOT NULL
              AND failure_codes ?| ARRAY['V01', 'V02', 'V03', 'V09']
            """,
        )

    rate = round(float(accepted) / float(reports), 4) if reports else 0.0

    return {
        "validation_reports": reports,
        "accepted_validation_reports": accepted,
        "validation_acceptance_rate": rate,
        "critical_catalogue_failures": critical,
        "passed": rate >= 0.85 and critical == 0,
    }


def pytest_collect_report():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr + f"\nexit_code={result.returncode}\n"


def known_limitations():
    return """# Known Limitations

- RAG modules are present but out of scope for PS-1 to PS-5.
- External production sources are disabled by default to avoid unapproved live
  crawling from a fresh checkout.
- Audio, PDF, image, and YouTube adapters support deterministic sidecar
  fallbacks; full Whisper/scanned-PDF OCR production services require external
  binaries or credentials.
- The current embedding model is 384-dimensional (`all-MiniLM-L6-v2`). The
  problem statement mentions 768 dimensions; this implementation uses the
  deployed 384-dimensional model consistently across schema, loaders, and tests.
- Top-200 ingredient density provenance is not complete yet. UOM normalization
  enforces the canonical unit set, but production density coverage still needs a
  curated `data/reference/top_200_ingredient_density.csv` with source
  provenance before PS-4 can be called fully production-complete.
"""


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar() or 0


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )


def _write_png(path):
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe"
        b"\x02\xfeA\xcd\xcc\xb3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    path.write_bytes(png_bytes)


def main():
    parser = argparse.ArgumentParser(
        description="Generate review evidence for PS-1 to PS-5."
    )
    parser.add_argument("--output-dir", default="evidence")
    args = parser.parse_args()

    print(json.dumps(generate(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
