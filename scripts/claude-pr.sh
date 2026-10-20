#!/usr/bin/env bash
# Pushes the current commit to a new branch named after the work item and opens a PR
# from it as the developer's Claude bot app.
# Usage: bash scripts/claude-pr.sh <work-item-id> <base-branch> [gh pr create flags, e.g. --title ... --body-file ...]
#   e.g. bash scripts/claude-pr.sh WI-001234 staging --title "..." --body-file /tmp/pr.md
# Needs: gh, jq, the gh-token extension, and CLAUDE_APP_ID, CLAUDE_INSTALL_ID,
# CLAUDE_APP_KEY (path to the app's .pem file) set in the environment.
set -euo pipefail

USAGE="Usage: bash scripts/claude-pr.sh <work-item-id> <base-branch> [gh pr create flags]"
WI="${1:?$USAGE}"
BASE="${2:?$USAGE}"
shift 2

if ! [[ "$WI" =~ ^WI-[0-9]{6}$ ]]; then
  echo "Work item id must look like WI-001234 (got '$WI')." >&2
  exit 1
fi

if [ $# -eq 0 ]; then
  set -- --title "$(git log -1 --pretty=%s)" --body "$(git log -1 --pretty=%b)"
fi

TOKEN=$(gh token generate --app-id "$CLAUDE_APP_ID" \
  --installation-id "$CLAUDE_INSTALL_ID" \
  --key "$CLAUDE_APP_KEY" | jq -re .token)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

if ! GH_TOKEN="$TOKEN" gh api "repos/$REPO/branches/$BASE" --silent; then
  echo "Base branch '$BASE' does not exist on $REPO." >&2
  exit 1
fi
if GH_TOKEN="$TOKEN" gh api "repos/$REPO/branches/$WI" --silent 2>/dev/null; then
  echo "Branch '$WI' already exists on $REPO. The bot only creates new branches." >&2
  exit 1
fi

git push "https://x-access-token:${TOKEN}@github.com/${REPO}.git" "HEAD:refs/heads/${WI}"
GH_TOKEN="$TOKEN" gh pr create --base "$BASE" --head "$WI" "$@"
