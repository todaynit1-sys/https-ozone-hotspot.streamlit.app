@echo off
REM ============================================================
REM  Ozone Hotspot Dashboard — Public URL via Cloudflare Tunnel
REM ============================================================
REM
REM  This gives your PC a temporary https://xxxx.trycloudflare.com URL
REM  that anyone (including people outside your office) can open.
REM
REM  FIRST-TIME SETUP:
REM    1) Download cloudflared.exe from:
REM       https://github.com/cloudflare/cloudflared/releases/latest
REM       (pick: cloudflared-windows-amd64.exe)
REM    2) Rename to cloudflared.exe
REM    3) Place it in this folder (same folder as this .bat file)
REM
REM  USAGE:
REM    Double-click this file. Two windows will open:
REM      - One runs Streamlit (localhost:8501)
REM      - Another shows the public URL (share this with others)
REM
REM ============================================================

echo.
echo ============================================================
echo   Ozone Hotspot — Public URL Launcher
echo ============================================================
echo.

REM Check that cloudflared.exe exists
if not exist cloudflared.exe (
    echo [ERROR] cloudflared.exe not found in this folder.
    echo.
    echo Please download it from:
    echo   https://github.com/cloudflare/cloudflared/releases/latest
    echo   File: cloudflared-windows-amd64.exe
    echo Rename to cloudflared.exe and place here.
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting Streamlit in background...
start "Ozone Streamlit" /MIN cmd /c "streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false"

REM Wait a few seconds for Streamlit to come up
timeout /t 8 /nobreak > nul

echo [2/2] Starting Cloudflare Tunnel...
echo.
echo Look for "https://" URL in the output below.
echo Copy it and share with whoever needs access.
echo.
echo ============================================================
echo.

cloudflared.exe tunnel --url http://localhost:8501

pause
