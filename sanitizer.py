from __future__ import annotations

import json
import re

from config import MAX_INPUT_CHARS
from review_contract import ChangedFile, FileStatus, SanitizedReviewInput

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
    changed_files: list[ChangedFile],
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


def _clean_changed_files(changed_files: list[ChangedFile]) -> list[ChangedFile]:
    if not isinstance(changed_files, list):
        raise TypeError("changed_files must be a list of ChangedFile objects")

    result = []
    seen = set()
    for changed_file in changed_files:
        if not isinstance(changed_file, ChangedFile):
            raise TypeError("changed_files must contain ChangedFile objects")

        cleaned_path = _clean_path(changed_file.path)
        if not cleaned_path or cleaned_path in seen:
            continue

        cleaned_old_path = None
        if changed_file.old_path is not None:
            cleaned_old_path = _clean_path(changed_file.old_path)
            if cleaned_old_path is None:
                continue

        status = _clean_status(changed_file.status)
        is_binary = bool(changed_file.is_binary)
        result.append(
            ChangedFile(
                path=cleaned_path,
                status=status,
                old_path=cleaned_old_path,
                is_binary=is_binary,
            )
        )
        seen.add(cleaned_path)
    return result


def _clean_path(path: str) -> str | None:
    cleaned = _clean_text(path)
    if not cleaned:
        return None
    if cleaned.startswith("/") or ".." in cleaned.split("/"):
        return None
    if not SAFE_FILE_PATH.match(cleaned):
        return None
    return cleaned


def _clean_status(status: str) -> FileStatus:
    allowed = {
        "added",
        "modified",
        "deleted",
        "renamed",
        "copied",
        "type_changed",
        "unmerged",
        "unknown",
    }
    if status not in allowed:
        return "unknown"
    return status


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
