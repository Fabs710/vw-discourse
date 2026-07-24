# GitHub setup

Kept private until after grading (per supervisor).

## One-time
**With GitHub CLI (`gh`) installed - easiest:**
```
./push.sh "first commit"
```
This inits the repo, creates a PRIVATE repo named `vw-discourse`, and pushes.

**Without `gh`:**
1. Create a new PRIVATE repo named `vw-discourse` on github.com (no README).
2. In the project folder (Git Bash):
```
git init && git branch -M main
git add -A && git commit -m "first commit"
git remote add origin https://github.com/Fabs710/vw-discourse.git
git push -u origin main
```

## Every time after
```
./push.sh "what changed"     # macOS / Linux / Git Bash
push.bat  "what changed"     # Windows cmd
```
Stages everything, commits, and pushes to `main`.

## Notes
- `.env` (API keys) and everything under `data/` (run outputs) are gitignored and never pushed.
- Prefer running the project from a local copy rather than inside the OneDrive-synced folder;
  OneDrive and a live `.git` can corrupt each other during heavy edits.
