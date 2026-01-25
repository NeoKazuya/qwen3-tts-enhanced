@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo   Qwen3-TTS Voice Clone - Installer
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo WARNING: NVIDIA GPU not detected. This app requires an NVIDIA GPU.
    echo.
)

:: Create venv
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/3] Virtual environment exists, skipping...
)

:: Activate and install
echo [2/3] Installing PyTorch with CUDA support...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

echo [3/3] Installing Qwen-TTS and dependencies...
pip install qwen-tts gradio noisereduce platformdirs

:: Install ffmpeg if not present
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing ffmpeg for audio processing...
    winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements >nul 2>&1
)

echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo To start the app, run: run.bat
echo.
pause
