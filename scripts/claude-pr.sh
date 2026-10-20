#!/usr/bin/env bash
# Pushes the current branch and opens a PR as the developer's Claude bot app.
# Usage: bash scripts/claude-pr.sh <base-branch> [gh pr create flags, e.g. --title ... --body-file ...]
# Needs: gh, jq, the gh-token extension, and CLAUDE_APP_ID, CLAUDE_INSTALL_ID,
# CLAUDE_APP_KEY (path to the app's .pem file) set in the environment.
set -euo pipefail

BASE="${1:?Usage: bash scripts/claude-pr.sh <base-branch> [gh pr create flags]}"
shift
if [ $# -eq 0 ]; then set -- --fill; fi

BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ] || [ "$BRANCH" = "$BASE" ]; then
  echo "Check out a feature branch first (current: '${BRANCH:-detached}')." >&2
  exit 1
fi

TOKEN=$(gh token generate --app-id "$CLAUDE_APP_ID" \
  --installation-id "$CLAUDE_INSTALL_ID" \
  --key "$CLAUDE_APP_KEY" | jq -re .token)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

if ! GH_TOKEN="$TOKEN" gh api "repos/$REPO/branches/$BASE" --silent; then
  echo "Base branch '$BASE' does not exist on $REPO." >&2
  exit 1
fi

git push "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "$BRANCH"
GH_TOKEN="$TOKEN" gh pr create --base "$BASE" --head "$BRANCH" "$@"
