#!/usr/bin/env bash
# One-command push for vw-discourse.
#   First run : inits the repo and (if the GitHub CLI 'gh' is installed) creates
#               a PRIVATE repo and pushes. Otherwise prints the remote command.
#   Later runs: stages everything, commits, and pushes to main.
# Usage: ./push.sh "your commit message"
set -e
REPO_NAME="vw-discourse"
MSG="${1:-update}"

if [ ! -d .git ]; then
  git init -q
  git branch -M main
fi

git add -A
git commit -q -m "$MSG" || echo "(nothing new to commit)"

if ! git remote | grep -q '^origin$'; then
  if command -v gh >/dev/null 2>&1; then
    gh repo create "$REPO_NAME" --private --source=. --remote=origin
  else
    echo ""
    echo "No 'origin' remote set, and GitHub CLI (gh) was not found."
    echo "Create a PRIVATE repo named '$REPO_NAME' on github.com (no README), then run:"
    echo "  git remote add origin https://github.com/Fabs710/$REPO_NAME.git"
    echo "  ./push.sh \"first commit\""
    exit 0
  fi
fi

git push -u origin main
echo "Pushed to origin/main."
