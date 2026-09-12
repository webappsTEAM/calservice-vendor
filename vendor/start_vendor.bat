@echo off
cd /d "%~dp0backend"
start "Vendor-Backend" /min "%~dp0backend\.venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8001
cd /d "%~dp0frontend"
start "Vendor-Frontend" /min cmd /c "npm run dev"
