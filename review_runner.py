from __future__ import annotations

from git_diff import GitDiffResult, get_local_working_tree_diff
from review_contract import ReviewOutput, SanitizedReviewInput
from sanitizer import sanitize_review_input


def build_sanitized_input_for_diff(
    diff_result: GitDiffResult,
    project_context: str,
    pr_summary: str,
) -> SanitizedReviewInput:
    return sanitize_review_input(
        project_context=project_context,
        pr_summary=pr_summary,
        changed_files=diff_result.changed_files,
        diff=diff_result.diff,
    )


def run_review_for_diff(
    diff_result: GitDiffResult,
    project_context: str,
    pr_summary: str,
    prompt_name: str = "qa_review",
) -> ReviewOutput:
    sanitized_input = build_sanitized_input_for_diff(
        diff_result=diff_result,
        project_context=project_context,
        pr_summary=pr_summary,
    )
    return _call_llm(prompt_name, sanitized_input)


def run_local_review(
    repo_path: str,
    project_context: str,
    pr_summary: str,
    prompt_name: str = "qa_review",
) -> ReviewOutput:
    diff_result = get_local_working_tree_diff(repo_path)
    return run_review_for_diff(
        diff_result=diff_result,
        project_context=project_context,
        pr_summary=pr_summary,
        prompt_name=prompt_name,
    )


def dry_run_for_diff(
    diff_result: GitDiffResult,
    project_context: str,
    pr_summary: str,
) -> SanitizedReviewInput:
    return build_sanitized_input_for_diff(
        diff_result=diff_result,
        project_context=project_context,
        pr_summary=pr_summary,
    )


def dry_run_local(
    repo_path: str,
    project_context: str,
    pr_summary: str,
) -> SanitizedReviewInput:
    diff_result = get_local_working_tree_diff(repo_path)
    return dry_run_for_diff(
        diff_result=diff_result,
        project_context=project_context,
        pr_summary=pr_summary,
    )


def _call_llm(prompt_name: str, sanitized_input: SanitizedReviewInput) -> ReviewOutput:
    from llm_client import call_llm

    return call_llm(prompt_name, sanitized_input)
