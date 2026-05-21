from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

FindingSeverity = Literal["critical", "high", "medium", "low"]


@dataclass(frozen=True)
class SanitizedReviewInput:
    project_context: str
    pr_summary: str
    changed_files: list[str]
    diff: str
    rules: list[str]

    def to_model_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewFinding:
    severity: FindingSeverity
    title: str
    detail: str
    recommendation: str
    file: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class ReviewOutput:
    summary: str
    findings: list[ReviewFinding]
    questions: list[str]


REVIEW_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "findings", "questions"],
    "properties": {
        "summary": {"type": "string", "maxLength": 600},
        "findings": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "severity",
                    "title",
                    "detail",
                    "recommendation",
                    "file",
                    "line",
                ],
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "title": {"type": "string", "maxLength": 140},
                    "detail": {"type": "string", "maxLength": 1200},
                    "recommendation": {"type": "string", "maxLength": 800},
                    "file": {"type": ["string", "null"], "maxLength": 260},
                    "line": {"type": ["integer", "null"], "minimum": 1},
                },
            },
        },
        "questions": {
            "type": "array",
            "maxItems": 3,
            "items": {"type": "string", "maxLength": 240},
        },
    },
}
