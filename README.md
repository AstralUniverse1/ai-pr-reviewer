# AI PR Reviewer

Comment-only AI-assisted GitHub PR reviewer.

This repository includes a smoke-test README so the GitHub Actions PR review workflow can be verified with a harmless docs-only pull request.

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
