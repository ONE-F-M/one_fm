#!/usr/bin/env bash
# Opens a PR as the developer's Claude bot app, or adds commits to a PR the bot already opened.
#
# New PR (creates a new branch named after the work item):
#   bash scripts/claude-pr.sh <work-item-id> <base-branch> [gh pr create flags, e.g. --title ... --body-file ...]
# Follow-up commits to an existing PR (only after the developer approves):
#   bash scripts/claude-pr.sh --update <work-item-id> <base-branch>
#
# Needs: gh, jq, the gh-token extension, and these environment variables:
#   CLAUDE_APP_ID, CLAUDE_INSTALL_ID, CLAUDE_APP_KEY (path to the app's .pem file),
#   CLAUDE_BOT_NAME (the app name, e.g. onefm-claude-abraham; used by --update)
set -euo pipefail

USAGE="Usage: bash scripts/claude-pr.sh [--update] <work-item-id> <base-branch> [gh pr create flags]"
UPDATE=0
if [ "${1:-}" = "--update" ]; then UPDATE=1; shift; fi
WI="${1:?$USAGE}"
BASE="${2:?$USAGE}"
shift 2

if ! [[ "$WI" =~ ^WI-[0-9]{6}$ ]]; then
  echo "Work item id must look like WI-001234 (got '$WI')." >&2
  exit 1
fi

TOKEN=$(gh token generate --app-id "$CLAUDE_APP_ID" \
  --installation-id "$CLAUDE_INSTALL_ID" \
  --key "$CLAUDE_APP_KEY" | jq -re .token)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PUSH_URL="https://x-access-token:${TOKEN}@github.com/${REPO}.git"

if ! GH_TOKEN="$TOKEN" gh api "repos/$REPO/branches/$BASE" --silent; then
  echo "Base branch '$BASE' does not exist on $REPO." >&2
  exit 1
fi

if GH_TOKEN="$TOKEN" gh api "repos/$REPO/branches/$WI" --silent 2>/dev/null; then
  # Branch exists: only add commits if the developer approved (--update) and the bot opened the PR.
  if [ "$UPDATE" -eq 0 ]; then
    echo "Branch '$WI' already exists on $REPO." >&2
    echo "Ask the developer whether to add these commits to it. Only if they approve, re-run with --update." >&2
    exit 1
  fi
  BOT="${CLAUDE_BOT_NAME:?Set CLAUDE_BOT_NAME to your app name, e.g. onefm-claude-abraham}[bot]"
  PR=$(GH_TOKEN="$TOKEN" gh api "repos/$REPO/pulls?head=${REPO%%/*}:$WI&base=$BASE&state=open" \
    | jq -c '.[0] // empty')
  if [ -z "$PR" ]; then
    echo "No open PR from '$WI' into '$BASE' on $REPO." >&2
    exit 1
  fi
  AUTHOR=$(jq -r '.user.login' <<<"$PR")
  if [ "$AUTHOR" != "$BOT" ]; then
    echo "The PR on '$WI' was opened by '$AUTHOR', not '$BOT'. Not adding commits." >&2
    exit 1
  fi
  git push "$PUSH_URL" "HEAD:refs/heads/${WI}"
  echo "Added commits to $(jq -r '.html_url' <<<"$PR")"
  exit 0
fi

if [ "$UPDATE" -eq 1 ]; then
  echo "Branch '$WI' does not exist on $REPO. Run without --update to open a new PR." >&2
  exit 1
fi

if [ $# -eq 0 ]; then
  set -- --title "$(git log -1 --pretty=%s)" --body "$(git log -1 --pretty=%b)"
fi

git push "$PUSH_URL" "HEAD:refs/heads/${WI}"
GH_TOKEN="$TOKEN" gh pr create --base "$BASE" --head "$WI" "$@"
