import json
from pathlib import Path


class SchemaRegistry:
    def __init__(self, schema_root="configs/schemas"):
        self.schema_root = Path(schema_root)
        self._cache = {}

    def load(self, schema_name="recipe", version="v1"):
        key = (schema_name, version)

        if key not in self._cache:
            path = self.schema_root / schema_name / f"{version}.json"

            with path.open("r", encoding="utf-8") as handle:
                self._cache[key] = json.load(handle)

        return self._cache[key]

    def validate(self, payload, schema_name="recipe", version="v1"):
        schema = self.load(schema_name=schema_name, version=version)
        errors = []

        for field in schema.get("required", []):
            if field not in payload or payload[field] in (None, ""):
                errors.append(f"{field} is required")

        properties = schema.get("properties", {})

        for field, rules in properties.items():
            if field not in payload or payload[field] is None:
                continue

            expected = rules.get("type")

            if isinstance(expected, list):
                if any(
                    self._matches_type(payload[field], item)
                    for item in expected
                ):
                    continue
            elif self._matches_type(payload[field], expected):
                continue

            errors.append(f"{field} must be {expected}")

        return {
            "valid": not errors,
            "schema_name": schema_name,
            "schema_version": version,
            "errors": errors,
        }

    def _matches_type(self, value, expected):
        if expected == "string":
            return isinstance(value, str)

        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)

        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(
                value,
                bool,
            )

        if expected == "boolean":
            return isinstance(value, bool)

        if expected == "array":
            return isinstance(value, list)

        if expected == "object":
            return isinstance(value, dict)

        if expected == "null":
            return value is None

        return True
