## Pull requests

Never run `git push` or `gh pr create` directly.
To push and open a PR, run this from the root of this repo:

```bash
bash scripts/claude-pr.sh <base-branch>
```

Always ask the developer which base branch to use before running the script.
Never guess or assume it. Common bases: `staging` for features, `version-15` for hotfixes.
