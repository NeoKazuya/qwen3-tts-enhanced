@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo   Qwen3-TTS Enhanced - Installer
echo ============================================
echo.

:: Configuration
set "PYTHON_VERSION=3.12.8"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_SHA256=8D3F33BE9EB810F23C102F08475AF2854E50484B8E4E06275E937BE61CE3D2FB"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "PYTHON_DIR=%~dp0python"
set "VENV_DIR=%~dp0venv"

:: ========== STEP 1: Find or Download Python ==========
echo [1/4] Checking Python...

:: Check if we already have embedded Python
if exist "%PYTHON_DIR%\python.exe" (
    echo       Found embedded Python in .\python\
    set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
    goto :check_gpu
)

:: Check system Python version
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "SYS_PY_VER=%%v"
    for /f "tokens=1,2 delims=." %%a in ("!SYS_PY_VER!") do (
        set "PY_MAJOR=%%a"
        set "PY_MINOR=%%b"
    )
    
    :: Accept Python 3.10, 3.11, or 3.12
    if !PY_MAJOR! equ 3 (
        if !PY_MINOR! geq 10 if !PY_MINOR! leq 12 (
            echo       Found compatible Python !SYS_PY_VER! in PATH
            set "PYTHON_EXE=python"
            goto :check_gpu
        )
    )
    echo       System Python !SYS_PY_VER! not compatible ^(need 3.10-3.12^)
)

:: Download embedded Python
echo       Downloading Python %PYTHON_VERSION%...
echo.
echo       This is a portable Python that won't affect your system.
echo       Size: ~25 MB
echo.

:: Create python directory
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

:: Download using PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_DIR%\python.zip' -UseBasicParsing}"
if %errorlevel% neq 0 (
    echo ERROR: Failed to download Python. Check your internet connection.
    pause
    exit /b 1
)

:: Verify SHA256 hash for security
echo       Verifying download...
for /f %%h in ('powershell -Command "(Get-FileHash '%PYTHON_DIR%\python.zip' -Algorithm SHA256).Hash"') do set "DOWNLOAD_HASH=%%h"
if /i not "!DOWNLOAD_HASH!"=="%PYTHON_SHA256%" (
    echo ERROR: Download verification failed! Hash mismatch.
    echo        Expected: %PYTHON_SHA256%
    echo        Got:      !DOWNLOAD_HASH!
    del "%PYTHON_DIR%\python.zip" 2>nul
    pause
    exit /b 1
)
echo       Verified OK

:: Extract
echo       Extracting...
powershell -Command "Expand-Archive -Path '%PYTHON_DIR%\python.zip' -DestinationPath '%PYTHON_DIR%' -Force"
del "%PYTHON_DIR%\python.zip"

:: Enable pip by modifying the ._pth file
:: Find the pth file (e.g., python312._pth)
for %%f in ("%PYTHON_DIR%\python*._pth") do (
    echo python312.zip>> "%%f"
    echo .>> "%%f"
    echo import site>> "%%f"
)

:: Download and install pip
echo       Installing pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%PYTHON_DIR%\get-pip.py' -UseBasicParsing}"
"%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location >nul 2>&1
del "%PYTHON_DIR%\get-pip.py"

echo       Python %PYTHON_VERSION% installed successfully!
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

:: ========== STEP 2: Check GPU ==========
:check_gpu
echo.
echo [2/4] Checking GPU...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo       WARNING: NVIDIA GPU not detected.
    echo       This app requires an NVIDIA GPU with 8GB+ VRAM.
    echo.
)

:: ========== STEP 3: Create Virtual Environment ==========
echo [3/4] Setting up environment...

if not exist "%VENV_DIR%" (
    echo       Creating virtual environment...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo       Virtual environment exists, skipping...
)

:: Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

:: Upgrade pip quietly
python -m pip install --upgrade pip >nul 2>&1

:: ========== STEP 4: Install Dependencies ==========
echo.
echo [4/4] Installing dependencies...
echo       This may take several minutes on first run.
echo.

:: Install PyTorch with CUDA first (most critical)
echo       [4a] PyTorch + CUDA 12.4...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyTorch installation failed.
    echo       Make sure you have a compatible NVIDIA GPU and drivers.
    pause
    exit /b 1
)

:: Install other dependencies
echo.
echo       [4b] Qwen-TTS and dependencies...
pip install qwen-tts gradio noisereduce platformdirs matplotlib
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

:: Install ffmpeg if not present
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo       [4c] Installing ffmpeg...
    winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements >nul 2>&1
    if errorlevel 1 (
        echo       Note: ffmpeg not installed. Install manually if audio issues occur.
    )
)

:: ========== DONE ==========
echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo   To start the app, run: run.bat
echo.
echo   First run will download ~4GB of AI models.
echo.
pause
