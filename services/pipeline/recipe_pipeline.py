import logging

from services.ingestion.csv_adapter import CSVAdapter

from services.enrichment.recipe_enricher import RecipeEnricher

from services.preprocessing.schema_coercer import SchemaCoercer

from services.validation.validation_engine import ValidationEngine

from services.database.recipe_loader import RecipeLoader
from services.database.ingestion_run_repository import IngestionRunRepository
from services.database.validation_repository import ValidationRepository


logger = logging.getLogger(__name__)


class RecipePipeline:

    def __init__(
        self,
        loader=None,
        enricher=None,
        validation_repository=None,
        persist_validation=True,
        run_repository=None,
        track_runs=True,
    ):

        self.validator = ValidationEngine()

        self.loader = loader

        self.enricher = enricher or RecipeEnricher()
        self.validation_repository = validation_repository
        self.persist_validation = persist_validation
        self.run_repository = run_repository
        self.track_runs = track_runs

        self.schema_coercer = SchemaCoercer.from_mapping_file(
            "configs/source_field_mappings.json"
        )


    def run_csv_pipeline(self, file_path, source_id="csv.default", source_name=None):


        adapter = CSVAdapter(file_path, source_id=source_id)

        raw_records = adapter.extract()

        return self.run_records(
            raw_records,
            source_id=source_id,
            source_name=source_name or file_path,
            source_type=adapter.source_type,
        )

    def run_records(
        self,
        raw_records,
        source_id=None,
        source_name=None,
        source_type=None,
    ):

        summary = {
            "records_found": len(raw_records),
            "coerced": 0,
            "enriched": 0,
            "accepted": 0,
            "review": 0,
            "loaded": 0,
            "rejected": 0,
            "dead_letter": [],
            "review_queue": [],
            "validation_errors": [],
            "validation_reports": [],
            "ingestion_run_id": None,
        }

        source_id = source_id or (
            raw_records[0].source_id if raw_records else "unknown.source"
        )
        source_name = source_name or source_id
        source_type = source_type or (
            raw_records[0].source_type if raw_records else None
        )
        run_id = self._start_run(source_id, source_name, source_type)
        summary["ingestion_run_id"] = run_id

        try:
            for raw_record in raw_records:

                coercion_result = self.schema_coercer.coerce(raw_record)

                if coercion_result.status != "accepted":
                    summary["dead_letter"].append(
                        coercion_result.dead_letter
                    )
                    self._save_dead_letter(
                        source_type=raw_record.source_type,
                        record_id=raw_record.record_id,
                        raw_payload=coercion_result.dead_letter,
                        error_message=coercion_result.dead_letter.get(
                            "error",
                            "Schema coercion failed",
                        ),
                    )
                    continue

                summary["coerced"] += 1
                recipe = coercion_result.recipe
                recipe = self.enricher.enrich_recipe(recipe)
                summary["enriched"] += 1

                validation_report = self.validator.validate(recipe)

                if validation_report.status == "REJECTED":
                    summary["rejected"] += 1
                    dead_letter_payload = self.validator.dead_letter_payload(
                        recipe,
                        validation_report,
                    )
                    summary["dead_letter"].append(dead_letter_payload)
                    summary["validation_errors"].append(
                        {
                            "record_id": raw_record.record_id,
                            "status": validation_report.status,
                            "errors": [
                                result.model_dump()
                                for result in validation_report
                                if not result.passed
                            ],
                        }
                    )
                    self._save_dead_letter(
                        source_type=raw_record.source_type,
                        record_id=raw_record.record_id,
                        raw_payload=dead_letter_payload,
                        error_message="Validation rejected recipe",
                        validation_report=validation_report.model_dump(
                            mode="json"
                        ),
                    )
                    continue

                if validation_report.status == "REVIEW":
                    summary["review"] += 1
                    summary["review_queue"].append(
                        {
                            "record_id": raw_record.record_id,
                            "recipe": recipe.model_dump(),
                            "validation_report": validation_report.model_dump(),
                        }
                    )
                    review_id = self._save_review(
                        raw_record.record_id,
                        recipe,
                        validation_report,
                    )
                    if review_id is not None:
                        summary["review_queue"][-1]["review_id"] = review_id
                    continue

                summary["accepted"] += 1

                loader = self._get_loader()

                recipe_id = loader.insert_recipe(

                    recipe

                )

                validation_id = self._save_validation_report(
                    recipe_id,
                    validation_report,
                )
                if validation_id is not None:
                    summary["validation_reports"].append(validation_id)


                loader.insert_ingredients(

                    recipe_id,

                    recipe.ingredients

                )


                loader.insert_steps(

                    recipe_id,

                    recipe.steps

                )

                loader.record_source(
                    recipe_id=recipe_id,
                    recipe=recipe,
                    source_name=raw_record.source_id,
                    source_type=raw_record.source_type,
                    run_id=run_id,
                )

                summary["loaded"] += 1

                logger.info("Inserted Recipe ID: %s", recipe_id)

            self._complete_run(run_id, summary)
        except Exception as exc:
            self._fail_run(run_id, exc, summary)
            raise

        return summary

    def _get_loader(self):
        if self.loader is None:
            self.loader = RecipeLoader()

        return self.loader

    def _get_validation_repository(self):
        if not self.persist_validation:
            return None

        if self.validation_repository is None:
            self.validation_repository = ValidationRepository()

        return self.validation_repository

    def _get_run_repository(self):
        if not self.track_runs:
            return None

        if self.run_repository is None:
            self.run_repository = IngestionRunRepository()

        return self.run_repository

    def _start_run(self, source_id, source_name, source_type):
        repository = self._get_run_repository()

        if repository is None:
            return None

        return repository.start_run(
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
        )

    def _complete_run(self, run_id, summary):
        repository = self._get_run_repository()

        if repository is None:
            return None

        return repository.complete_run(run_id, summary)

    def _fail_run(self, run_id, error, summary):
        repository = self._get_run_repository()

        if repository is None:
            return None

        return repository.fail_run(run_id, error, summary)

    def _save_validation_report(self, recipe_id, validation_report):
        repository = self._get_validation_repository()

        if repository is None:
            return None

        return repository.save_report(recipe_id, validation_report)

    def _save_review(self, record_id, recipe, validation_report):
        repository = self._get_validation_repository()

        if repository is None:
            return None

        return repository.save_review(
            record_id,
            recipe,
            validation_report,
        )

    def _save_dead_letter(
        self,
        source_type,
        record_id,
        raw_payload,
        error_message,
        validation_report=None,
    ):
        repository = self._get_validation_repository()

        if repository is None:
            return None

        return repository.save_dead_letter(
            source_type=source_type,
            record_id=record_id,
            raw_payload=raw_payload,
            error_message=error_message,
            validation_report=validation_report,
        )
