import unittest
from unittest.mock import patch

from git_diff import GitDiffResult
from github_context import GitHubPullRequestContext
from review_contract import ChangedFile, ReviewOutput
from review_runner import dry_run_for_diff, dry_run_github, run_github_review, run_review_for_diff


class ReviewRunnerTests(unittest.TestCase):
    def test_dry_run_for_diff_returns_sanitized_input_without_llm(self):
        diff_result = GitDiffResult(
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ api_key=secret",
            base_ref="HEAD",
            head_ref=None,
            mode="local",
        )

        result = dry_run_for_diff(diff_result, "ctx", "summary")

        self.assertEqual(result.changed_files, [ChangedFile(path="app.py", status="modified")])
        self.assertEqual(result.diff, "+ [REDACTED]")

    def test_run_review_for_diff_calls_llm_with_sanitized_input(self):
        diff_result = GitDiffResult(
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ token=abc123",
            base_ref="HEAD",
            head_ref=None,
            mode="local",
        )
        expected = ReviewOutput(summary="ok", findings=[], questions=[])

        with patch("review_runner._call_llm", return_value=expected) as call_llm:
            result = run_review_for_diff(diff_result, "ctx", "summary")

        self.assertEqual(result, expected)
        sanitized_input = call_llm.call_args.args[1]
        self.assertEqual(sanitized_input.diff, "+ [REDACTED]")

    def test_dry_run_github_uses_event_context_and_ref_diff(self):
        context = _github_context()
        diff_result = GitDiffResult(
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ password=secret",
            base_ref="base-sha",
            head_ref="head-sha",
            mode="refs",
        )

        with patch("review_runner.load_github_pull_request_context", return_value=context) as load_context:
            with patch("review_runner.get_ref_diff", return_value=diff_result) as get_ref_diff:
                result = dry_run_github(".", "ctx", "summary", env={"GITHUB_EVENT_NAME": "pull_request"})

        load_context.assert_called_once_with({"GITHUB_EVENT_NAME": "pull_request"})
        get_ref_diff.assert_called_once_with(base_ref="base-sha", head_ref="head-sha", repo_path=".")
        self.assertEqual(result.diff, "+ [REDACTED]")

    def test_run_github_review_posts_review_comment(self):
        context = _github_context()
        diff_result = GitDiffResult(
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ change",
            base_ref="base-sha",
            head_ref="head-sha",
            mode="refs",
        )
        review_output = ReviewOutput(summary="ok", findings=[], questions=[])

        with patch("review_runner.load_github_pull_request_context", return_value=context):
            with patch("review_runner.get_ref_diff", return_value=diff_result):
                with patch("review_runner._call_llm", return_value=review_output):
                    with patch("review_runner._post_review_comment", return_value={"id": 123}) as post_comment:
                        result = run_github_review(
                            repo_path=".",
                            project_context="ctx",
                            pr_summary="summary",
                            prompt_name="qa_review",
                            token="github-token",
                            env={"GITHUB_EVENT_NAME": "pull_request"},
                        )

        self.assertEqual(result, {"id": 123})
        post_comment.assert_called_once_with(
            owner="octo-org",
            repo="octo-repo",
            pr_number=42,
            review_output=review_output,
            token="github-token",
        )


def _github_context():
    return GitHubPullRequestContext(
        event_name="pull_request",
        event_path="/tmp/event.json",
        repo_owner="octo-org",
        repo_name="octo-repo",
        pr_number=42,
        base_ref="main",
        head_ref="feature",
        base_sha="base-sha",
        head_sha="head-sha",
    )


if __name__ == "__main__":
    unittest.main()
