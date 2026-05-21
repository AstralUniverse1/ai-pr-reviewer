import json
import unittest

from review_contract import ChangedFile
from sanitizer import render_review_input, sanitize_review_input


class SanitizerTests(unittest.TestCase):
    def test_preserves_modified_file_metadata(self):
        result = sanitize_review_input(
            project_context="ctx",
            pr_summary="summary",
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ change",
        )

        self.assertEqual(result.changed_files, [ChangedFile(path="app.py", status="modified")])

    def test_preserves_renamed_file_metadata(self):
        result = sanitize_review_input(
            project_context="ctx",
            pr_summary="summary",
            changed_files=[
                ChangedFile(path="new.py", status="renamed", old_path="legacy.py")
            ],
            diff="+ change",
        )

        self.assertEqual(
            result.changed_files,
            [ChangedFile(path="new.py", status="renamed", old_path="legacy.py")],
        )

    def test_preserves_binary_file_metadata(self):
        result = sanitize_review_input(
            project_context="ctx",
            pr_summary="summary",
            changed_files=[
                ChangedFile(path="image.png", status="modified", is_binary=True)
            ],
            diff="",
        )

        self.assertTrue(result.changed_files[0].is_binary)

    def test_filters_unsafe_paths(self):
        result = sanitize_review_input(
            project_context="ctx",
            pr_summary="summary",
            changed_files=[
                ChangedFile(path="../secret.py", status="modified"),
                ChangedFile(path="/abs.py", status="modified"),
                ChangedFile(path="safe.py", status="modified"),
            ],
            diff="+ token=abc123",
        )

        self.assertEqual(result.changed_files, [ChangedFile(path="safe.py", status="modified")])

    def test_render_outputs_json_friendly_metadata(self):
        result = sanitize_review_input(
            project_context="ctx api_key=secret",
            pr_summary="summary",
            changed_files=[ChangedFile(path="app.py", status="modified")],
            diff="+ token=abc123",
        )

        payload = json.loads(render_review_input(result))
        self.assertEqual(
            payload["changed_files"],
            [
                {
                    "path": "app.py",
                    "status": "modified",
                    "old_path": None,
                    "is_binary": False,
                }
            ],
        )
        self.assertEqual(payload["project_context"], "ctx [REDACTED]")
        self.assertEqual(payload["diff"], "+ [REDACTED]")


if __name__ == "__main__":
    unittest.main()
