@echo off
setlocal
set REPO_NAME=vw-discourse
set MSG=%~1
if "%MSG%"=="" set MSG=update
if not exist ".git" ( git init & git branch -M main )
git add -A
git commit -m "%MSG%"
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo No 'origin' remote set. Create a PRIVATE repo %REPO_NAME% on github.com, then run:
  echo   git remote add origin https://github.com/Fabs710/%REPO_NAME%.git
  echo   push.bat "first commit"
  goto :eof
)
git push -u origin main
echo Pushed to origin/main.
