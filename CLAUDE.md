## Pull requests

Never run `git push` or `gh pr create` directly. Commit your work, then run the script
below from the root of this repo.

Before running it, always ask the developer for the work item id and the base branch.
Never guess or assume either one. Common bases: `staging` for features, `version-15` for hotfixes.

**New PR**

```bash
bash scripts/claude-pr.sh <work-item-id> <base-branch> --title "<title>" --body-file <file>
```

This creates a new branch named after the work item (e.g. `WI-001234`) and opens the PR from it.
Write the PR body to a temporary file first. If the repo has a `pull_request_template.md`,
follow its structure.

**Follow-up commits to an existing PR**

If the script says the branch already exists, ask the developer whether to add the commits
to that PR. Only if they approve, run:

```bash
bash scripts/claude-pr.sh --update <work-item-id> <base-branch>
```

This only works when the open PR was opened by the developer's own bot. It never force-pushes.
