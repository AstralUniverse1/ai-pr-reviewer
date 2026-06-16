# AI PR Reviewer

Secure AI-assisted GitHub PR reviewer built around external LLM isolation and comment-only GitHub writes.

## Why this exists

AI review is useful, but a pull request is hostile input. The dangerous design is not "AI writes a comment"; it is letting an external LLM act inside the repository environment with repo access, shell access, filesystem access, secrets, network/tool access, or autonomous permissions.

This project keeps the external LLM outside that boundary. The trusted GitHub Actions runner collects PR metadata and a diff, reduces them to sanitized bounded input, sends that data packet to OpenAI, validates the structured response locally, and then posts a deterministic PR comment. The model does not get a checkout, a shell, the filesystem, credentials, tools, or control over the workflow.

## What it does

Runtime flow:

```text
GitHub PR
  -> GitHub Actions trusted workflow
  -> collect PR metadata and diff
  -> sanitize and limit input
  -> call external OpenAI model with strict schema
  -> validate output locally
  -> post deterministic PR comment
```

The reviewer supports initial PR reviews and stateless follow-up reviews triggered by `/ai-reviewer` comments.

## Architecture

```text
Target repository workflow
  checkout trusted base branch
  fetch PR head as diff data
  fetch pinned ai-pr-reviewer SHA into $RUNNER_TEMP
  run main.py
      |
      v
  review_runner.py
      |-- github_context.py    reads GitHub event/API metadata
      |-- git_diff.py          builds the base...head diff
      |-- sanitizer.py         redacts, normalizes, classifies, and caps input
      |-- llm_client.py        sends one structured request to the external LLM
      |-- output_validator.py  enforces local output limits
      |-- github_commenter.py  formats and posts one PR comment
```

## Security model

- The external LLM receives sanitized review input only.
- The external LLM has no repository, shell, filesystem, network, secret, or tool access inside the runner.
- Initial PR review workflows should use `pull_request_target` so the executed workflow code comes from the trusted base branch.
- PR head content is used only as diff data.
- LLM calls are capped at one per process run by `MAX_CALLS_PER_RUN = 1`.
- There are no autonomous retry loops or agentic tool loops.
- Model output must match a strict JSON schema and is then validated locally.
- GitHub writes are comment-only: the tool posts issue comments on pull requests.
- Follow-up reviews skip bot-authored trigger comments to prevent bot loops.
- Repository-local project rules are passed as guidance, not as system instructions.

## Main components

- `main.py`: CLI entry point for local, GitHub, dry-run, and follow-up modes.
- `review_runner.py`: Orchestrates context loading, diff collection, sanitization, model call, and comment posting.
- `git_diff.py`: Collects local or ref-based git diffs and changed-file metadata with command output caps.
- `github_context.py`: Reads GitHub Actions event payloads and PR metadata.
- `sanitizer.py`: Cleans text, redacts likely secrets, classifies changed files, truncates large inputs, and builds the model payload.
- `llm_client.py`: Calls the OpenAI Responses API with the configured model and strict output schema.
- `output_validator.py`: Parses and validates model JSON before any GitHub comment is created.
- `github_commenter.py`: Formats deterministic Markdown, escapes unsafe text, caps comment size, and posts PR comments.
- `review_contract.py`: Defines shared dataclasses and the review output JSON schema.

## Features

- Initial PR review from GitHub Actions.
- `/ai-reviewer` follow-up review from PR comments.
- Repository-local project rules from `.ai-pr-reviewer.md` and `.github/ai-pr-reviewer.md`.
- Sanitized diff and PR context before model input.
- Deterministic Markdown PR comments.
- Bot-loop prevention for follow-up comments.

## Install in a target repository

Use this repository as an external, pinned tool from the target repository's trusted GitHub Actions workflow. Do not vendor a copy of the reviewer into every repository.

Pin the reviewer to a full 40-character commit SHA. Tags such as `v0.1.0` are useful release labels for humans, but the workflow should execute the exact commit SHA reviewed and approved for the target repository.

The target workflow must keep the existing security model:

- Use `pull_request_target` for initial PR reviews.
- Use `issue_comment` only for `/ai-reviewer` follow-up comments on pull requests.
- Check out the trusted base branch of the target repository.
- Fetch the pull request head only as diff data.
- Fetch this reviewer repository into `$RUNNER_TEMP` at the pinned SHA.
- Run `main.py` from the fetched reviewer repository with `--repo-path` pointing at the target repository checkout.
- Keep project-specific guidance in the target repository, for example `.ai-pr-reviewer.md`.

Minimal fetch pattern:

```yaml
env:
  AI_PR_REVIEWER_REPO: AstralUniverse1/ai-pr-reviewer
  AI_PR_REVIEWER_SHA: "<full-40-character-sha>"

steps:
  - name: Checkout trusted target repo code
    uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.base.ref || github.event.repository.default_branch }}
      fetch-depth: 0

  - name: Fetch PR head for diff only
    run: git fetch --no-tags origin "pull/${{ github.event.pull_request.number || github.event.issue.number }}/head:refs/remotes/origin/pr-head"

  - name: Fetch pinned AI reviewer
    run: |
      REVIEWER_DIR="$RUNNER_TEMP/ai-pr-reviewer"
      git init "$REVIEWER_DIR"
      git -C "$REVIEWER_DIR" remote add origin "https://github.com/${AI_PR_REVIEWER_REPO}.git"
      git -C "$REVIEWER_DIR" fetch --depth=1 origin "$AI_PR_REVIEWER_SHA"
      git -C "$REVIEWER_DIR" checkout --detach FETCH_HEAD
      test "$(git -C "$REVIEWER_DIR" rev-parse HEAD)" = "$AI_PR_REVIEWER_SHA"

  - name: Install reviewer dependencies
    run: python -m pip install -r "$RUNNER_TEMP/ai-pr-reviewer/requirements.txt"

  - name: Run reviewer
    run: >-
      python "$RUNNER_TEMP/ai-pr-reviewer/main.py"
      --github
      --repo-path "$GITHUB_WORKSPACE"
      --project-context "$PROJECT_CONTEXT"
      --pr-summary "$PR_SUMMARY"
```

For follow-up comments, add `--follow-up`.

## Release process

1. Ensure the working tree is clean except for intentional release changes.
2. Run `python3 -m unittest discover -s . -p 'test_*.py'`.
3. Commit and push the release changes.
4. Create an annotated tag, for example `v0.1.0`.
5. Push the tag.
6. Publish the full commit SHA in the release notes and target-repository workflow examples.

Target repositories should upgrade by inspecting the diff from the old pinned SHA to the new pinned SHA, then updating `AI_PR_REVIEWER_SHA`.
