## Pull requests

Never run `git push` or `gh pr create` directly.
To push and open a PR, commit your work, then run this from the root of this repo:

```bash
bash scripts/claude-pr.sh <work-item-id> <base-branch> --title "<title>" --body-file <file>
```

The script always creates a new branch named after the work item (e.g. `WI-001234`) and opens
the PR from it. It stops if that branch already exists.

Always ask the developer for the work item id and the base branch before running the script.
Never guess or assume either one. Common bases: `staging` for features, `version-15` for hotfixes.

Write the PR body to a temporary file first and pass it with `--body-file`.
If the repo has a `pull_request_template.md`, follow its structure.
