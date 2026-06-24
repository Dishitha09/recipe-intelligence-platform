from services.ingestion.csv_adapter import CSVAdapter

from services.enrichment.recipe_enricher import RecipeEnricher

from services.preprocessing.schema_coercer import SchemaCoercer

from services.validation.validation_engine import ValidationEngine

from services.database.recipe_loader import RecipeLoader
from services.database.validation_repository import ValidationRepository


class RecipePipeline:

    def __init__(
        self,
        loader=None,
        enricher=None,
        validation_repository=None,
        persist_validation=True,
    ):

        self.validator = ValidationEngine()

        self.loader = loader

        self.enricher = enricher or RecipeEnricher()
        self.validation_repository = validation_repository
        self.persist_validation = persist_validation

        self.schema_coercer = SchemaCoercer.from_mapping_file(
            "configs/source_field_mappings.json"
        )


    def run_csv_pipeline(self, file_path):


        adapter = CSVAdapter(file_path)

        raw_records = adapter.extract()

        summary = {
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
        }

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

            summary["loaded"] += 1

            print(

                f"Inserted Recipe ID : {recipe_id}"

            )

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
