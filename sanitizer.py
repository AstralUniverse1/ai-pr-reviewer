from __future__ import annotations

import json
import re

from config import MAX_INPUT_CHARS
from review_contract import SanitizedReviewInput

DEFAULT_REVIEW_RULES = [
    "Use only the provided sanitized input.",
    "Do not assume hidden files or runtime state.",
    "Do not request secrets.",
    "Prioritize missing tests, edge cases, validation issues, auth risks, and regressions.",
]

SECRET_PATTERNS = [
    re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^'\"\s]+"
    ),
]

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_FILE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")


def sanitize_review_input(
    *,
    project_context: str,
    pr_summary: str,
    changed_files: list[str],
    diff: str,
    rules: list[str] | None = None,
) -> SanitizedReviewInput:
    sanitized = SanitizedReviewInput(
        project_context=_clean_text(project_context),
        pr_summary=_clean_text(pr_summary),
        changed_files=_clean_changed_files(changed_files),
        diff=_clean_text(diff),
        rules=_clean_rules(rules or DEFAULT_REVIEW_RULES),
    )
    _enforce_size_limit(sanitized)
    return sanitized


def render_review_input(review_input: SanitizedReviewInput) -> str:
    return json.dumps(review_input.to_model_payload(), indent=2, sort_keys=True)


def _clean_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("review input fields must be strings")

    cleaned = CONTROL_CHARS.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned.strip()


def _clean_changed_files(changed_files: list[str]) -> list[str]:
    if not isinstance(changed_files, list):
        raise TypeError("changed_files must be a list of strings")

    result = []
    seen = set()
    for path in changed_files:
        cleaned = _clean_text(path)
        if not cleaned or cleaned in seen:
            continue
        if cleaned.startswith("/") or ".." in cleaned.split("/"):
            continue
        if not SAFE_FILE_PATH.match(cleaned):
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _clean_rules(rules: list[str]) -> list[str]:
    if not isinstance(rules, list):
        raise TypeError("rules must be a list of strings")
    return [_clean_text(rule) for rule in rules if _clean_text(rule)]


def _enforce_size_limit(review_input: SanitizedReviewInput) -> None:
    payload = render_review_input(review_input)
    if len(payload) > MAX_INPUT_CHARS:
        raise ValueError(
            f"sanitized review input is {len(payload)} chars; limit is {MAX_INPUT_CHARS}"
        )
