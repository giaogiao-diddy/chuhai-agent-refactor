from typing import Literal

from pydantic import BaseModel, model_validator


class ReportAuditResult(BaseModel):
    passed: bool
    issues: list[str]
    rewrite_required: bool
    severity: Literal["pass", "warning", "fail"]

    @model_validator(mode="after")
    def _check_consistency(self) -> "ReportAuditResult":
        if self.severity == "pass" and (not self.passed or self.rewrite_required):
            raise ValueError("severity=pass 要求 passed=True 且 rewrite_required=False")
        if self.severity == "warning" and self.rewrite_required:
            raise ValueError("severity=warning 不允许 rewrite_required=True")
        if self.severity == "fail" and (self.passed or not self.rewrite_required):
            raise ValueError("severity=fail 要求 passed=False 且 rewrite_required=True")
        return self
