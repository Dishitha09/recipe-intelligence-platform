from pydantic import BaseModel

from services.validation.severity import Severity


class ValidationResult(BaseModel):

    passed: bool

    severity: Severity

    message: str