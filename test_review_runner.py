import unittest
from unittest.mock import patch

from git_diff import GitDiffResult
from review_contract import ChangedFile, ReviewOutput
from review_runner import dry_run_for_diff, run_review_for_diff


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


if __name__ == "__main__":
    unittest.main()
