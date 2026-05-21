from llm_client import call_llm
from sanitizer import sanitize_review_input

sample_input = sanitize_review_input(
    project_context="Flask banking API.",
    pr_summary="Added transfer-money endpoint validation.",
    changed_files=["backend/routes/transfer.py"],
    diff="""
+ reject negative transfer amounts
+ added insufficient funds validation
""",
)

result = call_llm("qa_review", sample_input)

print(result)
