@echo off
REM ============================================================
REM  Ozone Hotspot Dashboard — LAN launcher (Windows)
REM ============================================================
REM
REM  Starts the Streamlit dashboard and binds it so other
REM  computers on the same Wi-Fi / LAN can open it in a browser.
REM
REM  Usage: double-click this file (in the ozone_pkg folder).
REM
REM ============================================================

echo.
echo ============================================================
echo   Ozone Hotspot Dashboard — starting...
echo ============================================================
echo.

REM Find local IP (best-effort)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    for /f "tokens=* delims= " %%b in ("%%a") do (
        set LOCAL_IP=%%b
        goto :found_ip
    )
)
:found_ip

echo   On THIS PC:          http://localhost:8501
echo   On other PCs (LAN):  http://%LOCAL_IP%:8501
echo.
echo   Tell others to connect to the "LAN" URL above.
echo   Press Ctrl+C to stop the server.
echo.
echo ============================================================
echo.

REM Activate virtual environment if present (optional)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Start Streamlit, binding to all network interfaces (0.0.0.0)
streamlit run app.py ^
    --server.address 0.0.0.0 ^
    --server.port 8501 ^
    --server.headless true ^
    --browser.gatherUsageStats false

pause
