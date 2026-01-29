@echo off
setlocal

echo ========================================================
echo   PRIORITY TIRE: ONE-CLICK GIT SETUP
echo ========================================================

:: --- 1. Check for Git ---
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed!
    pause
    exit /b
)

:: --- 2. Initialize & Ignore ---
echo [STEP] Initializing repository...
if not exist ".git" git init

echo [STEP] Creating smart .gitignore...
(
    echo __pycache__/
    echo *.py[cod]
    echo venv/
    echo env/
    echo build/
    echo dist/
    echo *.spec
    echo Build_Artifacts/
    echo PriorityTire_Release/
    echo .vscode/
    echo .idea/
    echo poppler/
) > .gitignore

:: --- 3. FIX: Ensure a Commit Exists ---
echo [STEP] Staging all files...
git add .

echo [STEP] Creating commit (Fixes 'refspec' error)...
:: This command might say "nothing to commit" if you ran it before, which is fine.
git commit -m "Full Project Upload: PriorityTire PDF Converter" >nul 2>&1

:: --- 4. Connect to GitHub ---
echo.
echo ========================================================
echo [INPUT REQUIRED]
echo Paste your GitHub Repository URL below.
echo (Example: https://github.com/YourUser/RepoName.git)
echo ========================================================
set /p REMOTE_URL="URL: "

if "%REMOTE_URL%"=="" (
    echo [ERROR] No URL provided.
    pause
    exit /b
)

:: --- 5. Push ---
echo [STEP] configuring remote...
git branch -M main
git remote remove origin >nul 2>&1
git remote add origin %REMOTE_URL%

echo [STEP] Pushing to GitHub...
git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed. 
    echo 1. Check your URL.
    echo 2. Check your internet.
    echo 3. Ensure the repo on GitHub is EMPTY.
) else (
    echo.
    echo [SUCCESS] Upload Complete!
)
pause