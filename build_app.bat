@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   PRIORITY TIRE PDF TOOL BUILDER (PRO VERSION)
echo ========================================================

:: --- 1. Python Check ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not detected.
    pause
    exit /b
)

:: --- 2. Poppler Check ---
set "POPPLER_DIR="
if exist "poppler\Library\bin\pdftoppm.exe" (
    set "POPPLER_DIR=poppler\Library\bin"
) else if exist "poppler\bin\pdftoppm.exe" (
    set "POPPLER_DIR=poppler\bin"
)

if "%POPPLER_DIR%"=="" (
    echo [ERROR] Poppler structure incorrect!
    pause
    exit /b
)

:: --- 3. Clean & Install ---
echo [STEP] Cleaning and Installing...
if exist venv rmdir /s /q venv
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

python -m venv venv
call venv\Scripts\activate
:: Added tkinterdnd2 for Drag-and-Drop support
pip install customtkinter pdf2image img2pdf pyinstaller pillow packaging tkinterdnd2

:: --- 4. Auto-Generate Icon ---
echo [STEP] Checking Icon...
if exist "logo.png" (
    python make_icon.py
)

set "ICON_FLAG="
set "DATA_FLAG="
if exist "icon.ico" (
    set "ICON_FLAG=--icon=icon.ico"
    :: This adds the icon to the internal EXE data
    set "DATA_FLAG=--add-data "icon.ico;.""
)

:: --- 5. Build ---
echo [STEP] Building PriorityTire Converter...
:: Added --collect-all tkinterdnd2 to ensure drag-and-drop works in EXE
pyinstaller --noconfirm --onefile --noconsole --clean ^
    --name "PriorityTire_PDF_Converter" ^
    --add-binary "%POPPLER_DIR%;poppler_bin" ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    %ICON_FLAG% ^
    %DATA_FLAG% ^
    "main.py"

if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b
)
:: ... (Place this after the PyInstaller command and error check) ...

:: ... (Paste this AFTER the "if %errorlevel% neq 0" check) ...

:: --- 6. Finalize & Clean Up ---
echo [STEP] Cleaning up workspace...
set "ARTIFACTS_DIR=Build_Artifacts"
set "EXE_NAME=PriorityTire_PDF_Converter.exe"

:: 1. Move the final App to the Source Folder (Root)
if exist "dist\%EXE_NAME%" (
    move /Y "dist\%EXE_NAME%" ".\" >nul
    echo [SUCCESS] %EXE_NAME% is now in your Source folder.
) else (
    echo [WARN] Could not find the EXE to move!
)

:: 2. Create the Storage Folder for junk files
if exist "%ARTIFACTS_DIR%" rmdir /s /q "%ARTIFACTS_DIR%"
mkdir "%ARTIFACTS_DIR%"

:: 3. Move the messy folders/files into storage
echo [INFO] Moving venv, dist, build, and specs to %ARTIFACTS_DIR%...
if exist "venv" move "venv" "%ARTIFACTS_DIR%\" >nul
if exist "build" move "build" "%ARTIFACTS_DIR%\" >nul
if exist "dist" move "dist" "%ARTIFACTS_DIR%\" >nul
if exist "*.spec" move "*.spec" "%ARTIFACTS_DIR%\" >nul
if exist "icon.ico" move "icon.ico" "%ARTIFACTS_DIR%\" >nul

echo.
echo ========================================================
echo [SUCCESS] Build Complete! 
echo Your App is ready in this folder.
echo All build files have been moved to: \%ARTIFACTS_DIR%
echo ========================================================
pause

echo.
echo ========================================================
echo [SUCCESS] Build Complete!
echo The App Icon should now appear on the Window Titlebar too.
echo ========================================================
pause