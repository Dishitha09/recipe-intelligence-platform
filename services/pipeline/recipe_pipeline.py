from services.ingestion.csv_adapter import CSVAdapter

from services.enrichment.recipe_enricher import RecipeEnricher

from services.preprocessing.schema_coercer import SchemaCoercer

from services.validation.validation_engine import ValidationEngine

from services.database.recipe_loader import RecipeLoader


class RecipePipeline:

    def __init__(self, loader=None, enricher=None):

        self.validator = ValidationEngine()

        self.loader = loader

        self.enricher = enricher or RecipeEnricher()

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
        }

        for raw_record in raw_records:

            coercion_result = self.schema_coercer.coerce(raw_record)

            if coercion_result.status != "accepted":
                summary["dead_letter"].append(
                    coercion_result.dead_letter
                )
                continue

            summary["coerced"] += 1
            recipe = coercion_result.recipe
            recipe = self.enricher.enrich_recipe(recipe)
            summary["enriched"] += 1

            validation_report = self.validator.validate(recipe)

            if validation_report.status == "REJECTED":
                summary["rejected"] += 1
                summary["dead_letter"].append(
                    self.validator.dead_letter_payload(
                        recipe,
                        validation_report,
                    )
                )
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
                continue

            summary["accepted"] += 1

            loader = self._get_loader()

            recipe_id = loader.insert_recipe(

                recipe

            )


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
