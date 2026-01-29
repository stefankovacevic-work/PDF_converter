@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   PDF AND IMAGE CONVERTER BUILDER
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
    echo Ensure 'poppler' folder is in the same directory.
    pause
    exit /b
)

:: --- 3. Clean & Install Dependencies ---
echo [STEP] Cleaning and Installing Dependencies...
if exist venv rmdir /s /q venv
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

python -m venv venv
call venv\Scripts\activate

:: Install standard + new requirements (pillow-heif, tkinterdnd2)
echo [INFO] Installing libraries...
pip install customtkinter pdf2image img2pdf pyinstaller pillow packaging tkinterdnd2 pillow-heif

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

:: --- 5. Build EXE ---
echo [STEP] Building PDF and Image Converter...
:: --collect-all is CRITICAL for tkinterdnd2 to work in an EXE
pyinstaller --noconfirm --onefile --noconsole --clean ^
    --name "PDF_and_Image_Converter" ^
    --add-binary "%POPPLER_DIR%;poppler_bin" ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    --collect-all pillow_heif ^
    %ICON_FLAG% ^
    %DATA_FLAG% ^
    "main.py"

if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b
)

:: --- 6. Finalize & Cleanup ---
echo [STEP] Cleaning up workspace...
set "ARTIFACTS_DIR=Build_Artifacts"
set "EXE_NAME=PDF_and_Image_Converter.exe"

:: 1. Move the final App to the Source Folder (Root)
if exist "dist\%EXE_NAME%" (
    move /Y "dist\%EXE_NAME%" ".\" >nul
    echo [SUCCESS] %EXE_NAME% is now ready in this folder.
) else (
    echo [WARN] Could not find the EXE to move!
)

:: 2. Create the Storage Folder for temp files
if exist "%ARTIFACTS_DIR%" rmdir /s /q "%ARTIFACTS_DIR%"
mkdir "%ARTIFACTS_DIR%"

:: 3. Move the messy folders into storage
echo [INFO] Archiving build files...
if exist "venv" move "venv" "%ARTIFACTS_DIR%\" >nul
if exist "build" move "build" "%ARTIFACTS_DIR%\" >nul
if exist "dist" move "dist" "%ARTIFACTS_DIR%\" >nul
if exist "*.spec" move "*.spec" "%ARTIFACTS_DIR%\" >nul
if exist "icon.ico" move "icon.ico" "%ARTIFACTS_DIR%\" >nul

echo.
echo ========================================================
echo [SUCCESS] Build Complete!
echo You can now run "PDF_and_Image_Converter.exe"
echo ========================================================
pause