#!/usr/bin/env bash
# Pushes the current branch and opens a PR as the developer's Claude bot app.
# Usage: bash scripts/claude-pr.sh <base-branch>   (e.g. staging or version-15)
set -e

BASE="$1"
if [ -z "$BASE" ]; then
  echo "Usage: bash scripts/claude-pr.sh <base-branch>  (e.g. staging or version-15)" >&2
  exit 1
fi
if ! git ls-remote --exit-code --heads origin "$BASE" >/dev/null; then
  echo "Base branch '$BASE' does not exist on origin." >&2
  exit 1
fi

TOKEN=$(gh token generate --app-id "$CLAUDE_APP_ID" \
  --installation-id "$CLAUDE_INSTALL_ID" \
  --key "$CLAUDE_APP_KEY" | jq -r .token)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
BRANCH=$(git branch --show-current)

git push "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "$BRANCH"
GH_TOKEN="$TOKEN" gh pr create --fill --base "$BASE"
