from pydantic import BaseModel, Field
from typing import Any, Dict, List

from services.validation.severity import Severity


class ValidationResult(BaseModel):

    passed: bool

    severity: Severity

    message: str

    check_id: str = "LEGACY"

    check_name: str = "Legacy Check"

    action: str = "WARN"

    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):

    status: str

    check_results: List[ValidationResult]

    flags: List[str] = Field(default_factory=list)

    summary: Dict[str, Any] = Field(default_factory=dict)

    def __iter__(self):
        return iter(self.check_results)

    def __len__(self):
        return len(self.check_results)

    def __getitem__(self, index):
        return self.check_results[index]
