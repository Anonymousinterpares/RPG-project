@echo off
echo Starting RPG Game Web Server...
echo.

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the server startup script
python start_server.py

REM If server exits, keep the window open
pause