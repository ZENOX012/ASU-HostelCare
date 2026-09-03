@echo off
title ASU HostelCare Server Launcher
echo ===============================================================
echo            ASU HostelCare — Starting Local Server
echo ===============================================================
echo.
echo Installing / verifying dependencies...
python -m pip install -r requirements.txt
echo.
echo Starting server on http://127.0.0.1:8000 ...
echo Press CTRL+C to stop the server anytime.
echo.
python main.py
pause
